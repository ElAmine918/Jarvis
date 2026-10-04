import asyncio
import logging
import os
import re

import edge_tts
import httpx
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    tts,
    utils,
)
from livekit.agents.types import APIConnectOptions
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero

from jarvis.core.config import OLLAMA_LOCAL_URL

logger = logging.getLogger("jarvis-live")


def sanitize_speech_text(text: str) -> str:
    """Nettoie le texte avant synthèse vocale : filtre anti-Monsieur absolu et markdown."""
    text = re.sub(r"(?i)\b(monsieur)\b", "", text)
    text = re.sub(r"[*_`#~]", "", text)
    text = re.sub(r",\s*([?!.])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[,\s.-]+|[,\s.-]+$", "", text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


class ElevenLabsChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts_instance: tts.TTS,
        input_text: str,
        voice: str,
        api_key: str,
        model_id: str = "eleven_multilingual_v2",
        conn_options: APIConnectOptions | None = None,
    ):
        super().__init__(
            tts=tts_instance, input_text=input_text, conn_options=conn_options
        )
        self._voice = voice
        self._api_key = api_key
        self._model_id = model_id

    async def _run(self) -> None:
        request_id = utils.shortuuid()
        decoder = utils.codecs.AudioStreamDecoder(
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
        )

        clean_text = sanitize_speech_text(self.input_text)
        if not clean_text:
            return

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice}/stream?output_format=mp3_44100_128"
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": clean_text,
            "model_id": self._model_id,
        }

        async def _stream_producer():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream(
                        "POST", url, headers=headers, json=payload
                    ) as response:
                        if response.status_code != 200:
                            err_body = await response.aread()
                            logger.error(
                                f"Erreur ElevenLabs ({response.status_code}): {err_body.decode(errors='ignore')}"
                            )
                            return
                        async for chunk in response.aiter_bytes():
                            decoder.push(chunk)
            except Exception as e:
                logger.error(f"Exception flux ElevenLabs: {e}")
            finally:
                decoder.end_input()

        producer_task = asyncio.create_task(_stream_producer())

        try:
            emitter = tts.SynthesizedAudioEmitter(
                event_ch=self._event_ch,
                request_id=request_id,
            )
            async for frame in decoder:
                emitter.push(frame)
            emitter.flush()
        finally:
            await utils.aio.gracefully_cancel(producer_task)
            await decoder.aclose()


class ElevenLabsTTS(tts.TTS):
    def __init__(
        self,
        voice: str = "nPczCjzI2devNBz1zQrb",  # Brian (voix officielle studio)
        api_key: str = "",
        model_id: str = "eleven_multilingual_v2",
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )
        self._voice = voice
        self._api_key = api_key
        self._model_id = model_id

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions | None = None,
    ) -> tts.ChunkedStream:
        return ElevenLabsChunkedStream(
            tts_instance=self,
            input_text=text,
            voice=self._voice,
            api_key=self._api_key,
            model_id=self._model_id,
            conn_options=conn_options,
        )


class EdgeTTSChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts_instance: tts.TTS,
        input_text: str,
        voice: str,
        conn_options: APIConnectOptions | None = None,
    ):
        super().__init__(
            tts=tts_instance, input_text=input_text, conn_options=conn_options
        )
        self._voice = voice

    async def _run(self) -> None:
        request_id = utils.shortuuid()
        decoder = utils.codecs.AudioStreamDecoder(
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
        )

        clean_text = sanitize_speech_text(self.input_text)
        if not clean_text:
            return

        communicate = edge_tts.Communicate(clean_text, self._voice)

        async def _stream_producer():
            try:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        decoder.push(chunk["data"])
            finally:
                decoder.end_input()

        producer_task = asyncio.create_task(_stream_producer())

        try:
            emitter = tts.SynthesizedAudioEmitter(
                event_ch=self._event_ch,
                request_id=request_id,
            )
            async for frame in decoder:
                emitter.push(frame)
            emitter.flush()
        finally:
            await utils.aio.gracefully_cancel(producer_task)
            await decoder.aclose()


class EdgeTTS(tts.TTS):
    def __init__(self, voice: str = "fr-FR-RemyMultilingualNeural"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )
        self._voice = voice

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions | None = None,
    ) -> tts.ChunkedStream:
        return EdgeTTSChunkedStream(
            tts_instance=self,
            input_text=text,
            voice=self._voice,
            conn_options=conn_options,
        )


