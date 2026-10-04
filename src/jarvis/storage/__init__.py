"""Module de stockage pour Jarvis : mémoire SQLite, base de données logs et mémoire vectorielle."""

__all__ = [
    "MemoryManager",
    "init_db",
    "log_action",
    "log_conversation",
    "log_token_usage",
    "build_fts_query",
]


def __getattr__(name: str):
    if name == "MemoryManager":
        from jarvis.storage.memory import MemoryManager
        return MemoryManager
    if name in ("init_db", "log_action", "log_conversation", "log_token_usage"):
        from jarvis.storage import logger_db
        return getattr(logger_db, name)
    if name == "build_fts_query":
        from jarvis.storage.query_builder import build_fts_query
        return build_fts_query
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
