import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jarvis.core.agent import JarvisAgent


@pytest.mark.asyncio
async def test_agent_process_message_stream():
    agent = JarvisAgent()
    await agent.init()

    # Create mock streaming chunk
    mock_chunk = MagicMock()
    mock_choice = MagicMock()
    mock_delta = MagicMock()
    mock_delta.content = "Bonjour Monsieur, tout est nominal."
    mock_delta.tool_calls = None
    mock_choice.delta = mock_delta
    mock_chunk.choices = [mock_choice]

    async def mock_stream(*args, **kwargs):
        yield mock_chunk

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_stream)

    fake_backends = [("Mock Backend", mock_client, "mock-model")]

    with patch.object(agent, "_get_backends_for_model", return_value=fake_backends):
        messages = [{"role": "user", "content": "Statut du système"}]
        chunks = []
        async for chunk in agent.process_message(messages, session_id="test_session"):
            chunks.append(chunk)

        full_response = "".join(chunks)
        assert "Bonjour Monsieur" in full_response
        assert agent.last_backend_used == "mock-model"


@pytest.mark.asyncio
async def test_agent_all_backends_offline():
    agent = JarvisAgent()
    with patch.object(agent, "_get_backends_for_model", return_value=[]):
        messages = [{"role": "user", "content": "Bonjour"}]
        chunks = []
        async for chunk in agent.process_message(messages, requested_model="jarvis-gemini"):
            chunks.append(chunk)
        assert any("n'est pas en ligne" in c for c in chunks)
