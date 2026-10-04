import json
import os
import sqlite3
import uuid
from typing import Any

import os
from jarvis.core.config import LOGS_DB_PATH
DB_PATH = LOGS_DB_PATH


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            source TEXT NOT NULL,
            user_id TEXT,
            message_in TEXT NOT NULL,
            message_out TEXT NOT NULL,
            model_used TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            session_id TEXT,
            tool_name TEXT NOT NULL,
            arguments TEXT,
            result TEXT,
            model_used TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            tokens INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            fire_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)

    # Migrations if tables already exist but missing columns
    try:
        conn.execute(
            "ALTER TABLE conversations ADD COLUMN session_id TEXT DEFAULT 'default'"
        )
    except:
        pass
    try:
        conn.execute("ALTER TABLE actions ADD COLUMN session_id TEXT DEFAULT 'default'")
    except:
        pass
    try:
        conn.execute("ALTER TABLE actions ADD COLUMN model_used TEXT DEFAULT 'unknown'")
    except:
        pass

    conn.commit()
    conn.close()


def log_conversation(
    session_id: str,
    source: str,
    user_id: str,
    message_in: str,
    message_out: str,
    model_used: str = "",
) -> str:
    conv_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversations (id, session_id, source, user_id, message_in, message_out, model_used) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (conv_id, session_id, source, user_id, message_in, message_out, model_used),
    )
    conn.commit()
    conn.close()
    
    # Try async vector ingestion if running in an async context
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        async def _ingest():
            try:
                from jarvis.storage.vector_memory import get_db_pool, ingest_message
                pool = await get_db_pool()
                await ingest_message(pool, source, session_id, conv_id + "_in", "user", message_in, 1)
                await ingest_message(pool, source, session_id, conv_id + "_out", "assistant", message_out, 2)
                await pool.close()
            except Exception as e:
                pass
        loop.create_task(_ingest())
    except Exception:
        pass
        
    return conv_id



def log_action(
    session_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    result: str,
    model_used: str = "unknown",
):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO actions (id, session_id, tool_name, arguments, result, model_used) VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            session_id,
            tool_name,
            json.dumps(arguments),
            result,
            model_used,
        ),
    )
    conn.commit()
    conn.close()


def log_token_usage(model_name: str, tokens: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO token_usage (model_name, tokens) VALUES (?, ?)",
        (model_name, tokens),
    )
    conn.commit()
    conn.close()


def get_recent_conversations(limit: int = 50) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_actions(limit: int = 50) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM actions ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_token_stats() -> dict[str, int]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT model_name, SUM(tokens) as total FROM token_usage GROUP BY model_name"
    ).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def get_conversations_by_session(
    limit_sessions: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get most recent sessions
    sessions = conn.execute(
        "SELECT DISTINCT session_id, MAX(timestamp) as last_activity FROM conversations GROUP BY session_id ORDER BY last_activity DESC LIMIT ?",
        (limit_sessions,),
    ).fetchall()

    result = {}
    for s in sessions:
        sess_id = s["session_id"]
        msgs = conn.execute(
            "SELECT * FROM conversations WHERE session_id = ? ORDER BY timestamp ASC",
            (sess_id,),
        ).fetchall()
        result[sess_id] = [dict(m) for m in msgs]

    conn.close()
    return result


def save_scheduled_job(job_id: str, message: str, fire_at: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO scheduled_jobs (id, message, fire_at, status) VALUES (?, ?, ?, 'pending')",
        (job_id, message, fire_at),
    )
    conn.commit()
    conn.close()


def get_pending_jobs() -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM scheduled_jobs WHERE status = 'pending'"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_job_fired(job_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE scheduled_jobs SET status = 'fired' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def cancel_job(job_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE scheduled_jobs SET status = 'cancelled' WHERE id = ?", (job_id,)
    )
    conn.commit()
    conn.close()
