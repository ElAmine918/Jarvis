import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jarvis.core.router import (
    analyze_complexity,
    get_model_stats,
    mark_model_dead,
    _dead_models,
    check_endpoint,
    get_dynamic_gemini_models,
    get_dynamic_groq_models,
    get_dynamic_openrouter_models,
    get_all_backends,
)


def test_analyze_complexity_trivial():
    history = [{"role": "user", "content": "bonjour"}]
    res = analyze_complexity(history)
    assert res["level"] == "TRIVIAL"
    assert res["threshold"] == 40


def test_analyze_complexity_complex_keywords():
    history = [{"role": "user", "content": "Analyse ce code et optimise l'architecture du système"}]
    res = analyze_complexity(history)
    assert res["level"] == "COMPLEXE"
    assert res["threshold"] == 85


def test_analyze_complexity_complex_length():
    history = [{"role": "user", "content": "A" * 350}]
    res = analyze_complexity(history)
    assert res["level"] == "COMPLEXE"


def test_analyze_complexity_simple():
    history = [{"role": "user", "content": "Peux-tu me donner la recette de la tarte aux pommes simple ?"}]
    res = analyze_complexity(history)
    assert res["level"] == "SIMPLE"
    assert res["threshold"] == 70


def test_analyze_complexity_empty():
    res = analyze_complexity([])
    assert res["level"] == "SIMPLE"


def test_get_model_stats_scoring():
    gemini_pro = get_model_stats("gemini-1.5-pro")
    assert gemini_pro["score"] == 92
    assert gemini_pro["speed"] == "slow"

    gemini_flash = get_model_stats("gemini-1.5-flash")
    assert gemini_flash["score"] == 88
    assert gemini_flash["speed"] == "fast"

    llama_70b = get_model_stats("llama-3.3-70b-versatile")
    assert llama_70b["score"] == 90

    claude = get_model_stats("anthropic/claude-3.5-sonnet")
    assert claude["score"] == 95

    unknown = get_model_stats("some-random-unknown-model")
    assert unknown["score"] == 50


def test_circuit_breaker_mark_dead():
    current = time.time()
    # 404 Not Found -> ban for ~10 years
    mark_model_dead("dead-404-model", "404 Not Found")
    assert _dead_models["dead-404-model"] > current + 300000000

    # 400 Bad Request -> short cooldown 10s
    mark_model_dead("payload-error-model", "400 Bad Request: thought_signature missing")
    assert current < _dead_models["payload-error-model"] <= current + 15

    # 429 Daily Quota -> 24h cooldown
    mark_model_dead("daily-limit-model", "429 Daily quota per day exceeded")
    assert current + 80000 < _dead_models["daily-limit-model"] <= current + 86500

    # 429 Rate limit -> 1m cooldown
    mark_model_dead("rate-limit-model", "429 Rate limit exceeded tokens per minute")
    assert current < _dead_models["rate-limit-model"] <= current + 65

    # 503 Service Unavailable -> 15m cooldown
    mark_model_dead("overload-model", "503 Service Unavailable")
    assert current + 800 < _dead_models["overload-model"] <= current + 950


@pytest.mark.asyncio
async def test_check_endpoint():
    mock_resp_ok = AsyncMock()
    mock_resp_ok.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_resp_ok):
        assert await check_endpoint("http://localhost:11434/v1") is True

    mock_resp_err = AsyncMock()
    mock_resp_err.status_code = 500
    with patch("httpx.AsyncClient.get", return_value=mock_resp_err):
        assert await check_endpoint("http://localhost:11434/v1") is False


@pytest.mark.asyncio
async def test_get_dynamic_groq_models():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "qwen/qwen3.8-27b"},
            {"id": "whisper-large-v3"},  # Should be filtered out
            {"id": "llama-3.3-70b-versatile"},
        ]
    }
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        models = await get_dynamic_groq_models("fake_key", "qwen/qwen3.8-27b")
        assert "qwen/qwen3.8-27b" in models
        assert "llama-3.3-70b-versatile" in models
        assert "whisper-large-v3" not in models


@pytest.mark.asyncio
async def test_get_dynamic_openrouter_models():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "meta-llama/llama-3-8b:free", "pricing": {"prompt": "0"}},
            {"id": "paid-model-expensive", "pricing": {"prompt": "0.01"}},
        ]
    }
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        models = await get_dynamic_openrouter_models("fake_key", "meta-llama/llama-3-8b:free")
        assert "meta-llama/llama-3-8b:free" in models
        assert "paid-model-expensive" not in models


@pytest.mark.asyncio
async def test_get_all_backends_prioritizes_fast_for_trivial():
    with patch("jarvis.core.router.GEMINI_API_KEY", "fake_gemini"), \
         patch("jarvis.core.router.OPENROUTER_API_KEY", ""), \
         patch("jarvis.core.router.check_endpoint", return_value=False):
        backends = await get_all_backends(history=[{"role": "user", "content": "hello"}])
        assert len(backends) > 0
        assert all(len(b) == 3 for b in backends)
