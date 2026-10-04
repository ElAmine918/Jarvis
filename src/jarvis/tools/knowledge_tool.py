import logging
from typing import Any

from jarvis.core.agent import JarvisAgent
from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

class KnowledgeBaseTool(Tool):
    @property
    def name(self) -> str:
        return "knowledge_base"

    @property
    def description(self) -> str:
        return (
            "Permet d'écrire ou de lire des informations importantes et pérennes dans la base de connaissances (facts) de Jarvis. "
            "À utiliser pour mémoriser ou récupérer des IP, des topologies réseau, des mots de passe (chiffrés), ou des préférences utilisateur."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["save_fact", "get_fact"],
                    "description": "L'action à effectuer : 'save_fact' pour mémoriser une information, 'get_fact' pour la lire.",
                },
                "key": {
                    "type": "string",
                    "description": "La clé ou le nom du sujet (ex: 'ip_nas_proxmox', 'topologie_reseau'). Toujours en minuscules sans espaces.",
                },
                "value": {
                    "type": "string",
                    "description": "La valeur ou l'information détaillée à sauvegarder (uniquement requis si action='save_fact').",
                },
            },
            "required": ["action", "key"],
        }

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        key = kwargs.get("key", "").strip().lower().replace(" ", "_")
        value = kwargs.get("value")

        # Pour accéder au MemoryManager global
        # Solution simple : créer une instance temporaire ou l'importer, 
        # JarvisAgent.memory est un singleton de facto via config.
        from jarvis.storage.memory import MemoryManager
        memory = MemoryManager()

        try:
            if action == "save_fact":
                if not value:
                    return "❌ Erreur : La 'value' est requise pour sauvegarder un fait."
                res = await memory.save_fact(key, value)
                return f"✅ Fait sauvegardé avec succès dans la base de connaissances. (Clé: {key})"
                
            elif action == "get_fact":
                val = await memory.get_fact(key)
                if val:
                    return f"🧠 Résultat pour '{key}' : {val}"
                else:
                    return f"❌ Aucune information trouvée dans la base de connaissances pour la clé '{key}'."
                    
            else:
                return "❌ Action non reconnue."
                
        except Exception as e:
            logger.error(f"Erreur KnowledgeBaseTool : {e}")
            return f"❌ Erreur technique lors de l'accès à la base de connaissances : {e}"
