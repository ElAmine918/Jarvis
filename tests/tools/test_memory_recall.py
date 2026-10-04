import pytest
from jarvis.tools.memory_recall import MemoryRecallTool
from jarvis.storage import logger_db


@pytest.fixture
def recall_tool(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_recall_logs.db")
    monkeypatch.setattr(logger_db, "DB_PATH", test_db)
    logger_db.init_db()

    # Pre-populate sample data
    logger_db.log_conversation("sess_1", "telegram", "123", "Bonjour", "Bonjour Monsieur", "gemini-flash")
    logger_db.log_action("sess_1", "execute_shell", {"command": "uptime"}, "up 2 hours", "gemini-flash")
    logger_db.log_token_usage("gemini-flash", 120)

    from jarvis.tools import memory_recall
    monkeypatch.setattr(memory_recall, "DB_PATH", test_db)

    return MemoryRecallTool()


@pytest.mark.asyncio
async def test_memory_recall_conversations(recall_tool):
    res = await recall_tool.execute(query_type="conversations", days=7)
    assert "Résultats de la mémoire pour 'conversations'" in res
    assert "Bonjour Monsieur" in res


@pytest.mark.asyncio
async def test_memory_recall_actions(recall_tool):
    res = await recall_tool.execute(query_type="actions", days=7)
    assert "Résultats de la mémoire pour 'actions'" in res
    assert "execute_shell" in res


@pytest.mark.asyncio
async def test_memory_recall_token_stats(recall_tool):
    res = await recall_tool.execute(query_type="token_stats", days=7)
    assert "Résultats de la mémoire pour 'token_stats'" in res
    assert "gemini-flash" in res
    assert "120" in res


@pytest.mark.asyncio
async def test_memory_recall_search_fallback(recall_tool):
    res = await recall_tool.execute(query_type="search", keyword="Bonjour", days=7)
    assert "Bonjour" in res


@pytest.mark.asyncio
async def test_memory_recall_invalid_query_type(recall_tool):
    res = await recall_tool.execute(query_type="invalid_type")
    assert "non reconnu" in res
