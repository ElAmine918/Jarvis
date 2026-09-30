import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class Tool(ABC):
    """Classe de base pour tous les outils Jarvis."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom de l'outil (utilisé par Claude)."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Description de ce que fait l'outil."""
        pass
        
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Schéma JSON des paramètres attendus par l'outil."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Exécute l'outil avec les arguments fournis et retourne un résultat sous forme de chaîne."""
        pass
        
    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convertit la définition de l'outil au format attendu par l'API Anthropic."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters.get("properties", {}),
                "required": self.parameters.get("required", [])
            }
        }

class ToolRegistry:
    """Registre central pour tous les outils disponibles."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        
    def register(self, tool: Tool):
        """Enregistre un nouvel outil."""
        self._tools[tool.name] = tool
        
    def get_tool(self, name: str) -> Tool:
        """Récupère un outil par son nom."""
        if name not in self._tools:
            raise ValueError(f"Outil inconnu : {name}")
        return self._tools[name]
        
    def get_all_tools_anthropic_format(self) -> List[Dict[str, Any]]:
        """Récupère tous les outils au format attendu par Claude."""
        return [tool.to_anthropic_format() for tool in self._tools.values()]
        
    async def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Exécute l'outil spécifié avec les arguments fournis."""
        tool = self.get_tool(name)
        try:
            return await tool.execute(**args)
        except Exception as e:
            return f"Erreur lors de l'exécution de l'outil {name} : {str(e)}"
