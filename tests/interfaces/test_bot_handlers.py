import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from jarvis.interfaces.bot import (
    _check_allowed,
    cmd_start,
    cmd_status,
    cmd_reset,
    cmd_silent,
    cmd_show,
    handle_callback,
)


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user.id = 123456
    update.effective_user.username = "testuser"
    update.effective_chat.id = 123456
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.user_data = {}
    context.bot_data = {}
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_check_allowed_unauthorized(mock_update):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [999999]):
        allowed = await _check_allowed(mock_update)
        assert allowed is False


@pytest.mark.asyncio
async def test_check_allowed_empty_config(mock_update):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", []):
        allowed = await _check_allowed(mock_update)
        assert allowed is False
        assert mock_update.message.reply_text.called
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Sécurité activée" in call_text


@pytest.mark.asyncio
async def test_check_allowed_authorized(mock_update):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        allowed = await _check_allowed(mock_update)
        assert allowed is True


@pytest.mark.asyncio
async def test_cmd_start_authorized(mock_update, mock_context):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await cmd_start(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "Bienvenue sur Jarvis" in msg


@pytest.mark.asyncio
async def test_cmd_reset(mock_update, mock_context):
    mock_context.user_data["history"] = ["msg1", "msg2"]
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await cmd_reset(mock_update, mock_context)
        assert mock_context.user_data["history"] == []
        assert mock_update.message.reply_text.called
        assert "Mémoire effacée" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_show_toggle(mock_update, mock_context):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        # Default is false -> toggles to True
        await cmd_show(mock_update, mock_context)
        assert mock_context.user_data["show_signature"] is True

        # Toggles to False
        await cmd_show(mock_update, mock_context)
        assert mock_context.user_data["show_signature"] is False


@pytest.mark.asyncio
async def test_cmd_silent_empty(mock_update, mock_context):
    mock_update.message.text = "/silent"
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await cmd_silent(mock_update, mock_context)
        assert "Ajoute ta demande" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_silent_valid(mock_update, mock_context):
    mock_update.message.text = "/silent test query"
    mock_agent = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield "réponse éphémère"

    mock_agent.process_message = fake_stream
    mock_context.bot_data["agent"] = mock_agent

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await cmd_silent(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        assert "réponse éphémère" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_callback_approval(mock_context):
    req_id = "test_req_123"
    event = asyncio.Event()

    from jarvis.core.approvals import APPROVAL_RESULTS, PENDING_APPROVALS
    PENDING_APPROVALS[req_id] = event

    update = MagicMock()
    update.effective_user.id = 123456
    update.callback_query = AsyncMock()
    update.callback_query.data = f"approve_{req_id}"
    update.callback_query.message.text = "Demande d'action critique"

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        try:
            await handle_callback(update, mock_context)
            assert event.is_set()
            assert APPROVAL_RESULTS[req_id] is True
            assert update.callback_query.edit_message_text.called
            assert "Action approuvée" in update.callback_query.edit_message_text.call_args[0][0]
        finally:
            PENDING_APPROVALS.pop(req_id, None)
            APPROVAL_RESULTS.pop(req_id, None)


@pytest.mark.asyncio
async def test_handle_callback_expired(mock_context):
    update = MagicMock()
    update.effective_user.id = 123456
    update.callback_query = AsyncMock()
    update.callback_query.data = "approve_expired_999"
    update.callback_query.message.text = "Demande ancienne"

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await handle_callback(update, mock_context)
        assert update.callback_query.edit_message_text.called
        assert "expirée" in update.callback_query.edit_message_text.call_args[0][0]
