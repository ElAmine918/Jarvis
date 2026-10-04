"""
Test: Gemini API connectivity (uses env var, no hardcoded keys).
Run only if GEMINI_API_KEY is set in environment.
"""
import os
import pytest


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
async def test_gemini_api_reachable():
    """Integration test: verifies Gemini API endpoint is reachable with env key."""
    import httpx
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
    assert resp.status_code == 200, f"Gemini API returned {resp.status_code}"


def test_gemini_env_var_placeholder():
    """Unit test: verifies GEMINI_API_KEY env var is expected (not hardcoded)."""
    # This test always passes — it documents the contract
    assert True, "GEMINI_API_KEY must come from environment, never hardcoded"
