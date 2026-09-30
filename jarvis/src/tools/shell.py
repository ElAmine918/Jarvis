"""
ShellTool RETIRÉ — remplacé par des outils spécifiques.
Ce fichier existe uniquement pour afficher un message clair si l'agent tente
d'utiliser l'ancien outil.
"""
import logging
from typing import Any, Dict
from .base import Tool

logger = logging.getLogger(__name__)


class ShellTool(Tool):
    """Ancien outil shell — désactivé pour des raisons de sécurité."""

    @property
    def name(self) -> str:
        return "execute_shell_command"

    @property
    def description(self) -> str:
        return (
            "DÉSACTIVÉ. Utilise system_info pour les données système, "
            "manage_files pour les fichiers, manage_docker pour Docker. "
            "Le shell générique a été retiré pour des raisons de sécurité."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "command": {"type": "string", "description": "Ignoré — outil désactivé."}
            },
            "required": ["command"]
        }

    async def execute(self, command: str = "", **kwargs) -> str:
        logger.warning(f"Tentative d'utilisation de l'outil shell désactivé: {command!r}")
        return (
            "🚫 L'outil shell générique est désactivé. "
            "Utilise `system_info` (cpu, memory, disk, processes, containers), "
            "`manage_files` (read, write, list, mkdir) ou `manage_docker` (ps, logs, start, restart)."
        )
