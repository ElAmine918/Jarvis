import pytest
import re
from unittest.mock import patch, AsyncMock
from jarvis.tools.knowledge_tool import KnowledgeBaseTool


@pytest.fixture
def tool():
    return KnowledgeBaseTool()


@pytest.mark.asyncio
async def test_save_fact_success(tool):
    with patch("jarvis.storage.memory.MemoryManager.save_fact", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = "OK"
        res = await tool.execute(action="save_fact", key="my_key", value="my_val")
        assert "✅" in res


@pytest.mark.asyncio
async def test_save_fact_no_value(tool):
    res = await tool.execute(action="save_fact", key="my_key")
    assert "❌" in res


@pytest.mark.asyncio
async def test_get_fact_success(tool):
    with patch("jarvis.storage.memory.MemoryManager.get_fact", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "my_val"
        res = await tool.execute(action="get_fact", key="my_key")
        assert "my_val" in res


@pytest.mark.asyncio
async def test_get_fact_not_found(tool):
    with patch("jarvis.storage.memory.MemoryManager.get_fact", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        res = await tool.execute(action="get_fact", key="my_key")
        assert "❌" in res


@pytest.mark.asyncio
async def test_invalid_action(tool):
    res = await tool.execute(action="invalid", key="my_key")
    assert "❌" in res


@pytest.mark.asyncio
async def test_empty_key_after_sanitize(tool):
    # "@@@" after sanitization becomes "" → should fail gracefully
    res = await tool.execute(action="get_fact", key="@@@")
    assert "❌" in res


@pytest.mark.asyncio
async def test_save_fact_exception(tool):
    with patch("jarvis.storage.memory.MemoryManager.save_fact", side_effect=Exception("DB Error")):
        res = await tool.execute(action="save_fact", key="my_key", value="val")
        assert "❌" in res


@pytest.mark.asyncio
async def test_get_fact_exception(tool):
    with patch("jarvis.storage.memory.MemoryManager.get_fact", side_effect=Exception("DB Error")):
        res = await tool.execute(action="get_fact", key="my_key")
        assert "❌" in res


@pytest.mark.asyncio
async def test_key_sanitization_result(tool):
    """Verify that special chars are stripped and the sanitized key is actually used."""
    with patch("jarvis.storage.memory.MemoryManager.get_fact", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "val"
        await tool.execute(action="get_fact", key="my key with $!")
        # After re.sub(r'[^a-z0-9_]', '_', ...) then strip('_')
        # "my key with $!" → "my_key_with___" → strip('_') → "my_key_with"
        actual_key = mock_get.call_args[0][0]
        # Must be alphanumeric + underscores only, no leading/trailing underscores
        assert re.match(r'^[a-z0-9][a-z0-9_]*[a-z0-9]$|^[a-z0-9]$', actual_key), \
            f"Sanitized key '{actual_key}' is not clean"


@pytest.mark.asyncio
async def test_key_lowercased(tool):
    """Keys must always be stored lowercase."""
    with patch("jarvis.storage.memory.MemoryManager.save_fact", new_callable=AsyncMock) as mock_save:
        mock_save.return_value = "OK"
        await tool.execute(action="save_fact", key="MyUpperKey", value="val")
        actual_key = mock_save.call_args[0][0]
        assert actual_key == actual_key.lower(), f"Key '{actual_key}' is not lowercase"
