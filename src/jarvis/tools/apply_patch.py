import logging
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class ApplyPatchTool(Tool):
    @property
    def name(self) -> str:
        return "apply_patch"

    @property
    def description(self) -> str:
        return (
            "Applique un diff de type V4A (ou une édition textuelle) à un fichier de ton espace de travail. "
            "Plus précis que FileSystemTool pour modifier de gros fichiers sans tout réécrire."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Chemin absolu du fichier à modifier.",
                },
                "search_text": {
                    "type": "string",
                    "description": "Le texte exact à rechercher et remplacer.",
                },
                "replace_text": {
                    "type": "string",
                    "description": "Le nouveau texte qui viendra remplacer search_text.",
                },
            },
            "required": ["file_path", "search_text", "replace_text"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        from jarvis.filesystem import _safe_path

        file_path = kwargs.get("file_path")
        search_text = kwargs.get("search_text")
        replace_text = kwargs.get("replace_text")

        safe = _safe_path(file_path)
        if safe is None:
            return f"🚫 Sécurité: Le chemin '{file_path}' est interdit. Vous ne pouvez patcher que des fichiers dans /app/workspace."

        try:
            with open(safe, "r") as f:
                content = f.read()

            if search_text not in content:
                return f"Erreur : Le texte de recherche exact n'a pas été trouvé dans {safe.name}."

            new_content = content.replace(search_text, replace_text, 1)

            with open(safe, "w") as f:
                f.write(new_content)

            return f"✅ Fichier {safe.name} patché avec succès."
        except Exception as e:
            return f"Erreur lors du patch de {safe.name} : {e!s}"
