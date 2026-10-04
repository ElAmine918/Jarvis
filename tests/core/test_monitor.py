import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from jarvis.core.monitor import proactive_monitoring_loop


@pytest.mark.asyncio
async def test_monitor_disabled_without_telegram_creds():
    with patch("jarvis.core.monitor.TELEGRAM_BOT_TOKEN", ""), \
         patch("jarvis.core.monitor.ALLOWED_TELEGRAM_USER_IDS", []):
        # Should return immediately
        await proactive_monitoring_loop()


@pytest.mark.asyncio
async def test_monitor_detects_crashed_container_and_alerts():
    mock_run_result = MagicMock()
    mock_run_result.returncode = 0
    # Simulate one exited abnormally container and one normal container
    mock_run_result.stdout = "caddy|Up 2 hours\nredis|Exited (137) 5 minutes ago\nbackup|Exited (0) 10 minutes ago\n"

    mock_post = AsyncMock()

    with patch("jarvis.core.monitor.TELEGRAM_BOT_TOKEN", "fake_token"), \
         patch("jarvis.core.monitor.ALLOWED_TELEGRAM_USER_IDS", [12345]), \
         patch("subprocess.run", return_value=mock_run_result), \
         patch("httpx.AsyncClient.post", mock_post), \
         patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
        try:
            await proactive_monitoring_loop()
        except asyncio.CancelledError:
            pass

    assert mock_post.called
    sent_payload = mock_post.call_args[1]["json"]
    assert sent_payload["chat_id"] == 12345
    assert "redis" in sent_payload["text"]
    assert "caddy" not in sent_payload["text"]
    assert "backup" not in sent_payload["text"]
