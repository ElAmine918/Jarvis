import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from jarvis.storage.vector_memory import generate_embedding, ingest_message, search_memory


@pytest.mark.asyncio
async def test_generate_embedding_gemini():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "embedding": {"values": [0.1] * 768}
    }

    with patch("jarvis.storage.vector_memory.GEMINI_API_KEY", "fake_key"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):
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

    with patch("jarvis.storage.vector_memory.GEMINI_API_KEY", ""), \
         patch("jarvis.storage.vector_memory.OLLAMA_LOCAL_URL", "http://ollama:11434"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):
        emb = await generate_embedding("Hello local")
        assert len(emb) == 768
        assert emb[0] == 0.2


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
