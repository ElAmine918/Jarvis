from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.storage.vector_memory import (
    generate_embedding,
    get_db_pool,
    ingest_message,
    init_connection,
    search_memory,
)


@pytest.mark.asyncio
async def test_init_connection():
    mock_conn = MagicMock()
    with patch("jarvis.storage.vector_memory.register_vector", new_callable=AsyncMock) as mock_reg:
        await init_connection(mock_conn)
        mock_reg.assert_awaited_once_with(mock_conn)


@pytest.mark.asyncio
async def test_get_db_pool():
    with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
        pool = await get_db_pool()
        mock_create_pool.assert_awaited_once()
        assert pool == mock_create_pool.return_value


@pytest.mark.asyncio
async def test_generate_embedding_gemini():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "embedding": {"values": [0.1] * 768}
    }

    with (
        patch("jarvis.storage.vector_memory.GEMINI_API_KEY", "fake_key"),
        patch("httpx.AsyncClient.post", return_value=mock_resp),
    ):
        emb = await generate_embedding("Hello Jarvis")
        assert len(emb) == 768
        assert emb[0] == 0.1


@pytest.mark.asyncio
async def test_generate_embedding_ollama_fallback():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [{"embedding": [0.2] * 768}]
    }

    with (
        patch("jarvis.storage.vector_memory.GEMINI_API_KEY", ""),
        patch("jarvis.storage.vector_memory.OLLAMA_LOCAL_URL", "http://ollama:11434"),
        patch("httpx.AsyncClient.post", return_value=mock_resp),
    ):
        emb = await generate_embedding("Hello local")
        assert len(emb) == 768
        assert emb[0] == 0.2


@pytest.mark.asyncio
async def test_generate_embedding_both_fail():
    with (
        patch("jarvis.storage.vector_memory.GEMINI_API_KEY", "fake_key"),
        patch("jarvis.storage.vector_memory.OLLAMA_LOCAL_URL", "http://ollama:11434"),
        patch("httpx.AsyncClient.post", side_effect=RuntimeError("Network offline")),
    ):
        with pytest.raises(Exception, match="Impossible de générer l'embedding"):
            await generate_embedding("Test fail")


@pytest.mark.asyncio
async def test_ingest_message_already_exists():
    fake_pool = MagicMock()
    fake_conn = AsyncMock()
    fake_cm = AsyncMock()
    fake_cm.__aenter__.return_value = fake_conn
    fake_pool.acquire.return_value = fake_cm

    fake_conn.fetchval.return_value = 42

    res = await ingest_message(
        fake_pool, "tg", "conv1", "msg1", "user", "Bonjour déjà présent", 1
    )
    assert res == 42
    fake_conn.fetchval.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_message_new_success():
    fake_pool = MagicMock()
    fake_conn = AsyncMock()
    fake_cm = AsyncMock()
    fake_cm.__aenter__.return_value = fake_conn
    fake_pool.acquire.return_value = fake_cm

    # 1st fetchval: exists -> None; 2nd fetchval: INSERT returning id -> 99
    fake_conn.fetchval.side_effect = [None, 99]

    with patch("jarvis.storage.vector_memory.generate_embedding", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = [0.5] * 768
        res = await ingest_message(
            fake_pool, "tg", "conv1", "msg2", "user", "Nouveau message", 2
        )
        assert res == 99
        fake_conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_message_embedding_error_still_returns_id():
    fake_pool = MagicMock()
    fake_conn = AsyncMock()
    fake_cm = AsyncMock()
    fake_cm.__aenter__.return_value = fake_conn
    fake_pool.acquire.return_value = fake_cm

    fake_conn.fetchval.side_effect = [None, 100]

    with patch("jarvis.storage.vector_memory.generate_embedding", side_effect=RuntimeError("Embedding API down")):
        res = await ingest_message(
            fake_pool, "tg", "conv1", "msg3", "user", "Message sans embedding", 3
        )
        assert res == 100


@pytest.mark.asyncio
async def test_search_memory_hybrid():
    fake_pool = MagicMock()
    fake_conn = AsyncMock()
    fake_cm = AsyncMock()
    fake_cm.__aenter__.return_value = fake_conn
    fake_pool.acquire.return_value = fake_cm

    fake_conn.fetch.return_value = [
        {
            "message_id": 1,
            "content": "Bonjour Amine",
            "message_ts": "2026-10-04T12:00:00",
            "conversation_id": "conv_1",
            "score": 0.95,
        }
    ]

    with patch("jarvis.storage.vector_memory.generate_embedding", return_value=[0.1] * 768):
        results = await search_memory(fake_pool, "Bonjour", limit=2)
        assert len(results) == 1
        assert results[0]["message_id"] == 1
        assert results[0]["content"] == "Bonjour Amine"
        assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_search_memory_embedding_fail():
    fake_pool = MagicMock()
    with patch("jarvis.storage.vector_memory.generate_embedding", side_effect=RuntimeError("Embedding fail")):
        results = await search_memory(fake_pool, "Query error")
        assert results == []
