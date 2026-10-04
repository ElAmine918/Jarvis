import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from jarvis.tools.scheduler_tool import SchedulerTool, _send_telegram_reminder


@pytest.fixture
def scheduler():
    return SchedulerTool()


def test_scheduler_properties(scheduler):
    assert scheduler.name == "schedule_reminder"
    assert "Telegram" in scheduler.description
    assert "delay_minutes" in scheduler.parameters["properties"]


@pytest.mark.asyncio
async def test_scheduler_schedule_reminder(scheduler):
    with (
        patch("jarvis.tools.scheduler_tool.save_scheduled_job") as mock_save,
        patch("asyncio.create_task") as mock_task,
    ):
        res = await scheduler.execute(delay_minutes=5, message="Rendez-vous à 15h")
        assert "✅ Rappel programmé avec succès" in res
        assert "5 minute(s)" in res
        assert mock_save.called
        assert mock_task.called


@pytest.mark.asyncio
async def test_scheduler_max_pending_limit(scheduler):
    mock_tasks = []
    for i in range(12):
        t = MagicMock()
        t.get_name.return_value = f"reminder_job_{i}"
        mock_tasks.append(t)

    with patch("asyncio.all_tasks", return_value=mock_tasks):
        res = await scheduler.execute(delay_minutes=5, message="Trop de rappels")
        assert "❌ Limite atteinte" in res


@pytest.mark.asyncio
async def test_scheduler_clamp_delay_minutes(scheduler):
    with (
        patch("jarvis.tools.scheduler_tool.save_scheduled_job"),
        patch("asyncio.create_task"),
    ):
        # Lower clamp
        res_low = await scheduler.execute(delay_minutes=0, message="Instant")
        assert "1 minute(s)" in res_low

        # Upper clamp
        res_high = await scheduler.execute(delay_minutes=5000, message="Too late")
        assert "1440 minute(s)" in res_high


@pytest.mark.asyncio
async def test_scheduler_reload_pending_jobs():
    fake_jobs = [
        {"id": "j1", "message": "Futur rappel", "fire_at": (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat()},
        {"id": "j2", "message": "Rappel manqué", "fire_at": (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).isoformat()},
    ]
    with (
        patch("jarvis.tools.scheduler_tool.get_pending_jobs", return_value=fake_jobs),
        patch("asyncio.create_task") as mock_task,
    ):
        await SchedulerTool.reload_pending_jobs()
        assert mock_task.call_count == 2


@pytest.mark.asyncio
async def test_send_telegram_reminder_no_users():
    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch("jarvis.tools.scheduler_tool.ALLOWED_TELEGRAM_USER_IDS", []),
    ):
        await _send_telegram_reminder("job1", "Msg", delay_seconds=1)


@pytest.mark.asyncio
async def test_send_telegram_reminder_success():
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = MagicMock(status_code=200)

    with (
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("jarvis.tools.scheduler_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("jarvis.tools.scheduler_tool.TELEGRAM_BOT_TOKEN", "fake_bot_token"),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("jarvis.tools.scheduler_tool.mark_job_fired") as mock_mark_fired,
    ):
        await _send_telegram_reminder("job1", "Prendre les clés", delay_seconds=5, is_missed=False)
        mock_sleep.assert_awaited_once_with(5)
        mock_client.post.assert_awaited_once()
        mock_mark_fired.assert_called_once_with("job1")


@pytest.mark.asyncio
async def test_send_telegram_reminder_missed_and_error():
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = RuntimeError("Telegram down")

    with (
        patch("jarvis.tools.scheduler_tool.ALLOWED_TELEGRAM_USER_IDS", [12345]),
        patch("jarvis.tools.scheduler_tool.TELEGRAM_BOT_TOKEN", "fake_bot_token"),
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("jarvis.tools.scheduler_tool.mark_job_fired") as mock_mark_fired,
    ):
        await _send_telegram_reminder("job2", "Rappel manqué", delay_seconds=0, is_missed=True)
        mock_mark_fired.assert_called_once_with("job2")
