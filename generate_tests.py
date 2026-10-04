import os

TESTS_DIR = "/Users/amine/Code/Jarvis/tests"

# --- tests/tools/test_knowledge_tool.py ---
with open(f"{TESTS_DIR}/tools/test_knowledge_tool.py", "w") as f:
    f.write('''import pytest
from unittest.mock import patch, MagicMock
from jarvis.tools.knowledge_tool import KnowledgeBaseTool

@pytest.fixture
def tool():
    return KnowledgeBaseTool()

@pytest.mark.asyncio
async def test_save_fact_success(tool):
    with patch("jarvis.storage.memory.MemoryManager.save_fact") as mock_save:
        mock_save.return_value = "Success"
        res = await tool.execute(action="save_fact", key="my_key", value="my_val")
        assert "✅" in res

@pytest.mark.asyncio
async def test_save_fact_no_value(tool):
    res = await tool.execute(action="save_fact", key="my_key")
    assert "❌" in res

@pytest.mark.asyncio
async def test_get_fact_success(tool):
    with patch("jarvis.storage.memory.MemoryManager.get_fact") as mock_get:
        mock_get.return_value = "my_val"
        res = await tool.execute(action="get_fact", key="my_key")
        assert "my_val" in res

@pytest.mark.asyncio
async def test_get_fact_not_found(tool):
    with patch("jarvis.storage.memory.MemoryManager.get_fact") as mock_get:
        mock_get.return_value = None
        res = await tool.execute(action="get_fact", key="my_key")
        assert "❌" in res

@pytest.mark.asyncio
async def test_invalid_action(tool):
    res = await tool.execute(action="invalid", key="my_key")
    assert "❌" in res

@pytest.mark.asyncio
async def test_empty_key_after_sanitize(tool):
    res = await tool.execute(action="get_fact", key="@@@")
    assert "❌" in res

@pytest.mark.asyncio
async def test_save_fact_exception(tool):
    with patch("jarvis.storage.memory.MemoryManager.save_fact", side_effect=Exception("DB Error")):
        res = await tool.execute(action="save_fact", key="my_key", value="val")
        assert "❌" in res

@pytest.mark.asyncio
async def test_get_fact_exception(tool):
    with patch("jarvis.storage.memory.MemoryManager.get_fact", side_effect=Exception("DB Error")):
        res = await tool.execute(action="get_fact", key="my_key")
        assert "❌" in res

@pytest.mark.asyncio
async def test_key_sanitization(tool):
    with patch("jarvis.storage.memory.MemoryManager.get_fact") as mock_get:
        mock_get.return_value = "val"
        await tool.execute(action="get_fact", key="my key with $!")
        mock_get.assert_called_with("my_key_with___")
''')

# --- tests/tools/test_filesystem.py ---
with open(f"{TESTS_DIR}/tools/test_filesystem.py", "w") as f:
    f.write('''import pytest
from pathlib import Path
from jarvis.tools.filesystem import FileSystemTool

@pytest.fixture
def tool(): return FileSystemTool()

@pytest.mark.asyncio
async def test_fs_read_not_exist(tool):
    res = await tool.execute(action="read", path="/app/non_existent.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_write_no_content(tool):
    res = await tool.execute(action="write", path="/app/file.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_append_no_content(tool):
    res = await tool.execute(action="append", path="/app/file.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_delete_not_exist(tool):
    res = await tool.execute(action="delete", path="/app/non_existent.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_mkdir_ok(tool, tmp_path):
    res = await tool.execute(action="mkdir", path=str(tmp_path / "test_dir"))
    assert "✅" in res or "🚫" in res

@pytest.mark.asyncio
async def test_fs_stat_not_exist(tool):
    res = await tool.execute(action="stat", path="/app/non_existent.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_move_no_dest(tool):
    res = await tool.execute(action="move", path="/app/file.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_copy_no_dest(tool):
    res = await tool.execute(action="copy", path="/app/file.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_invalid_action(tool):
    res = await tool.execute(action="invalid_action", path="/app/file.txt")
    assert "❌" in res

@pytest.mark.asyncio
async def test_fs_path_traversal(tool):
    res = await tool.execute(action="read", path="/app/../../../../etc/passwd")
    assert "🚫" in res
''')

# --- tests/tools/test_docker_tool.py ---
with open(f"{TESTS_DIR}/tools/test_docker_tool.py", "w") as f:
    f.write('''import pytest
from unittest.mock import patch, MagicMock
from jarvis.tools.docker_tool import DockerTool

@pytest.fixture
def tool(): return DockerTool()

@pytest.mark.asyncio
async def test_ps(tool):
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        proc = MagicMock()
        proc.communicate.return_value = (b"ok", b"")
        proc.returncode = 0
        mock_exec.return_value = proc
        res = await tool.execute(action="ps")
        assert "ok" in res

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
    res = await tool.execute(action="invalid")
    assert "❌" in res

@pytest.mark.asyncio
async def test_timeout(tool):
    with patch("asyncio.wait_for", side_effect=Exception("timeout")):
        res = await tool.execute(action="ps")
        assert "❌" in res

@pytest.mark.asyncio
async def test_exec_success(tool):
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        proc = MagicMock()
        proc.communicate.return_value = (b"out", b"")
        proc.returncode = 0
        mock_exec.return_value = proc
        res = await tool.execute(action="exec", container_name="c", command="ls")
        assert "out" in res

@pytest.mark.asyncio
async def test_exec_error(tool):
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        proc = MagicMock()
        proc.communicate.return_value = (b"", b"err")
        proc.returncode = 1
        mock_exec.return_value = proc
        res = await tool.execute(action="exec", container_name="c", command="ls")
        assert "❌" in res
''')

# Create a small script for the rest of them
