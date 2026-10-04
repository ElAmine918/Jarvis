import logging
from typing import Any
import httpx
import os

from jarvis.tools.filesystem import _safe_path
from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

class DocumentRAGTool(Tool):
    @property
    def name(self) -> str:
        return "document_rag_search"

    @property
    def description(self) -> str:
        return "Analyse de grands documents textuels (RAG basique)."

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

        safe = _safe_path(file_path)
        if safe is None:
            return "🚫 Sécurité : chemin interdit. Le RAG est limité au répertoire /app ou autorisé."

        if not safe.exists():
            return f"❌ Le fichier {file_path} n'existe pas."

        try:
            with open(safe, "r") as f:
                content = f.read()

            max_chars = 40000
            content = content[:max_chars]

            prompt = f"Tu es un système de RAG. Voici un extrait de document :\n\n{content}\n\nQuestion de l'utilisateur : {question}\n\nRéponds en te basant UNIQUEMENT sur le document."

            api_host = os.getenv("API_HOST", "127.0.0.1")
            if api_host == "0.0.0.0":
                api_host = "127.0.0.1"
            api_port = os.getenv("API_PORT", "8080")
            url = f"http://{api_host}:{api_port}/v1/chat/completions"

            headers = {}
            api_key = os.getenv("JARVIS_API_KEY", "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": "jarvis-auto",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return (
                    f"🧠 Résultat de la recherche RAG sur {safe.name} :\n"
                    + data["choices"][0]["message"]["content"]
                )
        except Exception as e:
            return f"❌ Erreur RAG: {e!s}"
