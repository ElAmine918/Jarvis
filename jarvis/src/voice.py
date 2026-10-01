import os
import re
import tempfile
import logging
import openai
import edge_tts
import httpx
from typing import Optional

from .config import GEMINI_MODEL, LOCAL_STT_URL, LOCAL_TTS_URL

logger = logging.getLogger(__name__)

async def transcribe_voice(file_bytes: bytes) -> str:
    """
    Transcrit l'audio en texte avec priorité sur le modèle local.
    """
    if LOCAL_STT_URL:
        logger.info(f"Utilisation du STT Local : {LOCAL_STT_URL}")
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(file_bytes)
                temp_path = f.name
            try:
                async with httpx.AsyncClient() as client:
                    with open(temp_path, "rb") as audio_file:
                        res = await client.post(
                            f"{LOCAL_STT_URL}/asr",
                            files={"audio_file": audio_file},
                            data={"output": "txt", "encode": "true", "task": "transcribe"},
                            timeout=30.0
                        )
                    if res.status_code == 200:
                        return res.text.strip()
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            logger.error(f"Erreur STT Local: {e}. Fallback vers Cloud...")

    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not openai_key and not gemini_key:
        return "❌ Aucune clé API (OpenAI ou Gemini) ou serveur local configuré pour la transcription."
        
    use_gemini = not openai_key
    api_key = gemini_key if use_gemini else openai_key
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if use_gemini else None
    
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    model = GEMINI_MODEL if use_gemini else "whisper-1"
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(file_bytes)
            temp_path = f.name
            
        try:
            with open(temp_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model=model,
                    file=audio_file
                )
            return transcript.text
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        logger.error(f"Erreur de transcription : {e}", exc_info=True)
        return "❌ Erreur lors de la transcription."

async def synthesize_speech(text: str) -> Optional[bytes]:
    """
    Synthétise le texte en audio avec priorité au modèle local (Piper).
    """
    clean_text = re.sub(r'[*_`#]', '', text)
    if len(clean_text) > 2000:
        clean_text = clean_text[:1997] + "..."

    if LOCAL_TTS_URL:
        logger.info(f"Utilisation du TTS Local : {LOCAL_TTS_URL}")
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{LOCAL_TTS_URL}/",
                    params={"text": clean_text},
                    timeout=30.0
                )
                if res.status_code == 200:
                    return res.content
        except Exception as e:
            logger.error(f"Erreur TTS Local: {e}. Fallback vers Edge-TTS...")

    try:
        communicate = edge_tts.Communicate(clean_text, "fr-FR-HenriNeural")
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    except Exception as e:
        logger.error(f"Erreur TTS : {e}", exc_info=True)
        return None
