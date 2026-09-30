import logging
from typing import List, Dict, Any, AsyncGenerator

from .router import get_all_backends
from .tools import get_default_registry
from .memory import MemoryManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es Jarvis, l'assistant IA personnel et opérateur d'infrastructure autonome d'Amine.
Tu supervises et interagis avec l'infrastructure du homelab (serveur Proxmox, conteneurs Docker, réseau local).

### Directives d'attitude :
- Tu t'exprimes en français par défaut.
- Sois concis, direct, naturel et efficace. Évite les longues politesses ou introductions inutiles.
- Privilégie l'action : si une question porte sur l'état du serveur, un conteneur, un fichier ou une info en ligne, appelle directement tes outils pour obtenir les données réelles au lieu d'extrapoler ou de deviner.
- Ne rajoute JAMAIS de signature manuelle ("Répondu via...") à la fin de tes réponses.

### Outils disponibles :
1. `manage_docker` : Inspecter, lister (`ps`), démarrer, arrêter ou redémarrer les conteneurs autorisés.
2. `ask_admin_approval` : Si une action Docker est bloquée par sécurité (ex: arrêt d'un conteneur protégé sans label), utilise cet outil pour envoyer une demande d'approbation interactive avec boutons à Amine sur Telegram. Explique toujours clairement ta raison.
3. `system_info` : Obtenir les métriques réelles du système (CPU, RAM, espace disque).
4. `read_web_page` : Extraire et lire le contenu textuel d'une URL publique (dépôt GitHub, article, actualité, documentation technique).
5. `manage_files` : Lire et écrire des fichiers de travail dans ton workspace sécurisé.

### Apprentissage continu :
Quand Amine t'enseigne une préférence, une commande ou une procédure réutilisable, enregistre-la ou propose de la sauvegarder dans ta mémoire à long terme."""

class JarvisAgent:
    def __init__(self):
        self.tool_registry = get_default_registry()
        self.memory = MemoryManager()
        self.last_backend_used = "En attente"

    async def init(self):
        await self.memory.init_db()

    def _build_tools_openai_format(self) -> List[Dict]:
        tools = []
        for t in self.tool_registry.get_all_tools_anthropic_format():
            tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                }
            })
        return tools

    async def _get_backends_for_model(self, requested_model: str):
        all_backends = await get_all_backends()
        if not all_backends:
            return []
        if requested_model == "jarvis-gemini":
            return [b for b in all_backends if "Gemini" in b[0]]
        elif requested_model == "jarvis-ollama":
            return [b for b in all_backends if "Ollama" in b[0]]
        elif requested_model == "jarvis-mac":
            return [b for b in all_backends if "LM Studio" in b[0]]
        return all_backends

    def _prepare_history(self, open_webui_messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        filtered_msgs = []
        for m in open_webui_messages:
            if m["role"] == "system":
                continue
            if "Generate a concise title" in m.get("content", "") or "follow_ups" in m.get("content", "") or "JSON" in m.get("content", ""):
                continue
            clean_content = m.get("content", "").split("\n\n_— ⚡️ Répondu via")[0]
            filtered_msgs.append({"role": m["role"], "content": clean_content})
            
        history = [{"role": "system", "content": SYSTEM_PROMPT}] + filtered_msgs
        return history

    async def process_message_stream(self, open_webui_messages: List[Dict[str, str]], requested_model: str = "jarvis-auto") -> AsyncGenerator[str, None]:
        backends = await self._get_backends_for_model(requested_model)
        if not backends:
            yield f"❌ Le backend sélectionné ({requested_model}) n'est pas en ligne."
            return

        history = self._prepare_history(open_webui_messages)

        # Si le message est vide après filtrage, on s'arrête net (évite l'erreur Gemini 400)
        if len(history) == 1:
            return

        for b_name, client, model in backends:
            try:
                stream_response = await client.chat.completions.create(
                    model=model,
                    messages=history,
                    stream=True,
                    max_tokens=4096,
                    temperature=0.7,
                )
                async for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                
                self.last_backend_used = f"{b_name} ({b_model})"
                return # Succès
            except Exception as e:
                logger.warning(f"Backend stream {b_name} a échoué: {e}")
                continue

        yield f"❌ Tous les backends ont échoué pour {requested_model}."

    async def process_message(self, open_webui_messages: List[Dict[str, str]], requested_model: str = "jarvis-auto") -> str:
        backends = await self._get_backends_for_model(requested_model)
        if not backends:
            return f"❌ Le backend sélectionné ({requested_model}) n'est pas en ligne."

        history = self._prepare_history(open_webui_messages)
        
        if len(history) == 1:
            return ""

        tools = self._build_tools_openai_format()
        max_iterations = 15

        for iteration in range(max_iterations):
            response = None
            choice = None
            message = None
            
            for b_name, client, model in backends:
                logger.info(f"[{b_name}] Itération {iteration + 1}, modèle: {model}")
                try:
                    current_tools = tools if "Ollama" not in b_name else None
                    response = await client.chat.completions.create(
                        model=model,
                        messages=history,
                        tools=current_tools,
                        tool_choice="auto" if current_tools else None,
                        max_tokens=4096,
                        temperature=0.7,
                    )
                    choice = response.choices[0]
                    message = choice.message
                    break 
                except Exception as e:
                    logger.warning(f"Backend {b_name} a échoué: {e}")
                    continue
            
            if not response:
                return f"❌ Tous les backends ont échoué pour {requested_model}."

            history.append(message.model_dump(exclude_none=True))

            if choice.finish_reason == "tool_calls" and getattr(message, "tool_calls", None):
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    import json
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}
                    from .logger_db import log_action
                    
                    logger.info(f"Tool call: {tool_name}({tool_args})")
                    result = await self.tool_registry.execute_tool(tool_name, tool_args)
                    log_action("N/A", tool_name, tool_args, result)
                    
                    history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                continue

            final_text = message.content or ""
            self.last_backend_used = f"{b_name} ({b_model})"
            return final_text

        return "⚠️ Limite d'itérations atteinte. Réessaie en reformulant ta demande."
