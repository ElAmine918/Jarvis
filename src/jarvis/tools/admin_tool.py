import asyncio
import logging
import uuid
from typing import Any

import httpx

from jarvis.core.approvals import APPROVAL_RESULTS, PENDING_APPROVALS
from jarvis.core.config import ALLOWED_TELEGRAM_USER_IDS, TELEGRAM_BOT_TOKEN
from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class AdminActionTool(Tool):
    @property
    def name(self) -> str:
        return "ask_admin_approval"

    @property
    def description(self) -> str:
        return (
            "Demande à l'administrateur système (Amine) d'approuver une action Docker "
            "normalement interdite (comme arrêter un conteneur non-gérable ou redémarrer le système). "
            "Le script s'interrompt jusqu'à ce que l'administrateur clique sur un bouton dans Telegram."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "action": {
                    "type": "string",
                    "description": "L'action Docker à forcer (ex: 'stop', 'restart', 'rm -f')",
                },
                "container_name": {
                    "type": "string",
                    "description": "Le nom du conteneur cible (ex: 'open-webui')",
                },
                "reason": {
                    "type": "string",
                    "description": "Pourquoi as-tu besoin de faire ça ? (Sera lu par l'admin)",
                },
            },
            "required": ["action", "container_name", "reason"],
        }

    async def execute(
        self, action: str, container_name: str, reason: str, **kwargs
    ) -> str:
        if not TELEGRAM_BOT_TOKEN or not ALLOWED_TELEGRAM_USER_IDS:
            return "❌ Impossible: Telegram n'est pas configuré pour les approbations."

        _ALLOWED_DOCKER_ACTIONS = {"stop", "restart", "start", "rm", "kill", "pause", "unpause", "prune"}
        base_action = action.split()[0]
        if base_action not in _ALLOWED_DOCKER_ACTIONS:
            return (
                f"🚫 Action Docker '{action}' non reconnue. "
                f"Actions permises : {', '.join(sorted(_ALLOWED_DOCKER_ACTIONS))}."
            )

        req_id = str(uuid.uuid4())[:8]
        admin_id = ALLOWED_TELEGRAM_USER_IDS[0]  # On envoie à l'admin principal (Amine)

        event = asyncio.Event()
        PENDING_APPROVALS[req_id] = event

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approuver", "callback_data": f"approve_{req_id}"},
                    {"text": "❌ Refuser", "callback_data": f"reject_{req_id}"},
                ]
            ]
        }

        text_msg = (
            "⚠️ **Demande d'autorisation système** ⚠️\n\n"
            f"Jarvis demande à forcer l'exécution de :\n`docker {action} {container_name}`\n\n"
            f"**Raison fournie :**\n_{reason}_"
        )

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": admin_id,
                        "text": text_msg,
                        "parse_mode": "Markdown",
                        "reply_markup": keyboard,
                    },
                )
        except Exception as e:
            PENDING_APPROVALS.pop(req_id, None)
            return f"❌ Erreur lors de l'envoi de la demande Telegram: {e}"

        logger.info(f"En attente de l'approbation admin pour la requête {req_id}...")

        try:
            # On attend maximum 5 minutes pour que l'utilisateur clique
            await asyncio.wait_for(event.wait(), timeout=300.0)
        except asyncio.TimeoutError:
            PENDING_APPROVALS.pop(req_id, None)
            return "⏳ L'administrateur n'a pas répondu à temps (timeout de 5 minutes). L'action est annulée."

        approved = APPROVAL_RESULTS.pop(req_id, False)
        PENDING_APPROVALS.pop(req_id, None)

        if not approved:
            return "❌ L'administrateur a REFUSÉ l'action. N'insiste pas."

        # L'action est approuvée ! On l'exécute avec les args validés (allowlist)
        logger.warning(
            f"Action '{action} {container_name}' approuvée par l'admin ! Exécution."
        )

        import shlex
        args = ["docker"] + shlex.split(action) + [container_name]
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return f"❌ Action approuvée mais erreur d'exécution Docker : {stderr.decode()}"

        return f"✅ L'administrateur a approuvé et l'action a été exécutée avec succès.\n{stdout.decode()}"
