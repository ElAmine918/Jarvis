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
        elif requested_model == "jarvis-openrouter":
            return [b for b in all_backends if "OpenRouter" in b[0]]
        return all_backends

    def _prepare_history(self, open_webui_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered_msgs = []
        for m in open_webui_messages:
            if m["role"] == "system":
                continue
                
            content = m.get("content", "")
            
            # Handle multimodal content (list of dicts)
            if isinstance(content, list):
                # We keep the list intact for Vision models, but check text parts for filters
                text_parts = [part["text"] for part in content if part.get("type") == "text"]
                full_text = " ".join(text_parts)
                if "Generate a concise title" in full_text or "follow_ups" in full_text or "JSON" in full_text:
                    continue
                # For images, we just pass the content as-is so Gemini/OpenRouter can process the base64 or URL
                filtered_msgs.append({"role": m["role"], "content": content})
            else:
                if "Generate a concise title" in content or "follow_ups" in content or "JSON" in content:
                    continue
                clean_content = content.split("\n\n_— ⚡️ Répondu via")[0]
                filtered_msgs.append({"role": m["role"], "content": clean_content})
            
        history = [{"role": "system", "content": SYSTEM_PROMPT}] + filtered_msgs[-10:]
        return history


    async def process_message(self, open_webui_messages: List[Dict[str, Any]], requested_model: str = "jarvis-auto") -> AsyncGenerator[str, None]:
        backends = await self._get_backends_for_model(requested_model)
        if not backends:
            yield f"❌ Le backend sélectionné ({requested_model}) n'est pas en ligne."
            return

        history = self._prepare_history(open_webui_messages)
        
        if len(history) == 1:
            return

        tools = self._build_tools_openai_format()
        max_iterations = 15

        for iteration in range(max_iterations):
            current_backend = ""
            current_model = ""
            success_backend = False
            
            for b_name, client, model in backends:
                logger.info(f"[{b_name}] Itération {iteration + 1}, modèle: {model}")
                try:
                    stream_response = await client.chat.completions.create(
                        model=model,
                        messages=history,
                        tools=tools,
                        tool_choice="auto",
                        max_tokens=4096,
                        temperature=0.7,
                        stream=True
                    )
                    
                    final_text = ""
                    tool_calls_dict = {}
                    
                    async for chunk in stream_response:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if delta.content:
                            final_text += delta.content
                            yield delta.content
                            
                        if delta.tool_calls:
                            for tc_chunk in delta.tool_calls:
                                idx = tc_chunk.index
                                if idx not in tool_calls_dict:
                                    tool_calls_dict[idx] = {
                                        "id": tc_chunk.id,
                                        "type": "function",
                                        "function": {
                                            "name": tc_chunk.function.name or "",
                                            "arguments": tc_chunk.function.arguments or ""
                                        }
                                    }
                                else:
                                    if getattr(tc_chunk.function, "name", None):
                                        tool_calls_dict[idx]["function"]["name"] += tc_chunk.function.name
                                    if getattr(tc_chunk.function, "arguments", None):
                                        tool_calls_dict[idx]["function"]["arguments"] += tc_chunk.function.arguments

                    current_backend = b_name
                    current_model = model
                    success_backend = True
                    break 
                except Exception as e:
                    logger.warning(f"Backend stream {b_name} a échoué: {e}")
                    continue
            
            if not success_backend:
                yield f"❌ Tous les backends ont échoué pour {requested_model}."
                return

            assistant_msg = {"role": "assistant"}
            if final_text:
                assistant_msg["content"] = final_text
            
            tool_calls_list = []
            if tool_calls_dict:
                for idx in sorted(tool_calls_dict.keys()):
                    tool_calls_list.append(tool_calls_dict[idx])
                assistant_msg["tool_calls"] = tool_calls_list

            history.append(assistant_msg)

            if tool_calls_list:
                for tool_call in tool_calls_list:
                    tool_name = tool_call["function"]["name"]
                    import json
                    try:
                        tool_args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}
                        
                    yield f"\n\n⚙️ *Exécution de {tool_name}...*\n\n"
                        
                    from .logger_db import log_action
                    logger.info(f"Tool call: {tool_name}({tool_args})")
                    result = await self.tool_registry.execute_tool(tool_name, tool_args)
                    log_action("N/A", tool_name, tool_args, result)
                    
                    history.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    })
                continue
            else:
                self.last_backend_used = f"{current_backend} ({current_model})"
                return
                
        yield "⚠️ Limite d'itérations atteinte. Réessaie en reformulant ta demande."
