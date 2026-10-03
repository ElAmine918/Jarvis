from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Classe de base pour tous les outils Jarvis."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom de l'outil (utilisé par Claude)."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description de ce que fait l'outil."""

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """Schéma JSON des paramètres attendus par l'outil."""

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Exécute l'outil avec les arguments fournis et retourne un résultat sous forme de chaîne."""

    def to_anthropic_format(self) -> dict[str, Any]:
        """Convertit la définition de l'outil au format attendu par l'API Anthropic."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters.get("properties", {}),
                "required": self.parameters.get("required", []),
            },
        }


class ToolRegistry:
    """Registre central pour tous les outils disponibles."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Enregistre un nouvel outil."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        """Récupère un outil par son nom."""
        if name not in self._tools:
            raise ValueError(f"Outil inconnu : {name}")
        return self._tools[name]

    def get_all_tools_anthropic_format(self) -> list[dict[str, Any]]:
        """Récupère tous les outils au format attendu par Claude."""
        return [tool.to_anthropic_format() for tool in self._tools.values()]

    async def execute_tool(self, name: str, args: dict[str, Any]) -> str:
        """Exécute l'outil spécifié avec les arguments fournis."""
        tool = self.get_tool(name)
        try:
            return await tool.execute(**args)
        except Exception as e:
            return f"Erreur lors de l'exécution de l'outil {name} : {e!s}"
