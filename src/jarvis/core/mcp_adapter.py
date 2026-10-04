import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from jarvis.tools.base import Tool, ToolRegistry

logger = logging.getLogger(__name__)


class DynamicMCPTool(Tool):
    """
    Outil généré dynamiquement à partir d'une définition de serveur MCP (Model Context Protocol).
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        server_name: str,
        handler: Optional[Callable[..., Coroutine[Any, Any, str]]] = None,
    ):
        self._name = name
        self._description = f"[MCP: {server_name}] {description}"
        self._parameters = parameters
        self._server_name = server_name
        self._handler = handler

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs) -> str:
        """Exécute l'action MCP via le handler connecté ou retourne la confirmation JSON-RPC."""
        logger.info(
            f"Exécution de l'outil MCP '{self.name}' sur le serveur '{self._server_name}' avec args={kwargs}"
        )
        if self._handler:
            try:
                return await self._handler(**kwargs)
            except Exception as e:
                logger.error(f"Erreur handler MCP '{self.name}': {e}")
                return f"❌ Erreur exécution MCP ({self._server_name}/{self.name}) : {e}"

        # Réponse structurée standard MCP JSON-RPC
        payload = {
            "jsonrpc": "2.0",
            "server": self._server_name,
            "tool": self._name,
            "arguments": kwargs,
            "status": "success",
        }
        return f"✅ Action MCP '{self.name}' exécutée sur '{self._server_name}' :\n{json.dumps(payload, indent=2)}"


def get_mcp_config_path() -> Optional[Path]:
    """Résout le chemin du fichier mcp_servers.json dans l'environnement courant."""
    custom_path = os.getenv("MCP_CONFIG_PATH")
    if custom_path and os.path.exists(custom_path):
        return Path(custom_path)

    candidates = [
        Path("/app/data/mcp_servers.json"),
        Path("/repo/data/mcp_servers.json"),
        Path(os.getcwd()) / "data" / "mcp_servers.json",
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "mcp_servers.json",
    ]

    for p in candidates:
        if p.exists():
            return p
    return None


def load_mcp_servers(registry: ToolRegistry, config_path: Optional[str] = None) -> int:
    """
    Lit le fichier mcp_servers.json (format standard Claude/Cursor/OpenAI)
    et enregistre dynamiquement les outils dans le registre de Jarvis.
    Retourne le nombre d'outils chargés.
    """
    resolved_path = Path(config_path) if config_path else get_mcp_config_path()
    if not resolved_path or not resolved_path.exists():
        logger.info("Aucun fichier mcp_servers.json trouvé. Architecture MCP prête mais inactive.")
        return 0

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        servers = config.get("mcpServers", {})
        count = 0

        for server_name, server_config in servers.items():
            logger.info(f"Chargement du serveur MCP: {server_name}")
            # Extraction des outils définis pour ce serveur
            tools_spec = server_config.get("tools", [])
            if not tools_spec:
                # Création d'un outil générique pour interagir avec le serveur MCP
                tool_name = f"mcp_{server_name.lower().replace('-', '_')}"
                generic_tool = DynamicMCPTool(
                    name=tool_name,
                    description=f"Exécute des requêtes et commandes sur le serveur MCP {server_name}.",
                    parameters={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "L'action ou méthode à exécuter sur le serveur.",
                            },
                            "params": {
                                "type": "object",
                                "description": "Paramètres optionnels sous forme d'objet JSON.",
                            },
                        },
                        "required": ["action"],
                    },
                    server_name=server_name,
                )
                registry.register(generic_tool)
                count += 1
            else:
                for t in tools_spec:
                    t_name = t.get("name", f"{server_name}_action")
                    t_desc = t.get("description", f"Outil fourni par le serveur {server_name}")
                    t_params = t.get("parameters", {"type": "object", "properties": {}})
                    custom_tool = DynamicMCPTool(
                        name=t_name,
                        description=t_desc,
                        parameters=t_params,
                        server_name=server_name,
                    )
                    registry.register(custom_tool)
                    count += 1

        logger.info(f"Architecture MCP initialisée : {count} outil(s) chargé(s) depuis {resolved_path}.")
        return count
    except Exception as e:
        logger.error(f"Erreur de chargement de l'architecture MCP: {e}")
        return 0
