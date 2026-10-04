import pytest
from jarvis.storage import logger_db


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_logs.db")
    monkeypatch.setattr(logger_db, "DB_PATH", test_db)
    logger_db.init_db()


def test_log_and_get_conversations():
    conv_id = logger_db.log_conversation(
        session_id="session_1",
        source="telegram",
        user_id="12345",
        message_in="Bonjour Jarvis",
        message_out="Bonjour Monsieur",
        model_used="gemini-flash",
    )
    assert conv_id is not None

    recent = logger_db.get_recent_conversations(10)
    assert len(recent) == 1
    assert recent[0]["session_id"] == "session_1"
    assert recent[0]["message_in"] == "Bonjour Jarvis"
    assert recent[0]["model_used"] == "gemini-flash"

    by_sess = logger_db.get_conversations_by_session(5)
    assert "session_1" in by_sess
    assert len(by_sess["session_1"]) == 1


def test_log_and_get_actions():
    logger_db.log_action(
        session_id="session_1",
        tool_name="manage_docker",
        arguments={"action": "ps"},
        result="table container1",
        model_used="qwen2.5",
    )
    actions = logger_db.get_recent_actions(10)
    assert len(actions) == 1
    assert actions[0]["tool_name"] == "manage_docker"
    assert "table container1" in actions[0]["result"]


def test_token_usage_stats():
    logger_db.log_token_usage("gemini-flash", 150)
    logger_db.log_token_usage("gemini-flash", 250)
    logger_db.log_token_usage("qwen2.5", 500)

    stats = logger_db.get_token_stats()
    assert stats["gemini-flash"] == 400
    assert stats["qwen2.5"] == 500


def test_scheduled_jobs_lifecycle():
    logger_db.save_scheduled_job("job_1", "Rappel médical", "2026-10-04T18:00:00")
    logger_db.save_scheduled_job("job_2", "Backup auto", "2026-10-04T19:00:00")

    pending = logger_db.get_pending_jobs()
    assert len(pending) == 2

    # Fire job 1
    logger_db.mark_job_fired("job_1")
    pending_after_fire = logger_db.get_pending_jobs()
    assert len(pending_after_fire) == 1
    assert pending_after_fire[0]["id"] == "job_2"

    # Cancel job 2
    logger_db.cancel_job("job_2")
    assert len(logger_db.get_pending_jobs()) == 0
