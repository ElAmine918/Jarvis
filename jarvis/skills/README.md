# Skills & Memory System — Jarvis

Jarvis has a persistent memory system powered by SQLite (`aiosqlite`). This directory can hold exported skill files, though the primary storage is the database.

## How It Works

### Automatic Learning
When you ask Jarvis to remember a procedure or preference, it saves the information as a **Skill** or a **Fact** in the SQLite database at `MEMORY_DB_PATH` (default `/app/data/memory.db`).

### Memory Recall
Jarvis can search its own history (conversations, tool actions, token stats) via the `memory_recall` tool, which queries `logs.db` directly.

### Telegram Commands
- `/skills` — Lists all learned skills with usage statistics

## Database Schema

### Table `skills`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key, autoincrement |
| name | TEXT | Unique, not null |
| description | TEXT | Not null |
| content | TEXT | Markdown content, not null |
| created_at | TIMESTAMP | Default CURRENT_TIMESTAMP |
| last_used_at | TIMESTAMP | Updated on each retrieval |
| use_count | INTEGER | Incremented on each retrieval |

### Table `facts`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key, autoincrement |
| key | TEXT | Unique, not null |
| value | TEXT | Not null |
| created_at | TIMESTAMP | Default CURRENT_TIMESTAMP |

## API (memory.py)

```python
await memory.save_skill(name, description, content)  # UPSERT
await memory.get_skill(name)  # Retrieves + increments use_count
await memory.search_skills(query)  # SQL LIKE search on name/description
await memory.save_fact(key, value)  # UPSERT
await memory.get_fact(key)  # Retrieves value by key
```

## Limitations
- No vector database (no semantic search)
- Skills are keyword-matched via SQL LIKE, not embeddings
- Memory recall (logs.db) is synchronous sqlite3, not aiosqlite
