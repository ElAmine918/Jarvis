from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.storage import logger_db
from jarvis.tools.memory_recall import MemoryRecallTool


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


def test_memory_recall_properties(recall_tool):
    assert recall_tool.name == "memory_recall"
    assert "query_type" in recall_tool.parameters["properties"]


@pytest.mark.asyncio
async def test_memory_recall_missing_db(recall_tool, monkeypatch):
    from jarvis.tools import memory_recall
    monkeypatch.setattr(memory_recall, "DB_PATH", "/non/existent/path.db")
    res = await recall_tool.execute(query_type="conversations")
    assert "introuvable" in res


@pytest.mark.asyncio
async def test_memory_recall_conversations(recall_tool):
    res = await recall_tool.execute(query_type="conversations", days=7)
    assert "Résultats de la mémoire pour 'conversations'" in res
    assert "Bonjour Monsieur" in res


@pytest.mark.asyncio
async def test_memory_recall_conversations_empty(recall_tool):
    # cutoff 0 days ago (or far future filter)
    res = await recall_tool.execute(query_type="conversations", days=-1)
    assert "Aucune conversation trouvée" in res


@pytest.mark.asyncio
async def test_memory_recall_actions(recall_tool):
    res = await recall_tool.execute(query_type="actions", days=7)
    assert "Résultats de la mémoire pour 'actions'" in res
    assert "execute_shell" in res


@pytest.mark.asyncio
async def test_memory_recall_actions_empty(recall_tool):
    res = await recall_tool.execute(query_type="actions", days=-1)
    assert "Aucune action trouvée" in res


@pytest.mark.asyncio
async def test_memory_recall_token_stats(recall_tool):
    res = await recall_tool.execute(query_type="token_stats", days=7)
    assert "Résultats de la mémoire pour 'token_stats'" in res
    assert "gemini-flash" in res
    assert "120" in res


@pytest.mark.asyncio
async def test_memory_recall_token_stats_empty(recall_tool):
    res = await recall_tool.execute(query_type="token_stats", days=-1)
    assert "Aucune donnée d'utilisation des tokens" in res


@pytest.mark.asyncio
async def test_memory_recall_search_missing_keyword(recall_tool):
    res = await recall_tool.execute(query_type="search", keyword="")
    assert "mot-clé est requis" in res


@pytest.mark.asyncio
async def test_memory_recall_search_semantic_success(recall_tool):
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()

    mock_results = [
        {"content": "Contenu sémantique retrouvé", "timestamp": "2026-10-04", "role": "assistant"}
    ]

    with (
        patch("jarvis.storage.vector_memory.get_db_pool", new_callable=AsyncMock) as mock_get_pool,
        patch("jarvis.storage.vector_memory.search_memory", new_callable=AsyncMock) as mock_search,
    ):
        mock_get_pool.return_value = mock_pool
        mock_search.return_value = mock_results

        res = await recall_tool.execute(query_type="search", keyword="recherche", days=7)
        assert "Contenu sémantique retrouvé" in res
        mock_pool.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_memory_recall_search_semantic_empty(recall_tool):
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()

    with (
        patch("jarvis.storage.vector_memory.get_db_pool", new_callable=AsyncMock) as mock_get_pool,
        patch("jarvis.storage.vector_memory.search_memory", new_callable=AsyncMock) as mock_search,
    ):
        mock_get_pool.return_value = mock_pool
        mock_search.return_value = []

        res = await recall_tool.execute(query_type="search", keyword="recherche_vide", days=7)
        assert "Aucun résultat trouvé pour 'recherche_vide'" in res


@pytest.mark.asyncio
async def test_memory_recall_search_fallback_sqlite(recall_tool):
    with patch("jarvis.storage.vector_memory.get_db_pool", side_effect=RuntimeError("PG down")):
        res = await recall_tool.execute(query_type="search", keyword="Bonjour", days=7)
        assert "Bonjour" in res


@pytest.mark.asyncio
async def test_memory_recall_invalid_query_type(recall_tool):
    res = await recall_tool.execute(query_type="invalid_type")
    assert "non reconnu" in res
