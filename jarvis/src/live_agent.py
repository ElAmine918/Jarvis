import asyncio
import logging
import os
import re
from typing import Optional

import edge_tts
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm, tts, utils
from livekit.agents.types import APIConnectOptions
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero

logger = logging.getLogger("jarvis-live")


class EdgeTTSChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts_instance: tts.TTS,
        input_text: str,
        voice: str,
        conn_options: Optional[APIConnectOptions] = None,
    ):
        super().__init__(tts=tts_instance, input_text=input_text, conn_options=conn_options)
        self._voice = voice

    async def _run(self) -> None:
        request_id = utils.shortuuid()
        decoder = utils.codecs.AudioStreamDecoder(
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
        )

        clean_text = re.sub(r'[*_`#~]', '', self.input_text).strip()
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
        conn_options: Optional[APIConnectOptions] = None,
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
    if groq_api_key:
        logger.info("Utilisation de Groq Qwen-27B pour le LLM vocal (faible latence)")
        custom_llm = openai.LLM(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_api_key,
            model="qwen/qwen3.8-27b",
        )
    else:
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model_id = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free")
        custom_llm = openai.LLM(
            base_url=base_url,
            api_key=openrouter_api_key,
            model=model_id,
        )

    # 3. TTS (Synthèse vocale gratuite EdgeTTS Remy Multilingual)
    tts_plugin = EdgeTTS(voice=os.getenv("VOICE_LIVE_TTS", "fr-FR-RemyMultilingualNeural"))

    # Contexte & Personnalité Jarvis
    chat_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "Tu es Jarvis, un assistant IA vocal d'élite, intelligent, distingué et bienveillant. "
            "Tu t'exprimes en français avec une diction naturelle, chaleureuse et fluide. "
            "RÈGLES D'OR DE CONVERSATION : "
            "1. Ne répète JAMAIS le mot 'Monsieur' à tout bout de champ (évite-le ou utilise-le de façon rarissime). "
            "2. Fais des phrases courtes, directes et percutantes, adaptées à un échange vocal en direct. "
            "3. Pas de listes à puces ni de formatage écrit complexe. Va droit au but sans bavardage superflu."
        ),
    )

    # Définition de l'Assistant Vocal Jarvis
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=stt_plugin,
        llm=custom_llm,
        tts=tts_plugin,
        chat_ctx=chat_ctx,
    )

    assistant.start(ctx.room, participant)
    await asyncio.sleep(1)
    await assistant.say(
        "Bonjour, c'est Jarvis. Je suis en ligne et prêt à vous assister. Que puis-je faire pour vous ?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
