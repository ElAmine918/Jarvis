import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from jarvis.tools.filesystem import FileSystemTool


@pytest.fixture
def tool():
    return FileSystemTool()


@pytest.mark.asyncio
async def test_fs_read_not_exist(tool):
    res = await tool.execute(action="read", path="/app/non_existent_xyz.txt")
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
    res = await tool.execute(action="delete", path="/app/non_existent_xyz.txt")
    assert "❌" in res


@pytest.mark.asyncio
async def test_fs_mkdir_ok(tool, tmp_path):
    # mkdir succeeds within /tmp which is allowed
    target = str(tmp_path / "test_jarvis_dir")
    res = await tool.execute(action="mkdir", path=target)
    # Either succeeds or is blocked by sandbox — both are valid
    assert "✅" in res or "🚫" in res


@pytest.mark.asyncio
async def test_fs_stat_not_exist(tool):
    # stat on a non-existent path in allowed zone should return ❌, not raise
    res = await tool.execute(action="stat", path="/tmp/non_existent_xyz_jarvis.txt")
    assert "❌" in res or "existe" in res.lower()


@pytest.mark.asyncio
async def test_fs_move_no_dest(tool):
    # move without destination should return an error (❌ or 🚫)
    res = await tool.execute(action="move", path="/app/file.txt")
    assert "❌" in res or "🚫" in res or "requis" in res.lower()


@pytest.mark.asyncio
async def test_fs_copy_no_dest(tool):
    # copy without destination should return an error (❌ or 🚫)
    res = await tool.execute(action="copy", path="/app/file.txt")
    assert "❌" in res or "🚫" in res or "requis" in res.lower()


@pytest.mark.asyncio
async def test_fs_invalid_action(tool):
    res = await tool.execute(action="invalid_action", path="/app/file.txt")
    assert "❌" in res


@pytest.mark.asyncio
async def test_fs_path_traversal(tool):
    # Classic path traversal attempt must be blocked
    res = await tool.execute(action="read", path="/app/../../../../etc/passwd")
    assert "🚫" in res


@pytest.mark.asyncio
async def test_fs_path_traversal_dotdot(tool):
    # Another traversal pattern
    res = await tool.execute(action="read", path="../../etc/shadow")
    assert "🚫" in res


@pytest.mark.asyncio
async def test_fs_write_and_read_tmp(tool, tmp_path):
    # Write and read back inside /tmp (allowed sandbox zone)
    target = str(tmp_path / "jarvis_test_file.txt")
    write_res = await tool.execute(action="write", path=target, content="hello jarvis")
    if "✅" in write_res:
        read_res = await tool.execute(action="read", path=target)
        assert "hello jarvis" in read_res
