import logging
import os
from typing import Any

import httpx

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


def _get_api_headers():
    token = os.getenv("JARVIS_API_KEY", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get_api_url():
    port = os.getenv("API_PORT", "8080")
    host = os.getenv("API_HOST", "127.0.0.1")
    if host == "0.0.0.0":
        host = "127.0.0.1"
    return f"http://{host}:{port}/v1/chat/completions"


class SubagentTool(Tool):
    @property
    def name(self) -> str:
        return "delegate_to_subagent"

    @property
    def description(self) -> str:
        return (
            "Délègue une sous-tâche complexe (recherche, analyse de code, calcul) à un autre agent spécialisé. "
            "Le sous-agent est totalement autonome et renverra le résultat final de sa tâche."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Les instructions claires et détaillées pour le sous-agent.",
                },
                "model_tier": {
                    "type": "string",
                    "description": "Le modèle à utiliser. Options: 'jarvis-gemini' (très rapide, cloud), 'jarvis-ollama' (local 7B), 'jarvis-auto' (cascade par défaut).",
                    "enum": ["jarvis-gemini", "jarvis-ollama", "jarvis-auto"],
                },
            },
            "required": ["task", "model_tier"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        task = kwargs.get("task")
        model_tier = kwargs.get("model_tier", "jarvis-auto")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": model_tier,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Tu es un sous-agent. Voici ta tâche :\n\n{task}",
                        }
                    ],
                    "stream": False,
                }
                resp = await client.post(
                    _get_api_url(),
                    json=payload,
                    headers=_get_api_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return (
                    f"Réponse du sous-agent ({model_tier}) :\n"
                    + data["choices"][0]["message"]["content"]
                )
        except Exception as e:
            logger.error(f"Erreur Subagent: {e}")
            return f"Le sous-agent a échoué: {e!s}"


class AdvisorTool(Tool):
    @property
    def name(self) -> str:
        return "consult_advisor"

    @property
    def description(self) -> str:
        return (
            "Consulte un modèle de niveau supérieur (Advisor) pour obtenir un avis, une vérification ou une aide "
            "sur le raisonnement en cours, avant de donner ta réponse finale."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "question": {
                    "type": "string",
                    "description": "La question précise posée au conseiller.",
                },
                "context": {
                    "type": "string",
                    "description": "Le contexte actuel de la conversation pour que le conseiller comprenne la situation.",
                },
            },
            "required": ["question", "context"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        question = kwargs.get("question")
        context = kwargs.get("context", "")

        prompt = f"Tu es un conseiller expert. Voici le contexte actuel :\n{context}\n\nQuestion de l'agent principal :\n{question}\n\nDonne une analyse critique et des conseils."
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": "jarvis-gemini",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                resp = await client.post(
                    _get_api_url(),
                    json=payload,
                    headers=_get_api_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return (
                    "Avis du Conseiller :\n" + data["choices"][0]["message"]["content"]
                )
        except Exception as e:
            return f"Le conseiller n'est pas joignable: {e!s}"


class FusionTool(Tool):
    @property
    def name(self) -> str:
        return "fusion_panel_analysis"

    @property
    def description(self) -> str:
        return (
            "Lance un panel de réflexion (Fusion) : soumet une question complexe à plusieurs modèles simultanément "
            "(ex: Gemini + Ollama), puis fait faire la synthèse par un analyste. Idéal pour les problèmes très complexes."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "problem": {
                    "type": "string",
                    "description": "Le problème à soumettre au panel.",
                }
            },
            "required": ["problem"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        import asyncio

        problem = kwargs.get("problem")

        async def ask_model(model_id: str):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    payload = {
                        "model": model_id,
                        "messages": [{"role": "user", "content": problem}],
                        "stream": False,
                    }
                    resp = await client.post(
                        _get_api_url(),
                        json=payload,
                        headers=_get_api_headers(),
                    )
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
            except Exception:
                return "Échec de ce panéliste."

        results = await asyncio.gather(
            ask_model("jarvis-gemini"),
            ask_model("jarvis-ollama"),
            return_exceptions=True,
        )

        gemini_ans = results[0] if not isinstance(results[0], Exception) else "Erreur"
        ollama_ans = results[1] if not isinstance(results[1], Exception) else "Erreur"

        synthesis_prompt = f"Tu es l'Analyste Fusion. Voici le problème initial :\n{problem}\n\nRéponse Panéliste 1 (Gemini):\n{gemini_ans}\n\nRéponse Panéliste 2 (Ollama):\n{ollama_ans}\n\nSynthétise la meilleure réponse."

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": "jarvis-auto",
                    "messages": [{"role": "user", "content": synthesis_prompt}],
                    "stream": False,
                }
                resp = await client.post(
                    _get_api_url(),
                    json=payload,
                    headers=_get_api_headers(),
                )
                resp.raise_for_status()
                final_synth = resp.json()["choices"][0]["message"]["content"]
                return f"**Synthèse du Panel Fusion :**\n{final_synth}"
        except Exception as e:
            return f"Erreur de l'analyste: {e!s}"
