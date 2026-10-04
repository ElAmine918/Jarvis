from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.tools.deep_research import DeepResearchTool, _run_deep_research


@pytest.mark.asyncio
async def test_deep_research_execute_triggers_task():
    tool = DeepResearchTool()
    assert tool.name == "call_deep_research"
    assert "topic" in tool.parameters["required"]
    assert "recherche" in tool.description

    with patch("asyncio.create_task") as mock_create_task:
        res = await tool.execute(topic="Quantum Computing in 2026")
        assert "✅" in res
        assert "Quantum Computing in 2026" in res
        assert mock_create_task.called


@pytest.mark.asyncio
async def test_deep_research_missing_topic():
    tool = DeepResearchTool()
    res = await tool.execute(topic="")
    assert "Erreur" in res


@pytest.mark.asyncio
async def test_run_deep_research_no_user():
    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch("jarvis.tools.deep_research.ALLOWED_TELEGRAM_USER_IDS", []),
    ):
        await _run_deep_research("quantum")


@pytest.mark.asyncio
async def test_run_deep_research_success_chunks():
    mock_post = AsyncMock()
    mock_llm_resp = MagicMock()
    mock_llm_resp.status_code = 200
    # Create large report to test multi-chunk telegram sending (> 4000 chars)
    mock_llm_resp.json.return_value = {
        "choices": [{"message": {"content": "X" * 4500}}]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = [
        MagicMock(status_code=200),  # status msg
        mock_llm_resp,               # openrouter call
        MagicMock(status_code=200),  # chunk 1
        MagicMock(status_code=200),  # chunk 2
    ]

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch("jarvis.tools.deep_research.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        await _run_deep_research("AI Agents")
        assert mock_client.post.call_count >= 3


@pytest.mark.asyncio
async def test_run_deep_research_llm_error():
    mock_llm_resp = MagicMock()
    mock_llm_resp.status_code = 500

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = [
        MagicMock(status_code=200),  # status msg
        mock_llm_resp,               # openrouter call error
        MagicMock(status_code=200),  # chunk report error
    ]

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch("jarvis.tools.deep_research.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        await _run_deep_research("AI Agents")
        assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_run_deep_research_exception_handling():
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = [
        RuntimeError("Connection dropped"),
        MagicMock(status_code=200),
    ]

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch("jarvis.tools.deep_research.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        await _run_deep_research("Failing topic")
        assert mock_client.post.call_count == 2
