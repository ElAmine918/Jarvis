from unittest.mock import patch
import pytest
from jarvis.tools.self_improve import SelfImproveTool


@pytest.fixture
def self_improve():
    return SelfImproveTool()


@pytest.mark.asyncio
async def test_self_improve_missing_params(self_improve):
    res = await self_improve.execute(tool_name="", code="")
    assert "requis" in res


@pytest.mark.asyncio
async def test_self_improve_syntax_error(self_improve):
    invalid_code = "class MyTool:\n  def broken(:"
    res = await self_improve.execute(tool_name="broken_tool", code=invalid_code)
    assert "Erreur de syntaxe Python" in res


@pytest.mark.asyncio
async def test_self_improve_no_class_defined(self_improve):
    functions_only_code = "def standalone_func(): pass"
    res = await self_improve.execute(tool_name="no_class_tool", code=functions_only_code)
    assert "le code ne contient aucune classe définie" in res


@pytest.mark.asyncio
async def test_self_improve_valid_tool_creation(self_improve, tmp_path, monkeypatch):
    import os

    valid_code = """
from jarvis.tools.base import Tool

class DummyNewTool(Tool):
    @property
    def name(self) -> str: return "dummy_tool"
    @property
    def description(self) -> str: return "A dummy tool"
    @property
    def parameters(self) -> dict: return {"type": "object", "properties": {}}
    async def execute(self, **kwargs) -> str: return "Dummy executed"
"""
    dest_file = os.path.abspath("src/jarvis/tools/dummy_tool.py")
    try:
        res = await self_improve.execute(tool_name="dummy_tool", code=valid_code)
        assert "validé" in res or "enregistré" in res or "installé" in res
    finally:
        if os.path.exists(dest_file):
            os.remove(dest_file)


@pytest.mark.asyncio
async def test_self_improve_write_error(self_improve):
    valid_code = "class ValidTool:\n    pass"
    with patch("pathlib.Path.write_text", side_effect=IOError("Permission denied")):
        res = await self_improve.execute(tool_name="tool_fail", code=valid_code)
        assert "❌ Erreur lors de l'écriture" in res


def test_self_improve_properties(self_improve):
    assert self_improve.name == "self_improve_pipeline"
    assert "Tool" in self_improve.description
    assert "tool_name" in self_improve.parameters["properties"]

