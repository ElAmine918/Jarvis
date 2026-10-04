import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from jarvis.tools.docker_tool import DockerTool


@pytest.fixture
def tool():
    return DockerTool()


def _make_proc(stdout: bytes, stderr: bytes, returncode: int = 0):
    """Helper to create a properly async-mocked subprocess."""
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


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
async def test_logs_no_container(tool):
    res = await tool.execute(action="logs")
    assert "❌" in res


@pytest.mark.asyncio
async def test_inspect_no_container(tool):
    res = await tool.execute(action="inspect")
    assert "❌" in res


@pytest.mark.asyncio
async def test_start_no_container(tool):
    res = await tool.execute(action="start")
    assert "❌" in res


@pytest.mark.asyncio
async def test_rm_no_container(tool):
    res = await tool.execute(action="rm")
    assert "❌" in res


@pytest.mark.asyncio
async def test_exec_no_command(tool):
    res = await tool.execute(action="exec", container_name="c")
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
            assert "⏱️" in res or "❌" in res


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
async def test_exception_handling(tool):
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Connection refused")):
        res = await tool.execute(action="ps")
        assert "❌" in res
