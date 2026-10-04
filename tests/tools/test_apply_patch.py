import pytest
from jarvis.tools.apply_patch import ApplyPatchTool


@pytest.fixture
def patch_tool():
    return ApplyPatchTool()


@pytest.mark.asyncio
async def test_apply_patch_forbidden_path(patch_tool):
    res = await patch_tool.execute(
        file_path="/etc/passwd",
        search_text="root",
        replace_text="admin",
    )
    assert "🚫 Sécurité" in res


@pytest.mark.asyncio
async def test_apply_patch_search_not_found(patch_tool, tmp_path):
    target = tmp_path / "code.py"
    target.write_text("x = 1\ny = 2\n", encoding="utf-8")

    res = await patch_tool.execute(
        file_path=str(target),
        search_text="z = 3",
        replace_text="z = 4",
    )
    assert "Erreur" in res
    assert "n'a pas été trouvé" in res


@pytest.mark.asyncio
async def test_apply_patch_success(patch_tool, tmp_path):
    target = tmp_path / "code.py"
    target.write_text("def hello():\n    print('old')\n", encoding="utf-8")

    res = await patch_tool.execute(
        file_path=str(target),
        search_text="print('old')",
        replace_text="print('new')",
    )
    assert "✅" in res
    assert "patché avec succès" in res
    assert "print('new')" in target.read_text(encoding="utf-8")
