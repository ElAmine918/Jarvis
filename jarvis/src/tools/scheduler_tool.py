import logging
import asyncio
import httpx
from typing import Dict, Any
from .base import Tool
from ..config import TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_USER_IDS

logger = logging.getLogger(__name__)

async def _send_telegram_reminder(message: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    if not ALLOWED_TELEGRAM_USER_IDS:
        return
    user_id = ALLOWED_TELEGRAM_USER_IDS[0]
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": f"⏰ **RAPPEL PROGRAMMÉ** :\n\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        logger.error(f"Erreur d'envoi du rappel: {e}")

class SchedulerTool(Tool):
    @property
    def name(self) -> str:
        return "schedule_reminder"

    @property
    def description(self) -> str:
        return (
            "Planifie un rappel ou une tâche différée. "
            "Envoie automatiquement un message à l'utilisateur sur Telegram "
            "après un délai spécifique en minutes."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "delay_minutes": {
                    "type": "integer",
                    "description": "Le délai d'attente en minutes avant l'envoi du rappel."
                },
                "message": {
                    "type": "string",
                    "description": "Le texte du rappel à envoyer."
                }
            },
            "required": ["delay_minutes", "message"],
            "type": "object"
        }

    async def execute(self, **kwargs) -> str:
        delay_minutes = kwargs.get("delay_minutes", 1)
        message = kwargs.get("message")
        
        delay_seconds = int(delay_minutes * 60)
        
        # Lance la tâche en arrière-plan (Fire and forget)
        asyncio.create_task(_send_telegram_reminder(message, delay_seconds))
        
        return f"✅ Rappel programmé avec succès. Le message sera envoyé dans {delay_minutes} minute(s)."
