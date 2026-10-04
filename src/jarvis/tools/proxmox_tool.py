import asyncio
import logging
import uuid
from typing import Any

import httpx
import urllib3
from proxmoxer import ProxmoxAPI

from jarvis.core.approvals import APPROVAL_RESULTS, PENDING_APPROVALS
from jarvis.core.config import (
    ALLOWED_TELEGRAM_USER_IDS,
    PROXMOX_HOST,
    PROXMOX_TOKEN_NAME,
    PROXMOX_TOKEN_VALUE,
    PROXMOX_USER,
    TELEGRAM_BOT_TOKEN,
)
from jarvis.tools.base import Tool

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


def get_proxmox_client():
    if not PROXMOX_TOKEN_VALUE:
        raise ValueError("PROXMOX_TOKEN_VALUE is not set.")
    return ProxmoxAPI(
        PROXMOX_HOST,
        user=PROXMOX_USER,
        token_name=PROXMOX_TOKEN_NAME,
        token_value=PROXMOX_TOKEN_VALUE,
        verify_ssl=False,
    )


class ProxmoxStatusTool(Tool):
    @property
    def name(self) -> str:
        return "proxmox_status"

    @property
    def description(self) -> str:
        return "Récupère le statut de toutes les VMs (qemu) et conteneurs LXC sur le noeud Proxmox."

    @property
    def parameters(self) -> dict[str, Any]:
        return {"properties": {}, "required": []}

    async def execute(self, **kwargs) -> str:
        try:
            client = get_proxmox_client()
            node = "pve"

            # Using asyncio.to_thread because proxmoxer is synchronous
            qemu = await asyncio.to_thread(client.nodes(node).qemu.get)
            lxc = await asyncio.to_thread(client.nodes(node).lxc.get)

            output = []
            output.append("=== VMs (QEMU) ===")
            for vm in qemu:
                output.append(
                    f"[{vm.get('vmid', '')}] {vm.get('name', '')} - Status: {vm.get('status', '')}"
                )

            output.append("\n=== LXC Containers ===")
            for ct in lxc:
                output.append(
                    f"[{ct.get('vmid', '')}] {ct.get('name', '')} - Status: {ct.get('status', '')}"
                )

            return "\n".join(output)

        except Exception as e:
            return f"❌ Erreur lors de la récupération du statut Proxmox: {e}"


class ProxmoxActionTool(Tool):
    @property
    def name(self) -> str:
        return "ask_proxmox_action_approval"

    @property
    def description(self) -> str:
        return (
            "Demande à l'administrateur système (Amine) d'approuver une action Proxmox "
            "(start, stop, reboot, destroy, delete, rm d'une VM/LXC). "
            "Le script s'interrompt jusqu'à ce que l'administrateur clique sur un bouton dans Telegram."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "action": {
                    "type": "string",
                    "description": "L'action à effectuer ('start', 'stop', 'reboot', 'destroy', 'delete')",
                },
                "vmid": {
                    "type": "string",
                    "description": "L'ID de la VM ou du conteneur (ex: '100', '101')",
                },
                "vm_type": {
                    "type": "string",
                    "description": "Le type ('qemu' ou 'lxc')",
                },
                "reason": {
                    "type": "string",
                    "description": "Pourquoi as-tu besoin de faire ça ?",
                },
            },
            "required": ["action", "vmid", "vm_type", "reason"],
        }

    async def execute(
        self, action: str, vmid: str, vm_type: str, reason: str, **kwargs
    ) -> str:
        if not TELEGRAM_BOT_TOKEN or not ALLOWED_TELEGRAM_USER_IDS:
            return "❌ Impossible: Telegram n'est pas configuré pour les approbations."

        _ALLOWED_ACTIONS = {"start", "stop", "reboot", "destroy", "delete", "rm"}
        if action not in _ALLOWED_ACTIONS:
            return f"🚫 Sécurité : action Proxmox '{action}' non autorisée."

        if vm_type not in {"qemu", "lxc"}:
            return f"🚫 Erreur : type '{vm_type}' inconnu. Utilisez 'qemu' ou 'lxc'."

        req_id = str(uuid.uuid4())[:8]
        admin_id = ALLOWED_TELEGRAM_USER_IDS[0]

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
            "⚠️ **Demande d'action Proxmox** ⚠️\n\n"
            f"Jarvis demande à exécuter l'action :\n`{action}` sur `{vm_type}` ID `{vmid}`\n\n"
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

        logger.info(
            f"En attente de l'approbation admin pour la requête Proxmox {req_id}..."
        )

        try:
            await asyncio.wait_for(event.wait(), timeout=300.0)
        except asyncio.TimeoutError:
            PENDING_APPROVALS.pop(req_id, None)
            return "⏳ L'administrateur n'a pas répondu à temps (timeout de 5 minutes). L'action est annulée."

        approved = APPROVAL_RESULTS.pop(req_id, False)
        PENDING_APPROVALS.pop(req_id, None)

        if not approved:
            return "❌ L'administrateur a REFUSÉ l'action. N'insiste pas."

        logger.warning(f"Action '{action}' sur {vm_type} {vmid} approuvée ! Exécution.")

        try:
            pve_client = get_proxmox_client()
            node_api = pve_client.nodes("pve")
            resource = node_api.qemu(vmid) if vm_type == "qemu" else node_api.lxc(vmid)

            # Executing action
            if action == "start":
                await asyncio.to_thread(resource.status.start.post)
            elif action == "stop":
                await asyncio.to_thread(resource.status.stop.post)
            elif action == "reboot":
                await asyncio.to_thread(resource.status.reboot.post)
            elif action in {"destroy", "delete", "rm"}:
                # Ensure the container/VM is stopped first if it was running
                try:
                    await asyncio.to_thread(resource.status.stop.post)
                    await asyncio.sleep(2)
                except Exception:
                    pass
                # Delete the resource with purge=1
                await asyncio.to_thread(resource.delete, purge=1)

            return f"✅ L'administrateur a approuvé et l'action Proxmox '{action}' sur {vm_type} {vmid} a été exécutée avec succès."
        except Exception as e:
            return f"❌ Action approuvée mais erreur Proxmox : {e}"
