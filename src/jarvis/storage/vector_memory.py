import os
import hashlib
import logging
from datetime import datetime
import httpx
import asyncpg
from pgvector.asyncpg import register_vector
from jarvis.core.config import GEMINI_API_KEY, LM_STUDIO_URL, OLLAMA_LOCAL_URL

logger = logging.getLogger(__name__)

DB_USER = os.getenv("POSTGRES_USER", "jarvis")
DB_PASS = os.getenv("DB_PASSWORD", "jarvis_secret")
DB_HOST = os.getenv("POSTGRES_HOST", "jarvis-pgvector")
DB_NAME = os.getenv("POSTGRES_DB", "jarvis_memory")
DB_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

async def init_connection(conn):
    await register_vector(conn)

async def get_db_pool():
    return await asyncpg.create_pool(DB_URL, init=init_connection)

async def generate_embedding(text: str) -> list[float]:
    """
    Génère un embedding (768 dimensions) via Gemini (priorité) ou Ollama local (nomic).
    """
    if GEMINI_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_API_KEY}",
                    json={"model": "models/text-embedding-004", "content": {"parts": [{"text": text}]}},
                    timeout=5.0
                )
                if res.status_code == 200:
                    return res.json()["embedding"]["values"]
        except Exception as e:
            logger.warning(f"Erreur Gemini Embedding: {e}. Fallback Ollama...")

    if OLLAMA_LOCAL_URL:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{OLLAMA_LOCAL_URL}/embeddings",
                    json={"model": "nomic-embed-text", "input": text},
                    timeout=5.0
                )
                if res.status_code == 200:
                    return res.json()["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Erreur Ollama Embedding: {e}")
            
    raise Exception("Impossible de générer l'embedding (ni Gemini ni Ollama ne sont disponibles).")

async def ingest_message(pool, source: str, conversation_id: str, message_id: str, role: str, content: str, seq: int):
    """
    Insère un message dans la DB et génère son embedding.
    """
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async with pool.acquire() as conn:
        # Check if already exists
        exists = await conn.fetchval(
            "SELECT id FROM messages WHERE source=$1 AND conversation_id=$2 AND source_message_id=$3",
            source, conversation_id, message_id
        )
        if exists:
            return exists
            
        # Insert message
        db_msg_id = await conn.fetchval(
            """
            INSERT INTO messages (source, conversation_id, source_message_id, role, content, content_hash, message_ts, seq)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            source, conversation_id, message_id, role, content, content_hash, datetime.now(), seq
        )
        
        # Generate and insert embedding
        try:
            emb = await generate_embedding(content)
            await conn.execute(
                """
                INSERT INTO message_embeddings (message_id, chunk_index, embedded_text, embedding_model, embedding)
                VALUES ($1, $2, $3, $4, $5)
                """,
                db_msg_id, 0, content, "text-embedding-004", emb
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion de l'embedding: {e}")
            
        return db_msg_id

async def search_memory(pool, query: str, limit: int = 5) -> list[dict]:
    """
    Recherche hybride (Sémantique + Mots-clés).
    """
    try:
        emb = await generate_embedding(query)
    except Exception as e:
        logger.error(f"Erreur de génération d'embedding pour la recherche: {e}")
        return []
        
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM hybrid_search($1, $2, $3, $4)",
            query, emb, "text-embedding-004", limit
        )
        
        results = []
        for r in rows:
            results.append({
                "message_id": r["message_id"],
                "content": r["content"],
                "timestamp": r["message_ts"],
                "message_ts": r["message_ts"],
                "conversation_id": r["conversation_id"],
                "score": r["score"],
                "role": "Assistant",
            })
        return results
