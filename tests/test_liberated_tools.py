import pytest
from jarvis.tools.shell import ShellTool
from jarvis.tools.filesystem import FileSystemTool
from jarvis.tools.docker_tool import DockerTool

@pytest.mark.asyncio
async def test_shell_tool_echo():
    tool = ShellTool()
    res = await tool.execute(command="echo 'jarvis_online'")
    assert "jarvis_online" in res

@pytest.mark.asyncio
async def test_filesystem_crud(tmp_path):
    tool = FileSystemTool()
    test_file = str(tmp_path / "test.txt")
    
    # Write
    w_res = await tool.execute(action="write", path=test_file, content="ligne 1\n")
    assert "✅" in w_res
    
    # Append
    a_res = await tool.execute(action="append", path=test_file, content="ligne 2\n")
    assert "✅" in a_res
    
    # Read
    r_res = await tool.execute(action="read", path=test_file)
    assert "ligne 1" in r_res
    assert "ligne 2" in r_res
    
    # Stat
    s_res = await tool.execute(action="stat", path=test_file)
    assert "Fichier" in s_res
    
    # Delete
    d_res = await tool.execute(action="delete", path=test_file)
    assert "✅" in d_res

def test_docker_tool_parameters():
    tool = DockerTool()
    actions = tool.parameters["properties"]["action"]["enum"]
    for act in ["ps", "logs", "inspect", "start", "restart", "stop", "rm", "stats", "exec", "compose"]:
        assert act in actions
