import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.core.router import (
    _dead_models,
    analyze_complexity,
    check_endpoint,
    get_all_backends,
    get_dynamic_gemini_models,
    get_dynamic_groq_models,
    get_dynamic_openrouter_models,
    get_model_stats,
    mark_model_dead,
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

    # LLaMA / Groq variations
    llama_70b = get_model_stats("llama-3.3-70b-versatile")
    assert llama_70b["score"] == 90
    assert llama_70b["speed"] == "fast"

    llama_8b = get_model_stats("llama-3-8b")
    assert llama_8b["score"] == 75

    gpt_oss = get_model_stats("gpt-oss-120b")
    assert gpt_oss["score"] == 95

    qwen_27 = get_model_stats("qwen3.8-27b")
    assert qwen_27["score"] == 88

    mixtral = get_model_stats("mixtral-8x7b")
    assert mixtral["score"] == 85

    qwen_72 = get_model_stats("qwen-72b-chat")
    assert qwen_72["score"] == 88

    qwen_14 = get_model_stats("qwen-14b")
    assert qwen_14["score"] == 80

    qwen_mini = get_model_stats("qwen-0.5b")
    assert qwen_mini["score"] == 60

    llama_405 = get_model_stats("meta-llama/llama-3.1-405b")
    assert llama_405["score"] == 90

    claude = get_model_stats("anthropic/claude-3.5-sonnet")
    assert claude["score"] == 95

    mistral_l = get_model_stats("mistral-large")
    assert mistral_l["score"] == 85

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

    # default error (5 min = 300s)
    mark_model_dead("other-model", "other random error")
    assert current + 290 < _dead_models["other-model"] <= current + 310


@pytest.mark.asyncio
async def test_check_endpoint():
    mock_resp_ok = AsyncMock()
    mock_resp_ok.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_resp_ok):
        assert await check_endpoint("http://localhost:11434/v1") is True
        assert await check_endpoint("http://localhost:11434/chat/completions") is True

    mock_resp_err = AsyncMock()
    mock_resp_err.status_code = 500
    with patch("httpx.AsyncClient.get", return_value=mock_resp_err):
        assert await check_endpoint("http://localhost:11434/v1") is False

    with patch("httpx.AsyncClient.get", side_effect=RuntimeError("connection refused")):
        assert await check_endpoint("http://localhost:11434/v1") is False


@pytest.mark.asyncio
async def test_get_dynamic_gemini_models():
    # Test cached or API call
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [{"name": "models/gemini-2.5-pro"}, {"name": "models/embedding-001"}]
    }
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        models = await get_dynamic_gemini_models("api_key", "gemini-2.5-pro")
        assert "gemini-2.5-pro" in models

    # Error handling
    with patch("httpx.AsyncClient.get", side_effect=RuntimeError("API error")):
        with patch("jarvis.core.router._gemini_models_cache", None):
            fallback = await get_dynamic_gemini_models("api_key", "primary-gemini")
            assert "primary-gemini" in fallback


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

    # Error handling
    with patch("httpx.AsyncClient.get", side_effect=RuntimeError("Groq offline")):
        with patch("jarvis.core.router._groq_models_cache", None):
            res = await get_dynamic_groq_models("fake_key", "default-groq")
            assert "default-groq" in res


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

    # Error handling
    with patch("httpx.AsyncClient.get", side_effect=RuntimeError("OpenRouter offline")):
        with patch("jarvis.core.router._openrouter_models_cache", None):
            res = await get_dynamic_openrouter_models("fake_key", "primary-or")
            assert "primary-or" in res


@pytest.mark.asyncio
async def test_get_all_backends_empty_pool():
    with (
        patch("jarvis.core.router.GEMINI_API_KEY", ""),
        patch("jarvis.core.config.GROQ_API_KEY", ""),
        patch("jarvis.core.router.OPENROUTER_API_KEY", ""),
        patch("jarvis.core.router.check_endpoint", return_value=False),
    ):
        backends = await get_all_backends(history=[])
        assert backends == []


@pytest.mark.asyncio
async def test_get_all_backends_full_ecosystem_and_sorting():
    # Setup mock for Ollama discovery
    mock_ollama_resp = MagicMock()
    mock_ollama_resp.status_code = 200
    mock_ollama_resp.json.return_value = {
        "data": [{"id": "llama3.2:latest"}]
    }

    with (
        patch("jarvis.core.router.GEMINI_API_KEY", "fake_gemini"),
        patch("jarvis.core.router.get_dynamic_gemini_models", return_value=["gemini-1.5-pro", "gemini-1.5-flash"]),
        patch("jarvis.core.config.GROQ_API_KEY", "fake_groq"),
        patch("jarvis.core.router.get_dynamic_groq_models", return_value=["llama-3.3-70b-versatile"]),
        patch("jarvis.core.router.OPENROUTER_API_KEY", "fake_or"),
        patch("jarvis.core.router.get_dynamic_openrouter_models", return_value=["meta-llama/llama-3-8b:free"]),
        patch("jarvis.core.router.check_endpoint", return_value=True),  # LM studio & Ollama online
        patch("httpx.AsyncClient.get", return_value=mock_ollama_resp),
    ):
        # 1. Trivial history
        backends_trivial = await get_all_backends(history=[{"role": "user", "content": "salut"}])
        assert len(backends_trivial) >= 5

        # 2. Complex history (checks complex sort key branch)
        complex_prompt = "Analyse et optimise l'architecture du système en profondeur avec du code complet " * 5
        backends_complex = await get_all_backends(history=[{"role": "user", "content": complex_prompt}])
        assert len(backends_complex) >= 5

        # 3. Simple history
        backends_simple = await get_all_backends(history=[{"role": "user", "content": "Quelle est la capitale de l'Islande ?"}])
        assert len(backends_simple) >= 5