async def entrypoint(ctx: JobContext):
    logger.info(f"Jarvis se connecte à la salle d'appel : {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Attente de l'administrateur
    participant = await ctx.wait_for_participant()
    logger.info(f"Administrateur connecté : {participant.identity}")

    # Clés & Configuration
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    eleven_api_key = os.getenv("ELEVEN_API_KEY", "") or os.getenv(
        "ELEVENLABS_API_KEY", ""
    )
    eleven_voice_id = os.getenv(
        "ELEVEN_VOICE_ID", "nPczCjzI2devNBz1zQrb"
    )  # Brian par défaut

    # 1. STT (Écoute / Transcription)
    if groq_api_key:
        logger.info("Utilisation de Groq Whisper pour le STT (ultra-rapide)")
        stt_plugin = openai.STT(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_api_key,
            model="whisper-large-v3-turbo",
            language="fr",
        )
    elif openai_api_key:
        logger.info("Utilisation d'OpenAI pour le STT")
        stt_plugin = openai.STT(language="fr")
    else:
        logger.error("Aucune clé API (GROQ_API_KEY ou OPENAI_API_KEY) pour le STT !")
        stt_plugin = openai.STT(language="fr")

    # 2. LLM (Cerveau)
    import httpx
    
    # Test OpenRouter/Groq first, fallback to Ollama if they are down/out of credits
    async def check_api(url, key):
        if not key: return False
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{url.replace('/chat/completions', '').replace('/v1', '')}/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=2.0)
                return res.status_code == 200
        except Exception:
            return False

    if groq_api_key and await check_api("https://api.groq.com/openai", groq_api_key):
        logger.info("Utilisation de Groq pour le LLM vocal (faible latence)")
        custom_llm = openai.LLM(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_api_key,
            model="qwen/qwen3.8-27b",
        )
    elif openrouter_api_key and await check_api("https://openrouter.ai/api", openrouter_api_key):
        logger.info("Utilisation de OpenRouter pour le LLM vocal")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model_id = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free")
        custom_llm = openai.LLM(
            base_url=base_url,
            api_key=openrouter_api_key,
            model=model_id,
        )
    else:
        logger.warning("⚠️ API Cloud inaccessibles ou sans crédits. Fallback LOCAL sur Ollama pour la voix !")
        custom_llm = openai.LLM(
            base_url=OLLAMA_LOCAL_URL,
            api_key="ollama",
            model=os.getenv("OLLAMA_LOCAL_MODEL", "qwen2.5:7b"),
        )

    # 3. TTS (Synthèse vocale : ElevenLabs en priorité, sinon EdgeTTS)
    if eleven_api_key:
        logger.info(f"Utilisation d'ElevenLabs pour la voix (Voix: {eleven_voice_id})")
        tts_plugin = ElevenLabsTTS(
            voice=eleven_voice_id,
            api_key=eleven_api_key,
            model_id="eleven_multilingual_v2",
        )
    else:
        logger.info(
            "ElevenLabs non configuré -> Utilisation d'EdgeTTS (Remy Multilingual)"
        )
        tts_plugin = EdgeTTS(
            voice=os.getenv("VOICE_LIVE_TTS", "fr-FR-RemyMultilingualNeural")
        )

    # Contexte & Personnalité Jarvis
    chat_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "Tu es Jarvis, un assistant IA vocal d'élite, ultra-intelligent, posé et moderne. "
            "Tu t'exprimes en français avec un ton direct, naturel et chaleureux. "
            "RÈGLES STRICTES DE DIALOGUE ORAL : "
            "1. Interdiction absolue d'utiliser le mot 'Monsieur' sous quelque forme que ce soit. Parle directement à ton interlocuteur. "
            "2. Tes réponses doivent être très courtes (1 à 2 phrases percutantes), adaptées à une vraie conversation téléphonique. "
            "3. Pas de listes à puces, pas de formules d'obséquiosité, va droit au but."
        ),
    )

    # 4. Outils / Function Calling
    fnc_ctx = llm.FunctionContext()

    @fnc_ctx.ai_callable(
        description="Navigue sur internet pour obtenir des infos en temps réel (météo, actualités, recherche générale)."
    )
    async def browse_internet(
        url_or_search: str = llm.TypeInfo(
            description="Requête de recherche, ex: 'Météo Paris', 'News Tech'"
        ),
    ):
        from jarvis.tools.browser_tool import BrowserNavigateTool

        tool = BrowserNavigateTool()
        res = await tool.execute(url_or_search=url_or_search)
        return res[:1500] if len(res) > 1500 else res

    @fnc_ctx.ai_callable(
        description="Obtenir l'état du serveur Proxmox et des conteneurs Docker."
    )
    async def proxmox_status():
        from jarvis.tools.proxmox_tool import ProxmoxStatusTool

        tool = ProxmoxStatusTool()
        return await tool.execute()

    # Définition de l'Assistant Vocal Jarvis
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=stt_plugin,
        llm=custom_llm,
        tts=tts_plugin,
        chat_ctx=chat_ctx,
        fnc_ctx=fnc_ctx,
    )

    assistant.start(ctx.room, participant)
    await asyncio.sleep(1)
    await assistant.say(
        "Bonjour, c'est Jarvis. Je suis en ligne et prêt à vous assister. Que puis-je faire pour vous ?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
