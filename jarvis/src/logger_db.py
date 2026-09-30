import sqlite3
import json
import uuid
import datetime
import os
from typing import Dict, List, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "logs.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            user_id TEXT,
            message_in TEXT NOT NULL,
            message_out TEXT NOT NULL,
            model_used TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            tool_name TEXT NOT NULL,
            arguments TEXT,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_conversation(source: str, user_id: str, message_in: str, message_out: str, model_used: str = "") -> str:
    conv_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversations (id, source, user_id, message_in, message_out, model_used) VALUES (?, ?, ?, ?, ?, ?)",
        (conv_id, source, user_id, message_in, message_out, model_used)
    )
    conn.commit()
    conn.close()
    return conv_id

def log_action(conversation_id: str, tool_name: str, arguments: Dict[str, Any], result: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO actions (id, conversation_id, tool_name, arguments, result) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), conversation_id, tool_name, json.dumps(arguments), result)
    )
    conn.commit()
    conn.close()

def get_recent_conversations(limit: int = 50) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recent_actions(limit: int = 50) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM actions ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
