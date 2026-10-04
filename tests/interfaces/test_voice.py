import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from jarvis.interfaces.voice import transcribe_voice, synthesize_speech


@pytest.mark.asyncio
async def test_transcribe_voice_local_stt_success():
    fake_audio = b"FAKE_OGG_AUDIO_BYTES"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "Bonjour Jarvis transcription locale"

    with patch("jarvis.interfaces.voice.LOCAL_STT_URL", "http://local-stt:9000"), \
         patch("httpx.AsyncClient.post", return_value=mock_resp):
        result = await transcribe_voice(fake_audio)
        assert result == "Bonjour Jarvis transcription locale"


@pytest.mark.asyncio
async def test_transcribe_voice_local_stt_exception_falls_back():
    fake_audio = b"FAKE_OGG_AUDIO_BYTES"
    mock_transcript = MagicMock()
    mock_transcript.text = "Transcrit via cloud après plantage local"

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)

    with (
        patch("jarvis.interfaces.voice.LOCAL_STT_URL", "http://local-stt:9000"),
        patch("httpx.AsyncClient.post", side_effect=RuntimeError("Local server down")),
        patch.dict("os.environ", {"GROQ_API_KEY": "fake_groq"}),
        patch("openai.AsyncOpenAI", return_value=mock_client),
    ):
        result = await transcribe_voice(fake_audio)
        assert result == "Transcrit via cloud après plantage local"


@pytest.mark.asyncio
async def test_transcribe_voice_no_api_keys():
    fake_audio = b"FAKE_OGG_AUDIO_BYTES"
    with patch("jarvis.interfaces.voice.LOCAL_STT_URL", ""), \
         patch.dict("os.environ", {"GROQ_API_KEY": "", "OPENAI_API_KEY": "", "GEMINI_API_KEY": ""}, clear=True):
        result = await transcribe_voice(fake_audio)
        assert "Aucune clé API" in result


@pytest.mark.asyncio
async def test_transcribe_voice_cloud_groq_success():
    fake_audio = b"FAKE_OGG_AUDIO_BYTES"
    mock_transcript = MagicMock()
    mock_transcript.text = "Texte transcrit via Groq"

    mock_openai_client = MagicMock()
    mock_openai_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)

    with patch("jarvis.interfaces.voice.LOCAL_STT_URL", ""), \
         patch.dict("os.environ", {"GROQ_API_KEY": "fake_groq_key"}), \
         patch("openai.AsyncOpenAI", return_value=mock_openai_client):
        result = await transcribe_voice(fake_audio)
        assert result == "Texte transcrit via Groq"


@pytest.mark.asyncio
async def test_transcribe_voice_openai_fallback():
    fake_audio = b"FAKE_OGG"
    mock_transcript = MagicMock()
    mock_transcript.text = "Transcrit via OpenAI"
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)

    with (
        patch("jarvis.interfaces.voice.LOCAL_STT_URL", ""),
        patch.dict("os.environ", {"GROQ_API_KEY": "", "OPENAI_API_KEY": "fake_oa", "GEMINI_API_KEY": ""}),
        patch("openai.AsyncOpenAI", return_value=mock_client),
    ):
        res = await transcribe_voice(fake_audio)
        assert res == "Transcrit via OpenAI"


@pytest.mark.asyncio
async def test_transcribe_voice_gemini_fallback():
    fake_audio = b"FAKE_OGG"
    mock_transcript = MagicMock()
    mock_transcript.text = "Transcrit via Gemini"
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)

    with (
        patch("jarvis.interfaces.voice.LOCAL_STT_URL", ""),
        patch.dict("os.environ", {"GROQ_API_KEY": "", "OPENAI_API_KEY": "", "GEMINI_API_KEY": "fake_gemini"}),
        patch("openai.AsyncOpenAI", return_value=mock_client),
    ):
        res = await transcribe_voice(fake_audio)
        assert res == "Transcrit via Gemini"


@pytest.mark.asyncio
async def test_transcribe_voice_cloud_error():
    fake_audio = b"FAKE_OGG"
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create = AsyncMock(side_effect=RuntimeError("Cloud failure"))

    with (
        patch("jarvis.interfaces.voice.LOCAL_STT_URL", ""),
        patch.dict("os.environ", {"GROQ_API_KEY": "fake_key"}),
        patch("openai.AsyncOpenAI", return_value=mock_client),
    ):
        res = await transcribe_voice(fake_audio)
        assert "❌ Erreur lors de la transcription" in res


@pytest.mark.asyncio
async def test_synthesize_speech_local_tts_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"AUDIO_WAV_BYTES"

    with patch("jarvis.interfaces.voice.LOCAL_TTS_URL", "http://piper-tts:5000"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await synthesize_speech("**Bonjour** _Amine_ #titre `code`")
        assert res == b"AUDIO_WAV_BYTES"


@pytest.mark.asyncio
async def test_synthesize_speech_long_text_clamped():
    long_txt = "A" * 2500
    mock_comm = MagicMock()
    async def mock_stream():
        yield {"type": "audio", "data": b"CLIPPED_AUDIO"}
    mock_comm.stream = mock_stream

    with (
        patch("jarvis.interfaces.voice.LOCAL_TTS_URL", ""),
        patch("edge_tts.Communicate", return_value=mock_comm) as mock_cls,
    ):
        res = await synthesize_speech(long_txt)
        assert res == b"CLIPPED_AUDIO"
        assert len(mock_cls.call_args[0][0]) <= 2000


@pytest.mark.asyncio
async def test_synthesize_speech_local_tts_error_falls_back():
    async def mock_stream():
        yield {"type": "audio", "data": b"FALLBACK_EDGE_AUDIO"}
    mock_comm = MagicMock()
    mock_comm.stream = mock_stream

    with (
        patch("jarvis.interfaces.voice.LOCAL_TTS_URL", "http://broken-local:5000"),
        patch("httpx.AsyncClient.get", side_effect=RuntimeError("Piper crashed")),
        patch("edge_tts.Communicate", return_value=mock_comm),
    ):
        res = await synthesize_speech("Message court")
        assert res == b"FALLBACK_EDGE_AUDIO"


@pytest.mark.asyncio
async def test_synthesize_speech_edge_tts_fallback_error():
    with (
        patch("jarvis.interfaces.voice.LOCAL_TTS_URL", ""),
        patch("edge_tts.Communicate", side_effect=RuntimeError("EdgeTTS down")),
    ):
        res = await synthesize_speech("Message court")
        assert res is None


def test_sanitize_speech_text():
    from jarvis.interfaces.live_agent import sanitize_speech_text
    raw = "**Bonjour** monsieur, voici le *résultat* `#code` !"
    clean = sanitize_speech_text(raw)
    assert "monsieur" not in clean.lower()
    assert "*" not in clean
    assert "#" not in clean
    assert "`" not in clean
    assert clean.startswith("Bonjour")
