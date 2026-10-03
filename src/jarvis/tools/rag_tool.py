import logging
from typing import Any

import httpx
from jarvis.filesystem import _safe_path

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class DocumentRAGTool(Tool):
    @property
    def name(self) -> str:
        return "document_rag_search"

    @property
    def description(self) -> str:
        return (
            "Analyse de grands documents textuels (RAG basique). "
            "Lit un grand fichier, le découpe, et utilise un agent rapide (Gemini/Ollama) "
            "pour trouver la réponse sémantique exacte à une question."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Chemin du gros fichier texte ou Markdown à analyser.",
                },
                "question": {
                    "type": "string",
                    "description": "La question précise à poser sur le document.",
                },
            },
            "required": ["file_path", "question"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        file_path = kwargs.get("file_path")
        question = kwargs.get("question")

        # Security: Valider le chemin via le sandbox filesystem avant toute lecture
        safe = _safe_path(file_path)
        if safe is None:
            return "🚫 Sécurité : chemin interdit. Le RAG est limité au répertoire /app."

        if not safe.exists():
            return f"❌ Le fichier {file_path} n'existe pas."

        try:
            with open(safe, "r") as f:
                content = f.read()

            # Truncate content to avoid token limits for this basic RAG version
            # A real RAG would use a vector database (Chroma/Qdrant)
            max_chars = 40000  # Roughly 10k tokens
            content = content[:max_chars]

            prompt = f"Tu es un système de RAG. Voici un extrait de document :\n\n{content}\n\nQuestion de l'utilisateur : {question}\n\nRéponds en te basant UNIQUEMENT sur le document."

            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": "jarvis-gemini",  # Fast model for RAG extraction
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                resp = await client.post(
                    "http://127.0.0.1:8080/v1/chat/completions", json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                return (
                    f"🧠 Résultat de la recherche RAG sur {safe.name} :\n"
                    + data["choices"][0]["message"]["content"]
                )

        except Exception as e:
            return f"❌ Erreur RAG: {e!s}"
