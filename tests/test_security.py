"""
Tests de sécurité adverses mis à jour pour les outils v4.
"""
import asyncio
import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.tools.filesystem import FileSystemTool, _safe_path, WORKSPACE
from jarvis.tools.docker_tool import DockerTool, _validate_name
from jarvis.tools.shell import ShellTool


class TestShellDisabled:
    @pytest.mark.asyncio
    async def test_shell_is_disabled(self):
        tool = ShellTool()
        result = await tool.execute(command="ls /")
        assert "désactivé" in result.lower() or "DÉSACTIVÉ" in result


class TestFilesystemSecurity:
    def test_dotdot_blocked(self):
        assert _safe_path("../../etc/passwd") is None

    def test_absolute_outside_workspace_blocked(self):
        resolved = _safe_path("/etc/passwd")
        if resolved is not None:
            assert resolved.is_relative_to(WORKSPACE)

    def test_workspace_path_allowed(self):
        assert _safe_path("test.txt").is_relative_to(WORKSPACE)

    @pytest.mark.asyncio
    async def test_read_etc_passwd_blocked(self):
        tool = FileSystemTool()
        result = await tool.execute(action="read", path="../../etc/passwd")
        assert "🚫" in result or "interdit" in result.lower()

    @pytest.mark.asyncio
    async def test_cwd_root_blocked(self):
        tool = FileSystemTool()
        result = await tool.execute(action="list", path="/")
        assert "etc" not in result and "bin" not in result or "🚫" in result


class TestDockerSecurity:
    def test_injection_semicolon(self):
        assert _validate_name("x; rm -rf /app") is not None

    def test_option_injection_dash(self):
        assert _validate_name("-f") is not None

    def test_valid_name_allowed(self):
        assert _validate_name("my-container") is None

    @pytest.mark.asyncio
    async def test_rm_action_removed(self):
        tool = DockerTool()
        result = await tool.execute(action="rm", container_name="jarvis")
        assert "Action inconnue" in result or "❌" in result

    @pytest.mark.asyncio
    async def test_compose_up_removed(self):
        tool = DockerTool()
        result = await tool.execute(action="compose-up")
        assert "Action inconnue" in result or "❌" in result

    @pytest.mark.asyncio
    async def test_stop_unmanageable_container_blocked(self):
        tool = DockerTool()
        async def mock_is_manageable(name):
            return False
        tool._is_manageable = mock_is_manageable
        result = await tool.execute(action="stop", container_name="system-db")
        assert "bloquée" in result or "manuellement" in result.lower()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
