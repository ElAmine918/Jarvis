import pytest
from typing import Any
from jarvis.tools.base import Tool, ToolRegistry


class DummyTool(Tool):
    @property
    def name(self) -> str:
        return "dummy_tool"

    @property
    def description(self) -> str:
        return "A dummy tool for unit testing."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to echo"},
                "count": {"type": "integer", "description": "Repetition count"},
            },
            "required": ["message"],
        }

    async def execute(self, message: str, count: int = 1, fail: bool = False) -> str:
        if fail:
            raise RuntimeError("Simulation error")
        return f"{message} " * count


def test_tool_to_anthropic_format():
    tool = DummyTool()
    schema = tool.to_anthropic_format()
    assert schema["name"] == "dummy_tool"
    assert schema["description"] == "A dummy tool for unit testing."
    assert schema["input_schema"]["type"] == "object"
    assert "message" in schema["input_schema"]["properties"]
    assert "count" in schema["input_schema"]["properties"]
    assert schema["input_schema"]["required"] == ["message"]


@pytest.mark.asyncio
async def test_tool_registry_workflow():
    registry = ToolRegistry()
    dummy = DummyTool()

    # Register
    registry.register(dummy)
    assert registry.get_tool("dummy_tool") is dummy

    # Unknown tool raises ValueError
    with pytest.raises(ValueError, match="Outil inconnu : nonexistent"):
        registry.get_tool("nonexistent")

    # Format all tools
    anthropic_schemas = registry.get_all_tools_anthropic_format()
    assert len(anthropic_schemas) == 1
    assert anthropic_schemas[0]["name"] == "dummy_tool"

    # Execute successfully
    res = await registry.execute_tool("dummy_tool", {"message": "hello", "count": 2})
    assert res == "hello hello "

    # Execute with failure handled gracefully
    res_err = await registry.execute_tool("dummy_tool", {"message": "hello", "fail": True})
    assert "Erreur lors de l'exécution de l'outil dummy_tool : Simulation error" in res_err
