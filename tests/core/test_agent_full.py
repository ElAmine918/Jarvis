import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.core.agent import JarvisAgent, get_system_prompt, _resolve_data_dir


@pytest.fixture
def agent():
    return JarvisAgent()


def test_get_system_prompt_default():
    prompt = get_system_prompt()
    assert "Tu es Jarvis" in prompt


def test_get_system_prompt_from_file(tmp_path):
    prompt_file = tmp_path / "system_prompt.txt"
    prompt_file.write_text("Custom prompt content", encoding="utf-8")
    with patch("jarvis.core.agent._resolve_data_dir", return_value=tmp_path):
        assert get_system_prompt() == "Custom prompt content"


def test_get_system_prompt_read_error(tmp_path):
    prompt_file = tmp_path / "system_prompt.txt"
    prompt_file.write_text("Dummy", encoding="utf-8")
    with (
        patch("jarvis.core.agent._resolve_data_dir", return_value=tmp_path),
        patch("builtins.open", side_effect=IOError("Disk error")),
    ):
        prompt = get_system_prompt()
        assert "Tu es Jarvis" in prompt


def test_prepare_history_multimodal(agent):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Regarde cette photo"},
                {"type": "image_url", "image_url": {"url": "http://img.jpg"}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Generate a concise title"},
            ],
        },
    ]
    history = agent._prepare_history(messages, session_id="test")
    # Title generator message filtered out
    assert len(history) == 2
    assert isinstance(history[1]["content"], list)


@pytest.mark.asyncio
async def test_get_backends_for_different_models(agent):
    history = [{"role": "user", "content": "test"}]
    with patch("jarvis.core.agent.get_all_backends", new_callable=AsyncMock) as mock_all:
        mock_all.return_value = [
            ("Gemini (gemini-1.5-flash)", None, "gemini-1.5-flash"),
            ("OpenRouter (llama-3)", None, "or-model"),
            ("Ollama (llama)", None, "ollama-model"),
            ("LM Studio (Mac)", None, "mac-model"),
        ]

        b_auto = await agent._get_backends_for_model("jarvis-auto", history)
        assert len(b_auto) == 4

        b_gemini = await agent._get_backends_for_model("jarvis-gemini", history)
        assert len(b_gemini) == 1
        assert "Gemini" in b_gemini[0][0]

        b_or = await agent._get_backends_for_model("jarvis-openrouter", history)
        assert len(b_or) == 1
        assert "OpenRouter" in b_or[0][0]

        b_mac = await agent._get_backends_for_model("jarvis-mac", history)
        assert len(b_mac) == 1
        assert "LM Studio" in b_mac[0][0]

        b_ollama = await agent._get_backends_for_model("jarvis-ollama", history)
        assert len(b_ollama) == 1
        assert "Ollama" in b_ollama[0][0]


@pytest.mark.asyncio
async def test_agent_init(agent):
    agent.memory.init_db = AsyncMock()
    await agent.init()
    agent.memory.init_db.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_message_empty_history(agent):
    messages = []
    chunks = []
    async for c in agent.process_message(messages, session_id="test"):
        chunks.append(c)
    assert chunks == []


@pytest.mark.asyncio
async def test_process_message_no_backends_available(agent):
    messages = [{"role": "user", "content": "Hello"}]
    with patch.object(agent, "_get_backends_for_model", new_callable=AsyncMock) as mock_backends:
        mock_backends.return_value = []
        chunks = []
        async for c in agent.process_message(messages, session_id="test", requested_model="fake-model"):
            chunks.append(c)
        assert any("n'est pas en ligne" in c for c in chunks)


@pytest.mark.asyncio
async def test_process_message_all_backends_fail(agent):
    messages = [{"role": "user", "content": "Hello"}]
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))

    with (
        patch.object(agent, "_get_backends_for_model", new_callable=AsyncMock) as mock_backends,
        patch("jarvis.core.router.mark_model_dead") as mock_dead,
    ):
        mock_backends.return_value = [("Groq (llama)", mock_client, "llama")]
        chunks = []
        async for c in agent.process_message(messages, session_id="test"):
            chunks.append(c)
        assert any("Tous les backends ont échoué" in c for c in chunks)
        mock_dead.assert_called_once()


