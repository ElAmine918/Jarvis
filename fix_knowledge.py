import logging
import re
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

class KnowledgeBaseTool(Tool):
    @property
    def name(self) -> str:
        return "knowledge_base"

    @property
    def description(self) -> str:
        return "Permet d'écrire ou de lire des informations importantes et pérennes dans la base de connaissances (facts)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["save_fact", "get_fact"],
                    "description": "L'action à effectuer.",
                },
                "key": {
                    "type": "string",
                    "description": "La clé ou le nom du sujet.",
                },
                "value": {
                    "type": "string",
                    "description": "La valeur ou l'information détaillée à sauvegarder.",
                },
            },
            "required": ["action", "key"],
        }

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        raw_key = kwargs.get("key", "").strip().lower()
        # Sanitize key strictly: only alphanumeric and underscores
        key = re.sub(r'[^a-z0-9_]', '_', raw_key).strip('_')
        value = kwargs.get("value")

        if not key:
            return "❌ Erreur : La clé est invalide ou vide après nettoyage."

        from jarvis.storage.memory import MemoryManager
        memory = MemoryManager()

        try:
            if action == "save_fact":
                if not value:
                    return "❌ Erreur : La 'value' est requise."
                res = await memory.save_fact(key, value)
                return f"✅ Fait sauvegardé avec succès. (Clé: {key})"
                
            elif action == "get_fact":
                val = await memory.get_fact(key)
                if val:
                    return f"🧠 Résultat pour '{key}' : {val}"
                else:
                    return f"❌ Aucune information trouvée pour '{key}'."
                    
            else:
                return "❌ Action non reconnue."
                
        except Exception as e:
            logger.error(f"Erreur KnowledgeBaseTool : {e}")
            return f"❌ Erreur technique : {e}"
