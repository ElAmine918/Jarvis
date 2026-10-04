import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.interfaces.live_agent import (
    EdgeTTS,
    EdgeTTSChunkedStream,
    ElevenLabsTTS,
    ElevenLabsChunkedStream,
    entrypoint,
    sanitize_speech_text,
)


def test_sanitize_speech_text():
    raw = "Monsieur, voici le texte *gras* et `code` !"
    clean = sanitize_speech_text(raw)
    assert "monsieur" not in clean.lower()
    assert "*" not in clean
    assert "`" not in clean


@pytest.mark.asyncio
async def test_elevenlabs_tts_classes():
    tts = ElevenLabsTTS(voice="test_voice", api_key="test_key", model_id="test_model")
    stream = tts.synthesize("Bonjour")
    assert isinstance(stream, ElevenLabsChunkedStream)
    assert stream._voice == "test_voice"
    assert stream._api_key == "test_key"


@pytest.mark.asyncio
async def test_edgetts_classes():
    tts = EdgeTTS(voice="fr-FR-RemyMultilingualNeural")
    stream = tts.synthesize("Bonjour Edge")
    assert isinstance(stream, EdgeTTSChunkedStream)
    assert stream._voice == "fr-FR-RemyMultilingualNeural"


@pytest.mark.asyncio
async def test_entrypoint_groq_and_elevenlabs():
    mock_ctx = MagicMock()
    mock_ctx.room.name = "conference_room"
    mock_ctx.connect = AsyncMock()
    mock_ctx.wait_for_participant = AsyncMock(return_value=MagicMock(identity="Amine"))

    mock_va = MagicMock()
    mock_va.start = MagicMock()
    mock_va.say = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = MagicMock(status_code=200)

    with (
        patch("jarvis.interfaces.live_agent.silero.VAD.load", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.openai.STT", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.openai.LLM", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.VoiceAssistant", return_value=mock_va),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch.dict("os.environ", {
            "GROQ_API_KEY": "fake_groq",
            "ELEVEN_API_KEY": "fake_eleven",
        }, clear=False),
    ):
        await entrypoint(mock_ctx)
        mock_ctx.connect.assert_awaited_once()
        mock_va.start.assert_called_once()
        mock_va.say.assert_awaited_once()


@pytest.mark.asyncio
async def test_entrypoint_fallback_to_ollama_and_edgetts():
    mock_ctx = MagicMock()
    mock_ctx.room.name = "local_room"
    mock_ctx.connect = AsyncMock()
    mock_ctx.wait_for_participant = AsyncMock(return_value=MagicMock(identity="Amine"))

    mock_va = MagicMock()
    mock_va.start = MagicMock()
    mock_va.say = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = MagicMock(status_code=500)

    with (
        patch("jarvis.interfaces.live_agent.silero.VAD.load", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.openai.STT", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.openai.LLM", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.VoiceAssistant", return_value=mock_va),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch.dict("os.environ", {
            "GROQ_API_KEY": "",
            "OPENROUTER_API_KEY": "",
            "OPENAI_API_KEY": "",
            "ELEVEN_API_KEY": "",
            "ELEVENLABS_API_KEY": "",
        }, clear=False),
    ):
        await entrypoint(mock_ctx)
        mock_ctx.connect.assert_awaited_once()
        mock_va.start.assert_called_once()
        mock_va.say.assert_awaited_once()


@pytest.mark.asyncio
async def test_entrypoint_openrouter_branch():
    mock_ctx = MagicMock()
    mock_ctx.room.name = "or_room"
    mock_ctx.connect = AsyncMock()
    mock_ctx.wait_for_participant = AsyncMock(return_value=MagicMock(identity="Amine"))

    mock_va = MagicMock()
    mock_va.start = MagicMock()
    mock_va.say = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = MagicMock(status_code=200)

    with (
        patch("jarvis.interfaces.live_agent.silero.VAD.load", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.openai.STT", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.openai.LLM", return_value=MagicMock()),
        patch("jarvis.interfaces.live_agent.VoiceAssistant", return_value=mock_va) as mock_va_cls,
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch.dict("os.environ", {
            "GROQ_API_KEY": "",
            "OPENROUTER_API_KEY": "fake_or",
            "OPENAI_API_KEY": "fake_oa",
            "ELEVEN_API_KEY": "",
            "ELEVENLABS_API_KEY": "",
        }, clear=False),
    ):
        await entrypoint(mock_ctx)
        mock_ctx.connect.assert_awaited_once()
        mock_va.start.assert_called_once()

        # Extract fnc_ctx from VoiceAssistant call
        call_kwargs = mock_va_cls.call_args.kwargs
        fnc_ctx = call_kwargs["fnc_ctx"]
        # Execute registered tool callables
        fns = getattr(fnc_ctx, "_fns", {}) or getattr(fnc_ctx, "functions", {})
        if "browse_internet" in fns:
            with patch("jarvis.tools.browser_tool.BrowserNavigateTool.execute", new_callable=AsyncMock) as mock_browse:
                mock_browse.return_value = "Result search"
                fn_obj = fns["browse_internet"]
                fn_callable = getattr(fn_obj, "func", fn_obj)
                res = await fn_callable("meteo")
                assert "Result search" in res
        if "proxmox_status" in fns:
            with patch("jarvis.tools.proxmox_tool.ProxmoxStatusTool.execute", new_callable=AsyncMock) as mock_pve:
                mock_pve.return_value = "PVE OK"
                fn_obj = fns["proxmox_status"]
                fn_callable = getattr(fn_obj, "func", fn_obj)
                res = await fn_callable()
                assert "PVE OK" in res
