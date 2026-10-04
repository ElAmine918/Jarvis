import io
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update
from telegram.constants import ParseMode
from jarvis.interfaces.bot import (
    _send_long,
    cmd_help,
    cmd_status,
    cmd_backend,
    cmd_skills,
    cmd_ping,
    handle_message,
    handle_voice,
    handle_photo,
    build_app,
)


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user.id = 123456
    update.effective_user.username = "testuser"
    update.effective_chat.id = 123456
    update.message = AsyncMock()
    update.message.text = "Hello Jarvis"
    update.message.reply_text = AsyncMock()
    update.message.reply_voice = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.user_data = {}
    context.bot_data = {}
    context.bot = AsyncMock()
    mock_agent = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield "Réponse simulée de Jarvis"

    mock_agent.process_message = fake_stream
    mock_agent.last_backend_used = "OpenRouter/Llama"
    mock_agent.skill_registry.get_all_skills.return_value = []
    mock_agent.memory.search_skills = AsyncMock(return_value=[])
    context.bot_data["agent"] = mock_agent
    return context


@pytest.mark.asyncio
async def test_send_long_messages(mock_update):
    long_text = "A" * 9000
    await _send_long(mock_update, long_text)
    assert mock_update.message.reply_text.call_count == 3


@pytest.mark.asyncio
async def test_send_long_messages_markdown_fallback(mock_update):
    mock_update.message.reply_text.side_effect = [Exception("Markdown error"), AsyncMock()]
    await _send_long(mock_update, "Short text")
    assert mock_update.message.reply_text.call_count == 2


