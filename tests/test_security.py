import pytest
from jarvis.tools.filesystem import FileSystemTool

@pytest.mark.asyncio
async def test_absolute_outside_workspace_blocked():
    tool = FileSystemTool()
    res = await tool.execute(action="list", path="/etc")
    assert "interdit" in res.lower()

@pytest.mark.asyncio
async def test_workspace_path_allowed():
    tool = FileSystemTool()
    res = await tool.execute(action="list", path="/app/workspace")
    assert "interdit" not in res.lower()

@pytest.mark.asyncio
async def test_tools_path_allowed():
    tool = FileSystemTool()
    res = await tool.execute(action="list", path="/app/jarvis/tools")
    assert "interdit" not in res.lower()
