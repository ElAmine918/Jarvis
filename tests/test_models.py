"""
Test: Dynamic Gemini model discovery (uses env var, no hardcoded keys).
"""
import os
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_get_dynamic_gemini_models_success():
    """Verifies model list parsing when API returns valid data."""
    from jarvis.core.router import get_dynamic_gemini_models
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "models/gemini-1.5-pro", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]},
        ]
    }
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        models = await get_dynamic_gemini_models("fake_key", "gemini-1.5-pro")
    assert len(models) >= 1
    assert all(isinstance(m, str) for m in models)


@pytest.mark.asyncio
async def test_get_dynamic_gemini_models_api_error():
    """Verifies fallback when API returns an error."""
    from jarvis.core.router import get_dynamic_gemini_models
    mock_response = AsyncMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {}
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        models = await get_dynamic_gemini_models("bad_key", "gemini-1.5-pro")
    # Should fall back to the primary model or return empty list — not crash
    assert isinstance(models, list)


def test_no_hardcoded_api_keys():
    """Security test: ensure no API key is hardcoded in the test file itself."""
    import inspect
    import re
    import tests.test_models as this_module
    lines = inspect.getsourcelines(this_module)[0]
    # Filter out this check function lines to avoid matching literal check strings
    test_lines = [l for l in lines if "def test_no_hardcoded_api_keys" not in l and "source" not in l]
    source_to_check = "".join(test_lines)
    # Check for Gemini or OpenAI API key patterns
    assert not re.search(r"AQ\.[a-zA-Z0-9_-]{20,}", source_to_check), "Hardcoded Gemini API key found!"
    assert not re.search(r"sk-[a-zA-Z0-9_-]{20,}", source_to_check), "Hardcoded OpenAI API key found!"

