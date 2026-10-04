import pytest
from jarvis.core.agent import JarvisAgent


@pytest.fixture
def agent():
    return JarvisAgent()


def test_skill_and_rule_injection_in_system_prompt(agent):
    messages = [
        {"role": "user", "content": "Salut Jarvis, fais un code review de ce script s'il te plaît : print('hello')"}
    ]
    history = agent._prepare_history(messages, session_id="test")

    system_prompt = history[0]["content"]
    assert "règles actives" in system_prompt.lower()
    assert "tu dois être poli" in system_prompt.lower()
    # Code review skill triggered by "révise ce code"
    assert "code review" in system_prompt.lower() or "workflow" in system_prompt.lower()


def test_telegram_interface_prompt_adaptation(agent):
    messages = [{"role": "user", "content": "Bonjour"}]
    history_telegram = agent._prepare_history(messages, session_id="telegram_123")
    assert "[INTERFACE: TELEGRAM]" in history_telegram[0]["content"]
    assert "N'UTILISEZ AUCUN FORMATAGE MARKDOWN" in history_telegram[0]["content"]

    history_webui = agent._prepare_history(messages, session_id="open-webui")
    assert "[INTERFACE: OPEN WEBUI]" in history_webui[0]["content"]
    assert "Utilisez pleinement le formatage Markdown" in history_webui[0]["content"]


def test_filter_open_webui_system_and_meta_messages(agent):
    messages = [
        {"role": "system", "content": "System directive"},
        {"role": "user", "content": "Generate a concise title for this chat"},
        {"role": "user", "content": "follow_ups question"},
        {"role": "user", "content": "Vraie question de l'utilisateur"},
    ]
    history = agent._prepare_history(messages, session_id="test")
    # Only the dynamic system prompt + the genuine user question should remain
    assert len(history) == 2
    assert history[1]["content"] == "Vraie question de l'utilisateur"


def test_build_tools_openai_format(agent):
    tools = agent._build_tools_openai_format()
    assert isinstance(tools, list)
    assert len(tools) > 10
    for t in tools:
        assert t["type"] == "function"
        assert "name" in t["function"]
        assert "description" in t["function"]
        assert "parameters" in t["function"]
