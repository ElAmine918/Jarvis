import pytest
from jarvis.tools.shell import ShellTool


@pytest.fixture
def shell():
    return ShellTool()


@pytest.mark.asyncio
async def test_shell_tool_echo(shell):
    res = await shell.execute(command="echo 'bonjour jarvis'")
    assert "bonjour jarvis" in res


@pytest.mark.asyncio
async def test_shell_tool_empty_command(shell):
    res = await shell.execute(command="")
    assert "Commande shell vide" in res


@pytest.mark.asyncio
async def test_shell_tool_dangerous_rm_rf(shell):
    res = await shell.execute(command="rm -rf /")
    assert "🚫 Sécurité" in res
    assert "Command" in res or "Commande interceptée" in res


@pytest.mark.asyncio
async def test_shell_tool_dangerous_fork_bomb(shell):
    res = await shell.execute(command=":(){ :|:& };:")
    assert "🚫 Sécurité" in res


@pytest.mark.asyncio
async def test_shell_tool_dangerous_reboot(shell):
    res = await shell.execute(command="reboot")
    assert "🚫 Sécurité" in res


@pytest.mark.asyncio
async def test_shell_tool_timeout(shell):
    res = await shell.execute(command="sleep 5", timeout=1)
    assert "Timeout" in res


@pytest.mark.asyncio
async def test_shell_tool_stderr_capture(shell):
    res = await shell.execute(command="ls /non_existent_folder_jarvis_test")
    assert "Code de retour" in res or "STDERR" in res or "No such file" in res