@pytest.mark.asyncio
async def test_process_message_simple_text_streaming(agent):
    messages = [{"role": "user", "content": "Bonjour"}]

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Bonjour ", tool_calls=None))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content="Amine !", tool_calls=None))]

    async def mock_stream(*args, **kwargs):
        yield chunk1
        yield chunk2

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=lambda *args, **kwargs: mock_stream())

    with patch.object(agent, "_get_backends_for_model", new_callable=AsyncMock) as mock_backends:
        mock_backends.return_value = [("Gemini (gemini-1.5-flash)", mock_client, "gemini-1.5-flash")]
        chunks = []
        async for c in agent.process_message(messages, session_id="test"):
            chunks.append(c)

        assert "".join(chunks) == "Bonjour Amine !"
        assert agent.last_backend_used == "gemini-1.5-flash"


@pytest.mark.asyncio
async def test_process_message_with_tool_call_flow(agent):
    messages = [{"role": "user", "content": "Quelle heure est-il ?"}]

    # 1st iteration: returns tool call
    mock_func = MagicMock()
    mock_func.name = "system_info"
    mock_func.arguments = '{"query": "time"}'

    tc_item = MagicMock()
    tc_item.index = 0
    tc_item.id = "call_time_123"
    tc_item.function = mock_func

    tc_chunk = MagicMock()
    tc_delta = MagicMock(content=None, tool_calls=[tc_item])
    tc_chunk.choices = [MagicMock(delta=tc_delta)]

    # 2nd iteration: returns final answer
    ans_chunk = MagicMock()
    ans_delta = MagicMock(content="Il est 15h30.", tool_calls=None)
    ans_chunk.choices = [MagicMock(delta=ans_delta)]

    async def iter1_stream(*args, **kwargs):
        yield tc_chunk

    async def iter2_stream(*args, **kwargs):
        yield ans_chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[iter1_stream(), iter2_stream()])

    agent.tool_registry.execute_tool = AsyncMock(return_value="Time: 15h30")

    with (
        patch.object(agent, "_get_backends_for_model", new_callable=AsyncMock) as mock_backends,
        patch("jarvis.storage.logger_db.log_action"),
    ):
        mock_backends.return_value = [("Gemini (gemini-1.5-flash)", mock_client, "gemini-1.5-flash")]
        chunks = []
        async for c in agent.process_message(messages, session_id="test"):
            chunks.append(c)

        full_output = "".join(chunks)
        assert "Exécution de system_info" in full_output
        assert "Il est 15h30." in full_output
        agent.tool_registry.execute_tool.assert_awaited_once_with("system_info", {"query": "time"})


@pytest.mark.asyncio
async def test_process_message_silent_model_forced_synthesis(agent):
    """Vérifie que lorsqu'un modèle devient muet après avoir exécuté des outils,
    une passe de synthèse forcée est déclenchée pour garantir un retour complet à Monsieur."""
    messages = [{"role": "user", "content": "Vérifie le conteneur"}]

    mock_func = MagicMock()
    mock_func.name = "execute_shell_command"
    mock_func.arguments = '{"command": "docker ps"}'

    tc_item = MagicMock()
    tc_item.index = 0
    tc_item.id = "call_docker_1"
    tc_item.function = mock_func

    tc_chunk = MagicMock()
    tc_delta = MagicMock(content=None, tool_calls=[tc_item])
    tc_chunk.choices = [MagicMock(delta=tc_delta)]

    # 2nd iteration: model finishes silently (content is empty)
    silent_chunk = MagicMock()
    silent_delta = MagicMock(content="", tool_calls=None)
    silent_chunk.choices = [MagicMock(delta=silent_delta)]

    # 3rd call (forced synthesis pass): generates the final Claude/Gemini-style answer
    synth_chunk = MagicMock()
    synth_delta = MagicMock(content="Monsieur, le conteneur Caddy est opérationnel sur le port 80.", tool_calls=None)
    synth_chunk.choices = [MagicMock(delta=synth_delta)]

    async def iter1_stream(*args, **kwargs):
        yield tc_chunk

    async def iter2_stream(*args, **kwargs):
        yield silent_chunk

    async def synth_stream(*args, **kwargs):
        yield synth_chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[iter1_stream(), iter2_stream(), synth_stream()])

    agent.tool_registry.execute_tool = AsyncMock(return_value="CONTAINER ID: 1234 caddy Up 2 hours")

    with (
        patch.object(agent, "_get_backends_for_model", new_callable=AsyncMock) as mock_backends,
        patch("jarvis.storage.logger_db.log_action"),
    ):
        mock_backends.return_value = [("Groq (qwen)", mock_client, "qwen")]
        chunks = []
        async for c in agent.process_message(messages, session_id="test"):
            chunks.append(c)

        full_output = "".join(chunks)
        assert "execute_shell_command : docker ps" in full_output
        assert "Monsieur, le conteneur Caddy est opérationnel" in full_output
