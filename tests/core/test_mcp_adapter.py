import json
import os
from unittest.mock import patch
import pytest

from jarvis.core.mcp_adapter import DynamicMCPTool, get_mcp_config_path, load_mcp_servers
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


def test_load_mcp_servers_with_and_without_tools(tmp_path):
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
    count = load_mcp_servers(registry, config_path=str(cfg_file))
    assert count == 2
    assert "mcp_list_files" in registry._tools
    assert "mcp_empty_server" in registry._tools


def test_load_mcp_servers_missing_file():
    registry = ToolRegistry()
    count = load_mcp_servers(registry, config_path="/non_existent_file.json")
    assert count == 0


def test_load_mcp_servers_corrupted_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("NOT A VALID JSON", encoding="utf-8")
    registry = ToolRegistry()
    count = load_mcp_servers(registry, config_path=str(bad_file))
    assert count == 0


def test_get_mcp_config_path_env_var(tmp_path):
    custom_cfg = tmp_path / "custom_mcp.json"
    custom_cfg.write_text("{}", encoding="utf-8")
    with patch.dict(os.environ, {"MCP_CONFIG_PATH": str(custom_cfg)}):
        path = get_mcp_config_path()
        assert path == custom_cfg


def test_get_mcp_config_path_none():
    with (
        patch.dict(os.environ, {"MCP_CONFIG_PATH": ""}),
        patch("os.path.exists", return_value=False),
        patch("pathlib.Path.exists", return_value=False),
    ):
        path = get_mcp_config_path()
        assert path is None
