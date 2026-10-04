import datetime
import pytest
from unittest.mock import patch
from jarvis.tools.scheduler_tool import SchedulerTool


@pytest.fixture
def scheduler():
    return SchedulerTool()


@pytest.mark.asyncio
async def test_scheduler_schedule_reminder(scheduler):
    with patch("jarvis.tools.scheduler_tool.save_scheduled_job") as mock_save, \
         patch("asyncio.create_task") as mock_task:
        res = await scheduler.execute(delay_minutes=5, message="Rendez-vous à 15h")
        assert "✅ Rappel programmé avec succès" in res
        assert "5 minute(s)" in res
        assert mock_save.called
        assert mock_task.called


@pytest.mark.asyncio
async def test_scheduler_clamp_delay_minutes(scheduler):
    with patch("jarvis.tools.scheduler_tool.save_scheduled_job"), \
         patch("asyncio.create_task"):
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
    with patch("jarvis.tools.scheduler_tool.get_pending_jobs", return_value=fake_jobs), \
         patch("asyncio.create_task") as mock_task:
        await SchedulerTool.reload_pending_jobs()
        assert mock_task.call_count == 2
