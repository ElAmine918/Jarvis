from .admin_tool import AdminActionTool
from .apply_patch import ApplyPatchTool
from .base import Tool, ToolRegistry
from .browser_tool import BrowserNavigateTool
from .docker_tool import DockerTool
from .filesystem import FileSystemTool
from .git_tool import GitTool
from .image_tool import ImageGenerationTool
from .memory_recall import MemoryRecallTool
from .multi_agent import AdvisorTool, FusionTool, SubagentTool
from .proxmox_tool import ProxmoxActionTool, ProxmoxStatusTool
from .python_repl import PythonREPLTool
from .rag_tool import DocumentRAGTool
from .scheduler_tool import SchedulerTool
from .shell import ShellTool
from .system_info import SystemInfoTool
from .web_reader import NewsSearchTool, WebReaderTool

__all__ = ["Tool", "ToolRegistry", "get_default_registry"]


def get_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ShellTool())  # désactivé — renvoie message d'erreur
    registry.register(DockerTool())
    registry.register(FileSystemTool())
    registry.register(SystemInfoTool())
    registry.register(WebReaderTool())
    registry.register(NewsSearchTool())
    registry.register(BrowserNavigateTool())
    registry.register(AdminActionTool())
    registry.register(SubagentTool())
    registry.register(AdvisorTool())
    registry.register(FusionTool())
    registry.register(ApplyPatchTool())
    registry.register(ImageGenerationTool())
    registry.register(PythonREPLTool())
    registry.register(DocumentRAGTool())
    registry.register(MemoryRecallTool())
    registry.register(SchedulerTool())
    registry.register(GitTool())
    registry.register(ProxmoxStatusTool())
    registry.register(ProxmoxActionTool())
    return registry
