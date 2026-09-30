from .base import Tool, ToolRegistry
from .shell import ShellTool
from .docker_tool import DockerTool
from .filesystem import FileSystemTool
from .system_info import SystemInfoTool
from .web_reader import WebReaderTool
from .admin_tool import AdminActionTool

__all__ = ["Tool", "ToolRegistry", "ShellTool", "DockerTool",
           "FileSystemTool", "SystemInfoTool", "WebReaderTool", "AdminActionTool"]

def get_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ShellTool())       # désactivé — renvoie message d'erreur
    registry.register(DockerTool())
    registry.register(FileSystemTool())
    registry.register(SystemInfoTool())
    registry.register(WebReaderTool())
    registry.register(AdminActionTool())
    return registry
