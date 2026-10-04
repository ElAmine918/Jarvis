from pathlib import Path
import pytest

from jarvis.tools.filesystem import FileSystemTool


@pytest.fixture
def tool():
    return FileSystemTool()


def test_filesystem_properties(tool):
    assert tool.name == "manage_files"
    assert "fichiers" in tool.description.lower()
    assert "action" in tool.parameters["required"]


@pytest.mark.asyncio
async def test_fs_read_not_exist(tool):
    res = await tool.execute(action="read", path="/app/non_existent_xyz.txt")
    assert "❌" in res or "introuvable" in res


@pytest.mark.asyncio
async def test_fs_write_no_content(tool):
    res = await tool.execute(action="write", path="/tmp/file.txt")
    assert "❌" in res


@pytest.mark.asyncio
async def test_fs_append_no_content(tool):
    res = await tool.execute(action="append", path="/tmp/file.txt")
    assert "❌" in res


@pytest.mark.asyncio
async def test_fs_delete_not_exist(tool):
    res = await tool.execute(action="delete", path="/tmp/non_existent_xyz.txt")
    assert "❌" in res


@pytest.mark.asyncio
async def test_fs_mkdir_and_stat(tool, tmp_path):
    target_dir = str(tmp_path / "test_dir")
    res_mkdir = await tool.execute(action="mkdir", path=target_dir)
    assert "✅" in res_mkdir

    res_stat = await tool.execute(action="stat", path=target_dir)
    assert "Dossier" in res_stat


@pytest.mark.asyncio
async def test_fs_stat_not_exist(tool):
    res = await tool.execute(action="stat", path="/tmp/non_existent_xyz_jarvis.txt")
    assert "❌" in res


@pytest.mark.asyncio
async def test_fs_move_and_copy(tool, tmp_path):
    src_file = tmp_path / "src.txt"
    src_file.write_text("content to move", encoding="utf-8")

    # Move without dest
    res_no_dest = await tool.execute(action="move", path=str(src_file))
    assert "🚫" in res_no_dest

    # Move with dest
    dest_file = tmp_path / "dest.txt"
    res_move = await tool.execute(action="move", path=str(src_file), dest_path=str(dest_file))
    assert "✅ Déplacé" in res_move
    assert dest_file.exists()

    # Copy without dest
    res_copy_no_dest = await tool.execute(action="copy", path=str(dest_file))
    assert "🚫" in res_copy_no_dest

    # Copy file with dest
    copied_file = tmp_path / "copied.txt"
    res_copy = await tool.execute(action="copy", path=str(dest_file), dest_path=str(copied_file))
    assert "✅ Copié" in res_copy
    assert copied_file.exists()


@pytest.mark.asyncio
async def test_fs_copy_directory(tool, tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    (sub_dir / "file.txt").write_text("hello", encoding="utf-8")

    dest_dir = tmp_path / "destdir"
    res_copy_dir = await tool.execute(action="copy", path=str(sub_dir), dest_path=str(dest_dir))
    assert "✅ Copié" in res_copy_dir
    assert (dest_dir / "file.txt").exists()


@pytest.mark.asyncio
async def test_fs_list_and_line_slicing(tool, tmp_path):
    f = tmp_path / "lines.txt"
    f.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5", encoding="utf-8")

    # Test list
    res_list = await tool.execute(action="list", path=str(tmp_path))
    assert "lines.txt" in res_list

    # Test read with line slicing
    res_read_slice = await tool.execute(action="read", path=str(f), start_line=2, end_line=4)
    assert "Line 2\nLine 3\nLine 4" in res_read_slice
    assert "Line 1" not in res_read_slice

    # Test append
    res_append = await tool.execute(action="append", path=str(f), content="\nLine 6")
    assert "✅ Ajouté" in res_append
    assert "Line 6" in f.read_text(encoding="utf-8")

    # Test delete file
    res_del_file = await tool.execute(action="delete", path=str(f))
    assert "✅ Supprimé" in res_del_file

    # Test delete directory
    dummy_dir = tmp_path / "to_delete"
    dummy_dir.mkdir()
    res_del_dir = await tool.execute(action="rm", path=str(dummy_dir))
    assert "✅ Supprimé" in res_del_dir


@pytest.mark.asyncio
async def test_fs_read_truncation(tool, tmp_path):
    big_file = tmp_path / "big.txt"
    big_file.write_text("A" * 15000, encoding="utf-8")
    res = await tool.execute(action="read", path=str(big_file))
    assert "tronqué" in res


@pytest.mark.asyncio
async def test_fs_path_traversal(tool):
    res = await tool.execute(action="read", path="/app/../../../../etc/passwd")
    assert "🚫" in res

    res_dot = await tool.execute(action="read", path="../../etc/shadow")
    assert "🚫" in res


@pytest.mark.asyncio
async def test_fs_invalid_action(tool, tmp_path):
    res = await tool.execute(action="invalid_cmd", path=str(tmp_path))
    assert "Action inconnue" in res