@pytest.mark.asyncio
async def test_cmd_help(mock_update, mock_context):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await cmd_help(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "COMMANDES JARVIS" in msg


@pytest.mark.asyncio
async def test_cmd_status_all_variants(mock_update, mock_context):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.interfaces.bot.check_endpoint", AsyncMock(side_effect=[True, False])):
        await cmd_status(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "RAPPORT SYSTÈME JARVIS" in msg
        assert "LM Studio" in msg


@pytest.mark.asyncio
async def test_cmd_status_fallback_backends(mock_update, mock_context):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.interfaces.bot.check_endpoint", AsyncMock(return_value=False)), \
         patch("jarvis.interfaces.bot.OPENROUTER_API_KEY", "key_openrouter"), \
         patch("jarvis.interfaces.bot.GEMINI_API_KEY", ""):
        await cmd_status(mock_update, mock_context)
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "OpenRouter" in msg


@pytest.mark.asyncio
async def test_cmd_status_no_engine(mock_update, mock_context):
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.interfaces.bot.check_endpoint", AsyncMock(return_value=False)), \
         patch("jarvis.interfaces.bot.OPENROUTER_API_KEY", ""), \
         patch("jarvis.interfaces.bot.GEMINI_API_KEY", ""):
        await cmd_status(mock_update, mock_context)
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "Aucun moteur disponible" in msg


@pytest.mark.asyncio
async def test_cmd_backend(mock_update, mock_context):
    fake_pool = [
        ("Cloud (Gemini)", "gemini", "gemini-2.5-flash"),
        ("Cloud (OpenRouter)", "openrouter", "meta-llama/llama-3"),
        ("Local (LM Studio)", "lm_studio", "qwen-2.5"),
    ]
    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.core.router.get_all_backends", AsyncMock(return_value=fake_pool)), \
         patch("jarvis.core.router._dead_models", {"fake_model": 9999999999}):
        await cmd_backend(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "NEURAL ROUTER" in msg
        assert "Circuit Breaker" in msg


@pytest.mark.asyncio
async def test_cmd_skills_with_content(mock_update, mock_context):
    mock_skill = MagicMock()
    mock_skill.name = "docker_deploy"
    mock_skill.description = "Deploy docker stacks"
    mock_context.bot_data["agent"].skill_registry.get_all_skills.return_value = [mock_skill]
    mock_context.bot_data["agent"].memory.search_skills.return_value = [
        {"name": "owner_info", "description": "Amine preferences", "use_count": 5}
    ]

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await cmd_skills(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "docker_deploy" in msg
        assert "owner_info" in msg


@pytest.mark.asyncio
async def test_cmd_skills_empty(mock_update, mock_context):
    mock_context.bot_data["agent"].skill_registry.get_all_skills.return_value = []
    mock_context.bot_data["agent"].memory.search_skills.return_value = []

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await cmd_skills(mock_update, mock_context)
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "Aucune compétence" in msg


@pytest.mark.asyncio
async def test_cmd_ping_flow(mock_update, mock_context):
    msg_mock = AsyncMock()
    mock_update.message.reply_text.return_value = msg_mock

    async def fake_stream_ok(*args, **kwargs):
        yield "OK"

    mock_context.bot_data["agent"].process_message = fake_stream_ok

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.interfaces.bot.check_endpoint", AsyncMock(return_value=True)):
        await cmd_ping(mock_update, mock_context)
        assert msg_mock.edit_text.called
        edited = msg_mock.edit_text.call_args[0][0]
        assert "DIAGNOSTIC RÉSEAU" in edited


@pytest.mark.asyncio
async def test_handle_message_signature_and_long_text(mock_update, mock_context):
    mock_update.message.text = "Question complexe"
    mock_context.user_data["show_signature"] = True

    async def fake_long_stream(*args, **kwargs):
        yield "R" * 4500

    mock_context.bot_data["agent"].process_message = fake_long_stream

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await handle_message(mock_update, mock_context)
        assert mock_update.message.reply_text.call_count >= 2


@pytest.mark.asyncio
async def test_handle_message_exception(mock_update, mock_context):
    mock_update.message.text = "Crasher"

    async def crash_stream(*args, **kwargs):
        raise RuntimeError("Crash simulé")
        yield ""

    mock_context.bot_data["agent"].process_message = crash_stream

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await handle_message(mock_update, mock_context)
        assert "Une erreur interne s'est produite" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_voice_flow(mock_update, mock_context):
    mock_file = AsyncMock()
    mock_file.download_as_bytearray.return_value = b"VOICE_BYTES"
    mock_context.bot.get_file.return_value = mock_file

    mock_update.message.voice = MagicMock(file_id="voice_123")
    mock_update.message.audio = None

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.interfaces.bot.transcribe_voice", AsyncMock(return_value="Bonjour Jarvis en vocal")), \
         patch("jarvis.interfaces.bot.VOICE_TTS_ENABLED", True), \
         patch("jarvis.interfaces.bot.synthesize_speech", AsyncMock(return_value=b"AUDIO_TTS_BYTES")):
        await handle_voice(mock_update, mock_context)
        assert mock_update.message.reply_voice.called


@pytest.mark.asyncio
async def test_handle_photo_flow(mock_update, mock_context):
    mock_photo_file = AsyncMock()
    async def fake_download(out_stream):
        out_stream.write(b"FAKE_JPEG_BYTES")
    mock_photo_file.download_to_memory = fake_download

    mock_photo_item = MagicMock()
    mock_photo_item.get_file = AsyncMock(return_value=mock_photo_file)
    mock_update.message.photo = [mock_photo_item]
    mock_update.message.caption = "Regarde ce diagramme"

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await handle_photo(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        assert "Réponse simulée" in mock_update.message.reply_text.call_args[0][0]


def test_build_app_missing_token():
    with patch("jarvis.interfaces.bot.TELEGRAM_BOT_TOKEN", ""):
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN manquant"):
            build_app(MagicMock())


def test_build_app_success():
    with patch("jarvis.interfaces.bot.TELEGRAM_BOT_TOKEN", "123456:FAKE_TOKEN_FOR_TESTS"):
        app = build_app(MagicMock())
        assert app is not None
        assert "agent" in app.bot_data


@pytest.mark.asyncio
async def test_build_app_post_init():
    with patch("jarvis.interfaces.bot.TELEGRAM_BOT_TOKEN", "123456:FAKE_TOKEN_FOR_TESTS"), \
         patch.dict("os.environ", {"ALLOWED_TELEGRAM_USER_IDS": "123,456"}):
        app = build_app(MagicMock())
        mock_app = MagicMock()
        mock_app.bot = AsyncMock()
        # Execute post_init directly
        await app.post_init(mock_app)
        assert mock_app.bot.set_my_commands.called
        assert mock_app.bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_cmd_ping_error_in_response(mock_update, mock_context):
    msg_mock = AsyncMock()
    mock_update.message.reply_text.return_value = msg_mock

    async def fake_stream_fail(*args, **kwargs):
        yield "❌ Timeout sur l'API"

    mock_context.bot_data["agent"].process_message = fake_stream_fail

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.interfaces.bot.check_endpoint", AsyncMock(return_value=True)):
        await cmd_ping(mock_update, mock_context)
        assert msg_mock.edit_text.called
        assert "Échec" in msg_mock.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_voice_transcription_failure(mock_update, mock_context):
    mock_file = AsyncMock()
    mock_file.download_as_bytearray.return_value = b"VOICE_BYTES"
    mock_context.bot.get_file.return_value = mock_file
    mock_update.message.voice = MagicMock(file_id="voice_123")
    mock_update.message.audio = None

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]), \
         patch("jarvis.interfaces.bot.transcribe_voice", AsyncMock(return_value="❌ Clé manquante")):
        await handle_voice(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        assert "Clé manquante" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_photo_error(mock_update, mock_context):
    mock_update.message.photo = [MagicMock()]
    mock_update.message.photo[-1].get_file = AsyncMock(side_effect=RuntimeError("Download failed"))

    with patch("jarvis.interfaces.bot.ALLOWED_TELEGRAM_USER_IDS", [123456]):
        await handle_photo(mock_update, mock_context)
        assert mock_update.message.reply_text.called
        assert "rencontré une erreur" in mock_update.message.reply_text.call_args[0][0]

