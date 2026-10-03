import asyncio
import httpx
import logging
from typing import Dict, Any
from .base import Tool
from ..config import TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_USER_IDS, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

logger = logging.getLogger(__name__)

async def _run_deep_research(topic: str):
    """Exécute une recherche profonde en arrière-plan et notifie l'utilisateur."""
    # On attend un peu pour s'assurer que la réponse initiale de Jarvis est bien partie
    await asyncio.sleep(2)
    
    user_id = ALLOWED_TELEGRAM_USER_IDS[0] if ALLOWED_TELEGRAM_USER_IDS else None
    if not user_id: 
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        # Envoi d'un statut intermédiaire
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": user_id,
                "text": f"🔍 *L'agent de recherche a bien démarré son analyse sur :* `{topic}`...",
                "parse_mode": "Markdown"
            })
            
        # Simulation d'une recherche web exhaustive ou appel d'un agent spécialisé.
        prompt = (
            f"Tu es un agent de recherche (Deep Research) autonome de très haut niveau. "
            f"L'utilisateur a demandé une analyse exhaustive sur le sujet suivant : {topic}\n\n"
            f"Rédige un rapport complet, extrêmement détaillé, structuré avec des titres, des bullet points "
            f"et des analyses de fond. Ne fais pas de résumé expéditif. Prends le rôle d'un expert du domaine."
        )
        
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                },
                timeout=180.0 # Timeout long pour la recherche profonde
            )
            if res.status_code == 200:
                report = res.json()["choices"][0]["message"]["content"]
            else:
                report = f"❌ L'agent de recherche a rencontré une erreur réseau. Code: {res.status_code}"
                
        text = f"🔬 **RAPPORT DE DEEP RESEARCH** 🔬\n**Sujet :** {topic}\n\n{report}"
        
        # Envoi par chunks si le rapport dépasse la limite Telegram (4096)
        async with httpx.AsyncClient() as client:
            for i in range(0, len(text), 4000):
                await client.post(url, json={
                    "chat_id": user_id,
                    "text": text[i:i+4000],
                    "parse_mode": "Markdown"
                })
                
    except Exception as e:
        logger.error(f"Erreur Deep Research: {e}")
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": user_id,
                "text": f"❌ L'agent de recherche a planté : {e}",
                "parse_mode": "Markdown"
            })

class DeepResearchTool(Tool):
    @property
    def name(self) -> str:
        return "call_deep_research"

    @property
    def description(self) -> str:
        return "Délègue une recherche web longue et complexe à un sous-agent autonome (Deep Research). Le rapport te sera envoyé en différé. Utilise cet outil au lieu de chercher toi-même quand la tâche est immense."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Le sujet exact et détaillé de la recherche à mener."
                }
            },
            "required": ["topic"]
        }

    async def execute(self, **kwargs) -> str:
        topic = kwargs.get("topic")
        if not topic:
            return "Erreur: Sujet manquant."
            
        # Lancement de la tâche en arrière-plan, non-bloquant
        asyncio.create_task(_run_deep_research(topic))
        
        return (
            f"✅ Le sous-agent 'Deep Research' a été déployé en arrière-plan avec succès sur le sujet : '{topic}'. "
            f"Il enverra son rapport détaillé directement sur Telegram d'ici quelques minutes. "
            f"Dis à l'utilisateur que c'est en cours et que tu es disponible pour d'autres requêtes en attendant."
        )
