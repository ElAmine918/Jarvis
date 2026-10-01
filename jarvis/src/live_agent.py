import asyncio
import logging
import os
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero

logger = logging.getLogger("jarvis-live")

# Ce script est un processus autonome qui se connecte à un serveur LiveKit
# Il permet des conversations vocales "Full Duplex" (tu peux couper la parole à l'IA).

async def entrypoint(ctx: JobContext):
    logger.info(f"Jarvis se connecte à la salle d'appel : {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Attente de l'administrateur
    participant = await ctx.wait_for_participant()
    logger.info(f"Administrateur connecté : {participant.identity}")

    # Configuration des endpoints (Cloud ou Local si configuré)
    # L'astuce est de faire pointer le plugin OpenAI vers notre Mac (LM Studio) ou nos conteneurs locaux !
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model_id = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")

    custom_llm = openai.LLM(
        base_url=base_url,
        api_key=api_key,
        model=model_id
    )

    # Définition de l'Assistant Vocal Jarvis
    assistant = VoiceAssistant(
        vad=silero.VAD.load(), # Voice Activity Detection en local (très rapide)
        stt=openai.STT(), # Pourrait pointer vers Whisper.cpp local via base_url
        llm=custom_llm,
        tts=openai.TTS(voice="echo"), # Pourrait pointer vers Piper local
    )
    
    assistant.start(ctx.room, participant)
    await asyncio.sleep(1)
    await assistant.say("Bonjour Monsieur. C'est Jarvis. Je suis en ligne et prêt à vous assister en temps réel. Que puis-je faire pour vous ?", allow_interruptions=True)

if __name__ == "__main__":
    # Point d'entrée de la CLI LiveKit
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
