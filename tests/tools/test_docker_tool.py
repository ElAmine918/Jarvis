import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.tools.docker_tool import DockerTool


@pytest.fixture
def tool():
    return DockerTool()


def _make_proc(stdout: bytes, stderr: bytes, returncode: int = 0):
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


def test_docker_tool_properties(tool):
    assert tool.name == "manage_docker"
    assert "conteneurs" in tool.description
    assert "action" in tool.parameters["required"]


@pytest.mark.asyncio
async def test_ps_success(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"container1   running", b"")
        res = await tool.execute(action="ps")
        assert "container1" in res


@pytest.mark.asyncio
async def test_ps_docker_error(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"", b"permission denied", returncode=1)
        res = await tool.execute(action="ps")
        assert "❌" in res


@pytest.mark.asyncio
async def test_missing_container_name_branches(tool):
    for act in ["logs", "inspect", "start", "restart", "stop", "rm"]:
        res = await tool.execute(action=act)
        assert "❌ 'container_name' requis" in res


@pytest.mark.asyncio
async def test_container_actions_success(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"OK", b"")

        res_logs = await tool.execute(action="logs", container_name="c1", lines=50)
        assert res_logs == "OK"

        res_inspect = await tool.execute(action="inspect", container_name="c1")
        assert res_inspect == "OK"

        for act in ["start", "restart", "stop", "rm"]:
            res = await tool.execute(action=act, container_name="c1")
            assert res == "OK"


@pytest.mark.asyncio
async def test_stats_with_and_without_container(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"CPU: 5%", b"")
        res_with = await tool.execute(action="stats", container_name="c1")
        assert "CPU: 5%" in res_with

        res_without = await tool.execute(action="stats")
        assert "CPU: 5%" in res_without


@pytest.mark.asyncio
async def test_compose_action(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"service_1 up", b"")
        res = await tool.execute(action="compose", command="up -d")
        assert "service_1 up" in res


@pytest.mark.asyncio
async def test_exec_no_command(tool):
    res = await tool.execute(action="exec", container_name="c")
    assert "❌" in res


@pytest.mark.asyncio
async def test_exec_success(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"total 8\ndrwxr-xr-x", b"")
        res = await tool.execute(action="exec", container_name="c", command="ls")
        assert "total" in res or "drwxr" in res


@pytest.mark.asyncio
async def test_exec_error(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"", b"command not found", returncode=127)
        res = await tool.execute(action="exec", container_name="c", command="badcmd")
        assert "❌" in res


@pytest.mark.asyncio
async def test_invalid_action(tool):
    res = await tool.execute(action="invalid_action")
    assert "❌" in res


@pytest.mark.asyncio
async def test_timeout(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"", b"")
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            res = await tool.execute(action="ps")
            assert "⏱️" in res


@pytest.mark.asyncio
async def test_exception_handling(tool):
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Connection refused")):
        res = await tool.execute(action="ps")
        assert "❌ Erreur d'exécution Docker" in res


@pytest.mark.asyncio
async def test_output_truncation(tool):
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = _make_proc(b"X" * 12000, b"")
        res = await tool.execute(action="ps")
        assert "tronqué" in res
