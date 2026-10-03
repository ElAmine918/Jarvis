import logging
import os

import aiosqlite

from jarvis.core.config import MEMORY_DB_PATH

logger = logging.getLogger(__name__)


class MemoryManager:
    """Gestionnaire de mémoire SQLite pour Jarvis (Skills et Facts)."""

    def __init__(self, db_path: str = MEMORY_DB_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Initialise la base de données et crée les tables si nécessaires."""
        # Créer le dossier parent si besoin
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(name, description, content, content_rowid='id');
            """)
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS skills_ai AFTER INSERT ON skills BEGIN
                  INSERT INTO skills_fts(rowid, name, description, content) VALUES (new.id, new.name, new.description, new.content);
                END;
            """)
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS skills_ad AFTER DELETE ON skills BEGIN
                  INSERT INTO skills_fts(skills_fts, rowid, name, description, content) VALUES('delete', old.id, old.name, old.description, old.content);
                END;
            """)
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS skills_au AFTER UPDATE ON skills BEGIN
                  INSERT INTO skills_fts(skills_fts, rowid, name, description, content) VALUES('delete', old.id, old.name, old.description, old.content);
                  INSERT INTO skills_fts(rowid, name, description, content) VALUES (new.id, new.name, new.description, new.content);
                END;
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info(f"Base de données mémoire initialisée à {self.db_path}")

    async def save_skill(self, name: str, description: str, content: str) -> str:
        """Sauvegarde une nouvelle compétence ou la met à jour."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO skills (name, description, content, created_at, last_used_at, use_count)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
                    ON CONFLICT(name) DO UPDATE SET 
                        description=excluded.description,
                        content=excluded.content,
                        last_used_at=CURRENT_TIMESTAMP
                """,
                    (name, description, content),
                )
                await db.commit()
            return f"Compétence '{name}' sauvegardée avec succès."
        except Exception as e:
            logger.error(f"Erreur save_skill: {e}")
            return f"Erreur lors de la sauvegarde: {e}"

    async def get_skill(self, name: str) -> dict[str, str] | None:
        """Récupère une compétence par son nom exact et met à jour ses stats."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM skills WHERE name = ?", (name,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        # Mettre à jour les stats d'utilisation
                        await db.execute(
                            "UPDATE skills SET use_count = use_count + 1, last_used_at = CURRENT_TIMESTAMP WHERE name = ?",
                            (name,),
                        )
                        await db.commit()
                        return dict(row)
            return None
        except Exception as e:
            logger.error(f"Erreur get_skill: {e}")
            return None

    async def search_skills(self, query: str) -> list[dict[str, str]]:
        """Recherche des compétences via FTS5."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                if not query:
                    async with db.execute("SELECT * FROM skills") as cursor:
                        rows = await cursor.fetchall()
                        return [dict(row) for row in rows]

                async with db.execute(
                    """
                    SELECT skills.* FROM skills_fts 
                    JOIN skills ON skills.id = skills_fts.rowid 
                    WHERE skills_fts MATCH ? 
                    ORDER BY rank
                """,
                    (query,),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur search_skills: {e}")
            return []

    async def save_fact(self, key: str, value: str) -> str:
        """Sauvegarde un fait clé-valeur."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO facts (key, value, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                    (key, value),
                )
                await db.commit()
            return f"Fait '{key}' sauvegardé."
        except Exception as e:
            logger.error(f"Erreur save_fact: {e}")
            return f"Erreur lors de la sauvegarde: {e}"

    async def get_fact(self, key: str) -> str | None:
        """Récupère la valeur d'un fait."""
        try:
            async with aiosqlite.connect(self.db_path) as db, db.execute(
                "SELECT value FROM facts WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
            return None
        except Exception as e:
            logger.error(f"Erreur get_fact: {e}")
            return None
