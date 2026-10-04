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
async def test_synthesize_speech_local_tts_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"AUDIO_WAV_BYTES"

    with patch("jarvis.interfaces.voice.LOCAL_TTS_URL", "http://piper-tts:5000"), \
         patch("httpx.AsyncClient.get", return_value=mock_resp):
        res = await synthesize_speech("**Bonjour** _Amine_ #titre `code`")
        assert res == b"AUDIO_WAV_BYTES"


@pytest.mark.asyncio
async def test_synthesize_speech_edge_tts_fallback():
    async def mock_stream():
        yield {"type": "audio", "data": b"CHUNK_1_"}
        yield {"type": "audio", "data": b"CHUNK_2"}

    mock_comm = MagicMock()
    mock_comm.stream = mock_stream

    with patch("jarvis.interfaces.voice.LOCAL_TTS_URL", ""), \
         patch("edge_tts.Communicate", return_value=mock_comm):
        res = await synthesize_speech("Message court")
        assert res == b"CHUNK_1_CHUNK_2"


def test_sanitize_speech_text():
    from jarvis.interfaces.live_agent import sanitize_speech_text
    raw = "**Bonjour** monsieur, voici le *résultat* `#code` !"
    clean = sanitize_speech_text(raw)
    assert "monsieur" not in clean.lower()
    assert "*" not in clean
    assert "#" not in clean
    assert "`" not in clean
    assert clean.startswith("Bonjour")

