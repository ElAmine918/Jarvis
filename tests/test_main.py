import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jarvis import main


@pytest.mark.asyncio
async def test_run_telegram_no_token():
    with patch("jarvis.main.TELEGRAM_BOT_TOKEN", None):
        agent = MagicMock()
        await main.run_telegram(agent)


@pytest.mark.asyncio
async def test_run_telegram_with_token():
    with patch("jarvis.main.TELEGRAM_BOT_TOKEN", "mock_token"):
        mock_app = MagicMock()
        mock_app.initialize = AsyncMock()
        mock_app.start = AsyncMock()
        mock_app.updater.start_polling = AsyncMock()

        # Stop event to not hang forever
        with patch("jarvis.main.build_telegram_app", return_value=mock_app):
            with patch("asyncio.Event") as mock_event_cls:
                mock_event = MagicMock()
                mock_event.wait = AsyncMock(return_value=True)
                mock_event_cls.return_value = mock_event

                agent = MagicMock()
                await main.run_telegram(agent)
                mock_app.initialize.assert_awaited_once()
                mock_app.start.assert_awaited_once()
                mock_app.updater.start_polling.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_api():
    agent = MagicMock()
    with patch("uvicorn.Server.serve", new_callable=AsyncMock) as mock_serve:
        await main.run_api(agent)
        assert main.fastapi_app.state.agent == agent
        mock_serve.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_function():
    with (
        patch("jarvis.main.init_db") as mock_init_db,
        patch("jarvis.core.agent.JarvisAgent.init", new_callable=AsyncMock) as mock_agent_init,
        patch("jarvis.tools.scheduler_tool.SchedulerTool.reload_pending_jobs", new_callable=AsyncMock) as mock_reload,
        patch("jarvis.main.run_telegram", new_callable=AsyncMock) as mock_run_tg,
        patch("jarvis.main.run_api", new_callable=AsyncMock) as mock_run_api,
    ):
        await main.main()
        mock_init_db.assert_called_once()
        mock_agent_init.assert_awaited_once()
        mock_reload.assert_awaited_once()
        mock_run_tg.assert_awaited_once()
        mock_run_api.assert_awaited_once()
