import pytest
from jarvis.tools.git_tool import GitTool


@pytest.fixture
def git_tool():
    return GitTool()


@pytest.mark.asyncio
async def test_git_tool_status(git_tool):
    res = await git_tool.execute(command="git status", working_dir=".")
    assert "On branch" in res or "sur la branche" in res or "working tree" in res or "code" in res


@pytest.mark.asyncio
async def test_git_tool_disallowed_subcommand(git_tool):
    res = await git_tool.execute(command="git archive master", working_dir=".")
    assert "🚫 Sécurité" in res
    assert "non autorisée" in res


@pytest.mark.asyncio
async def test_git_tool_dangerous_flag(git_tool):
    res = await git_tool.execute(command="git status --config=core.pager=cat", working_dir=".")
    assert "🚫 Sécurité" in res
    assert "interdite" in res


@pytest.mark.asyncio
async def test_git_tool_non_git_command(git_tool):
    res = await git_tool.execute(command="cat /etc/passwd", working_dir=".")
    assert "❌ Erreur" in res


@pytest.mark.asyncio
async def test_git_tool_forbidden_directory(git_tool):
    res = await git_tool.execute(command="git status", working_dir="/etc")
    assert "🚫 Sécurité" in res
