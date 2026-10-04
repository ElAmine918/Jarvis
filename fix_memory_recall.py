import datetime
import logging
import os
import sqlite3
from typing import Any

from jarvis.tools.base import Tool

try:
    from jarvis.storage.logger_db import DB_PATH
except ImportError:
    DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "..", "data", "logs.db"
    )

logger = logging.getLogger(__name__)

class MemoryRecallTool(Tool):
    @property
    def name(self) -> str:
        return "memory_recall"

    @property
    def description(self) -> str:
        return "Permet à Jarvis de rechercher dans son propre historique."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["conversations", "actions", "token_stats", "search"],
                    "description": "Le type de requête.",
                },
                "keyword": {
                    "type": "string",
                    "description": "Le mot-clé pour la recherche (utilisé uniquement si query_type est 'search').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Le nombre maximum de résultats à retourner.",
                },
                "days": {
                    "type": "integer",
                    "description": "Le nombre de jours dans le passé à inclure.",
                },
            },
            "required": ["query_type"],
        }

    async def execute(self, **kwargs) -> str:
        query_type = kwargs.get("query_type")
        keyword = kwargs.get("keyword", "")
        limit = min(kwargs.get("limit", 10), 50)
        days = kwargs.get("days", 7)

        if not os.path.exists(DB_PATH):
            return "Erreur : La base de données des logs est introuvable."

        cutoff_date = (
            datetime.datetime.now() - datetime.timedelta(days=days)
        ).isoformat()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            result_text = f"Résultats de la mémoire pour '{query_type}' :\n"

            if query_type == "conversations":
                cursor.execute(
                    "SELECT timestamp, message_in, message_out FROM conversations WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                    (cutoff_date, limit),
                )
                rows = cursor.fetchall()
                if not rows:
                    result_text += "- Aucune conversation trouvée."
                else:
                    for row in rows:
                        msg_in = str(row[1])[:100] + "..." if len(str(row[1])) > 100 else str(row[1])
                        msg_out = str(row[2])[:100] + "..." if len(str(row[2])) > 100 else str(row[2])
                        result_text += f"\n- [{row[0]}] User: {msg_in} | Jarvis: {msg_out}"

            elif query_type == "actions":
                cursor.execute(
                    "SELECT timestamp, tool_name, arguments FROM actions WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                    (cutoff_date, limit),
                )
                rows = cursor.fetchall()
                if not rows:
                    result_text += "- Aucune action trouvée."
                else:
                    for row in rows:
                        args = str(row[2])[:100] + "..." if len(str(row[2])) > 100 else str(row[2])
                        result_text += f"\n- [{row[0]}] Outil: {row[1]} | Args: {args}"

            elif query_type == "token_stats":
                cursor.execute(
                    "SELECT model_name, SUM(tokens) FROM token_usage WHERE timestamp >= ? GROUP BY model_name ORDER BY SUM(tokens) DESC",
                    (cutoff_date,),
                )
                rows = cursor.fetchall()
                if not rows:
                    result_text += "- Aucune donnée d'utilisation des tokens."
                else:
                    for row in rows:
                        result_text += f"\n- Modèle: {row[0]} | Tokens totaux: {row[1]}"

            elif query_type == "search":
                if not keyword:
                    return "Erreur : Le mot-clé est requis pour le type de recherche 'search'."
                
                try:
                    from jarvis.storage.vector_memory import get_db_pool, search_memory
                    pool = await get_db_pool()
                    try:
                        results = await search_memory(pool, keyword, limit=limit)
                        if not results:
                            result_text += f"- Aucun résultat trouvé pour '{keyword}' dans la mémoire sémantique."
                        else:
                            for r in results:
                                c = str(r['content'])[:150] + "..." if len(str(r['content'])) > 150 else str(r['content'])
                                result_text += f"\n- [{r['message_ts']}] {r['role'].capitalize()}: {c}"
                    finally:
                        await pool.close()
                except (ImportError, Exception) as vec_err:
                    logger.warning(f"Vector search failed ({vec_err}), fallback to SQLite.")
                    search_term = f"%{keyword}%"
                    cursor.execute(
                        "SELECT timestamp, message_in, message_out FROM conversations WHERE timestamp >= ? AND (message_in LIKE ? OR message_out LIKE ?) ORDER BY timestamp DESC LIMIT ?",
                        (cutoff_date, search_term, search_term, limit),
                    )
                    rows = cursor.fetchall()
                    if not rows:
                        result_text += f"- Aucun résultat trouvé pour '{keyword}'."
                    else:
                        for row in rows:
                            msg_in = str(row[1])[:100] + "..." if len(str(row[1])) > 100 else str(row[1])
                            msg_out = str(row[2])[:100] + "..." if len(str(row[2])) > 100 else str(row[2])
                            result_text += f"\n- [{row[0]}] User: {msg_in} | Jarvis: {msg_out}"
            else:
                return f"Erreur : Type de requête '{query_type}' non reconnu."

            conn.close()

            if len(result_text) > 3000:
                return result_text[:2997] + "..."

            return result_text

        except Exception as e:
            logger.error(f"Erreur lors de la lecture de la mémoire: {e!s}")
            return f"Erreur lors de l'accès à la base de données : {e!s}"
