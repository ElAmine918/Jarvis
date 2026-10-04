import json
import pytest
from jarvis.core.mcp_adapter import DynamicMCPTool, load_mcp_servers
from jarvis.tools.base import ToolRegistry


@pytest.mark.asyncio
async def test_dynamic_mcp_tool_execution():
    tool = DynamicMCPTool(
        name="test_tool",
        description="A test MCP tool",
        parameters={"type": "object", "properties": {"arg1": {"type": "string"}}},
        server_name="test_server",
    )
    assert tool.name == "test_tool"
    assert "[MCP: test_server]" in tool.description

    res = await tool.execute(arg1="val1")
    assert "test_server" in res
    assert "test_tool" in res
    assert "val1" in res


@pytest.mark.asyncio
async def test_dynamic_mcp_tool_custom_handler():
    async def custom_h(x: int):
        return f"Result: {x * 2}"

    tool = DynamicMCPTool(
        name="double_it",
        description="Doubles input",
        parameters={"type": "object"},
        server_name="calc_server",
        handler=custom_h,
    )
    res = await tool.execute(x=21)
    assert res == "Result: 42"


def test_load_mcp_servers(tmp_path):
    config = {
        "mcpServers": {
            "filesystem_server": {
                "tools": [
                    {
                        "name": "mcp_list_files",
                        "description": "Lists files on remote MCP server",
                        "parameters": {"type": "object", "properties": {"dir": {"type": "string"}}},
                    }
                ]
            },
            "empty_server": {
                "tools": []
            }
        }
    }
    cfg_file = tmp_path / "mcp_servers.json"
    cfg_file.write_text(json.dumps(config), encoding="utf-8")

    registry = ToolRegistry()
    loaded_count = load_mcp_servers(registry, config_path=str(cfg_file))
    assert loaded_count == 2
    assert "mcp_list_files" in registry._tools
    assert "mcp_empty_server" in registry._tools
