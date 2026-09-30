import logging
from typing import Dict, Any
from .base import Tool

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
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Chemin absolu du fichier à modifier."
                },
                "search_text": {
                    "type": "string",
                    "description": "Le texte exact à rechercher et remplacer."
                },
                "replace_text": {
                    "type": "string",
                    "description": "Le nouveau texte qui viendra remplacer search_text."
                }
            },
            "required": ["file_path", "search_text", "replace_text"],
            "type": "object"
        }

    async def execute(self, **kwargs) -> str:
        file_path = kwargs.get("file_path")
        search_text = kwargs.get("search_text")
        replace_text = kwargs.get("replace_text")
        
        try:
            with open(file_path, "r") as f:
                content = f.read()
                
            if search_text not in content:
                return f"Erreur : Le texte de recherche exact n'a pas été trouvé dans {file_path}."
                
            new_content = content.replace(search_text, replace_text, 1)
            
            with open(file_path, "w") as f:
                f.write(new_content)
                
            return f"✅ Fichier {file_path} patché avec succès."
        except Exception as e:
            return f"Erreur lors du patch de {file_path} : {str(e)}"
