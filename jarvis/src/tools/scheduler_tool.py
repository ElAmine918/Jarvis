import asyncio
import datetime
import logging
import uuid
from typing import Any

import httpx

from ..config import ALLOWED_TELEGRAM_USER_IDS, TELEGRAM_BOT_TOKEN
from ..logger_db import get_pending_jobs, mark_job_fired, save_scheduled_job
from .base import Tool

logger = logging.getLogger(__name__)


async def _send_telegram_reminder(
    job_id: str, message: str, delay_seconds: float, is_missed: bool = False
):
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    if not ALLOWED_TELEGRAM_USER_IDS:
        return
    user_id = ALLOWED_TELEGRAM_USER_IDS[0]

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    prefix = "⏰ [RAPPEL DIFFÉRÉ]" if is_missed else "⏰ **RAPPEL PROGRAMMÉ** :"
    text = f"{prefix}\n\n{message}"

    payload = {"chat_id": user_id, "text": text, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except Exception as e:
        logger.error(f"Erreur d'envoi du rappel: {e}")
    finally:
        mark_job_fired(job_id)


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
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "delay_minutes": {
                    "type": "integer",
                    "description": "Le délai d'attente en minutes avant l'envoi du rappel.",
                },
                "message": {
                    "type": "string",
                    "description": "Le texte du rappel à envoyer.",
                },
            },
            "required": ["delay_minutes", "message"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        delay_minutes = kwargs.get("delay_minutes", 1)
        message = kwargs.get("message")

        # M-13 : Valider le délai — min 1 min, max 24h (1440 min)
        delay_minutes = max(1, min(int(delay_minutes), 1440))
        delay_seconds = delay_minutes * 60

        # M-11 : Limiter le nombre de rappels actifs simultanés
        _MAX_PENDING = 10
        active_tasks = [t for t in asyncio.all_tasks() if "reminder" in t.get_name()]
        if len(active_tasks) >= _MAX_PENDING:
            return f"❌ Limite atteinte : {_MAX_PENDING} rappels sont déjà en attente. Attends qu'ils s'exécutent avant d'en programmer d'autres."

        job_id = uuid.uuid4().hex[:8]
        fire_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=delay_minutes)
        save_scheduled_job(job_id, message, fire_at.isoformat())

        asyncio.create_task(
            _send_telegram_reminder(job_id, message, delay_seconds),
            name=f"reminder_{job_id}_{delay_minutes}m",
        )

        return f"✅ Rappel programmé avec succès. Le message sera envoyé dans {delay_minutes} minute(s)."

    @classmethod
    async def reload_pending_jobs(cls):
        jobs = get_pending_jobs()
        now = datetime.datetime.utcnow()
        for job in jobs:
            job_id = job["id"]
            message = job["message"]
            fire_at = datetime.datetime.fromisoformat(job["fire_at"])
            remaining = (fire_at - now).total_seconds()

            if remaining > 0:
                asyncio.create_task(
                    _send_telegram_reminder(
                        job_id, message, remaining, is_missed=False
                    ),
                    name=f"reminder_{job_id}_reloaded",
                )
            else:
                asyncio.create_task(
                    _send_telegram_reminder(job_id, message, 0, is_missed=True),
                    name=f"reminder_{job_id}_missed",
                )
