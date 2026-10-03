import logging
from collections.abc import AsyncGenerator
from typing import Any

from jarvis.core.router import get_all_backends
from jarvis.storage.memory import MemoryManager
from jarvis.tools import get_default_registry

logger = logging.getLogger(__name__)

import os
from pathlib import Path

DEFAULT_PROMPT = (
    "Tu es Jarvis, l'assistant d'Amine. Réponds de manière concise et utile."
)


def get_system_prompt() -> str:
    # Look for prompt in data/system_prompt.txt
    prompt_path = (
        Path(os.getenv("WORKSPACE_DIR", "/app/workspace")).parent
        / "data"
        / "system_prompt.txt"
    )
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return DEFAULT_PROMPT


class JarvisAgent:
    def __init__(self):
        self.tool_registry = get_default_registry()
        self.memory = MemoryManager()
        self.last_backend_used = "En attente"

    async def init(self):
        await self.memory.init_db()

    def _build_tools_openai_format(self) -> list[dict]:
        tools = []
        for t in self.tool_registry.get_all_tools_anthropic_format():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
            )
        return tools

    async def _get_backends_for_model(self, requested_model: str, history: list = None):
        all_backends = await get_all_backends(history)
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

    def _prepare_history(
        self, open_webui_messages: list[dict[str, Any]], session_id: str
    ) -> list[dict[str, Any]]:
        filtered_msgs = []
        for m in open_webui_messages:
            if m["role"] == "system":
                continue

            content = m.get("content", "")

            # Handle multimodal content (list of dicts)
            if isinstance(content, list):
                # We keep the list intact for Vision models, but check text parts for filters
                text_parts = [
                    part["text"] for part in content if part.get("type") == "text"
                ]
                full_text = " ".join(text_parts)
                if (
                    "Generate a concise title" in full_text
                    or "follow_ups" in full_text
                    or "JSON" in full_text
                ):
                    continue
                # For images, we just pass the content as-is so Gemini/OpenRouter can process the base64 or URL
                filtered_msgs.append({"role": m["role"], "content": content})
            else:
                if (
                    "Generate a concise title" in content
                    or "follow_ups" in content
                    or "JSON" in content
                ):
                    continue
                clean_content = content.split("\n\n— ")[0]
                filtered_msgs.append({"role": m["role"], "content": clean_content})

                dynamic_system_prompt = get_system_prompt()
        if session_id != "open-webui":
            dynamic_system_prompt += "\n\n[INTERFACE: TELEGRAM]\nVous parlez actuellement à Monsieur via Telegram. N'UTILISEZ AUCUN FORMATAGE MARKDOWN (pas d'astérisques, pas de gras, pas de listes complexes), uniquement du texte brut clair et bien espacé. Soyez détaillé et communicant tout en restant élégant."
        else:
            dynamic_system_prompt += "\n\n[INTERFACE: OPEN WEBUI]\nVous parlez à l'utilisateur via une interface web riche. Utilisez pleinement le formatage Markdown (tableaux, gras, listes, code)."

        history = [
            {"role": "system", "content": dynamic_system_prompt}
        ] + filtered_msgs[-10:]
        return history

    async def process_message(
        self,
        open_webui_messages: list[dict[str, Any]],
        session_id: str = "default",
        requested_model: str = "jarvis-auto",
    ) -> AsyncGenerator[str, None]:
        history = self._prepare_history(open_webui_messages, session_id)

        if len(history) == 1:
            return

        backends = await self._get_backends_for_model(requested_model, history)
        if not backends:
            yield f"❌ Le backend sélectionné ({requested_model}) n'est pas en ligne."
            return

        tools = self._build_tools_openai_format()
        max_iterations = 15

        for iteration in range(max_iterations):
            current_backend = ""
            current_model = ""
            success_backend = False

            if iteration == 10:
                history.append({
                    "role": "system",
                    "content": "⚠️ AVERTISSEMENT INTERNE : Tu as utilisé 10 itérations pour cette tâche. Tu sembles bloqué ou tourner en boucle. Arrête immédiatement d'essayer la même stratégie. Utilise l'outil `consult_advisor` pour demander de l'aide à l'Agent Superviseur, ou arrête l'exécution et explique le problème à l'utilisateur."
                })
                yield "\n⚠️ *Jarvis ressent de la fatigue cognitive (10 itérations). Appel à la prudence...*"

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
                        stream=True,
                    )

                    final_text = ""
                    tool_calls_dict = {}
                    active_index_map = {}
                    true_idx_counter = 0

                    async for chunk in stream_response:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if delta.content:
                            final_text += delta.content
                            yield delta.content

                        if delta.tool_calls:
                            for tc_chunk in delta.tool_calls:
                                prov_idx = tc_chunk.index

                                # Provider bug fix: some providers stream multiple tools but reuse index=0.
                                # A new tool ALWAYS has an 'id' in its first chunk.
                                if getattr(tc_chunk, "id", None) is not None:
                                    true_idx = true_idx_counter
                                    true_idx_counter += 1
                                    active_index_map[prov_idx] = true_idx

                                    tool_calls_dict[true_idx] = {
                                        "id": tc_chunk.id,
                                        "type": "function",
                                        "function": {
                                            "name": tc_chunk.function.name or "",
                                            "arguments": tc_chunk.function.arguments
                                            or "",
                                        },
                                    }
                                else:
                                    true_idx = active_index_map.get(prov_idx, prov_idx)
                                    if true_idx not in tool_calls_dict:
                                        tool_calls_dict[true_idx] = {
                                            "id": f"call_{true_idx}",
                                            "type": "function",
                                            "function": {"name": "", "arguments": ""},
                                        }

                                    if getattr(tc_chunk.function, "name", None):
                                        tool_calls_dict[true_idx]["function"][
                                            "name"
                                        ] += tc_chunk.function.name
                                    if getattr(tc_chunk.function, "arguments", None):
                                        tool_calls_dict[true_idx]["function"][
                                            "arguments"
                                        ] += tc_chunk.function.arguments

                    current_backend = b_name
                    current_model = model
                    success_backend = True
                    break
                except Exception as e:
                    logger.warning(f"Backend stream {b_name} a échoué: {e}")
                    error_str = str(e)
                    from jarvis.core.router import mark_model_dead

                    mark_model_dead(model, error_str)
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

                    yield f"\n⚙️ *Exécution de {tool_name}...*"

                    from jarvis.storage.logger_db import log_action

                    logger.info(f"Tool call: {tool_name}({tool_args})")
                    result = await self.tool_registry.execute_tool(tool_name, tool_args)
                    log_action(
                        session_id,
                        tool_name,
                        tool_args,
                        result,
                        getattr(self, "last_backend_used", "unknown"),
                    )

                    history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        }
                    )
                continue
            else:
                self.last_backend_used = current_model
                return

        yield "⚠️ Limite d'itérations atteinte. Réessaie en reformulant ta demande."
