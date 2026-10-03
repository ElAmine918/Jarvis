import logging
from typing import Any

from .base import Tool

logger = logging.getLogger(__name__)


class ImageGenerationTool(Tool):
    @property
    def name(self) -> str:
        return "generate_image"

    @property
    def description(self) -> str:
        return "Génère une image à partir d'un prompt textuel."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "La description détaillée de l'image à générer.",
                }
            },
            "required": ["prompt"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        # Placeholder because generating images requires a dedicated API (OpenAI DALL-E) or heavy local GPU
        return "L'outil ImageGenerationTool nécessite la configuration d'une clé API DALL-E ou d'un worker GPU local (indisponible sur le nœud Proxmox actuel). Cette fonctionnalité arrivera dans Jarvis v6.1."
