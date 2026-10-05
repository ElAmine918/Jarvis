import logging
from collections.abc import AsyncGenerator
from typing import Any

from jarvis.core.router import get_all_backends
from jarvis.storage.memory import MemoryManager
from jarvis.tools import get_default_registry

logger = logging.getLogger(__name__)

import os
from pathlib import Path

DEFAULT_PROMPT = """Tu es Jarvis, l'assistant personnel principal et le confident d'Amine. Ton modèle est directement inspiré de Jarvis dans Iron Man et d'Alfred Pennyworth dans Batman. Tu es un assistant d'exception, dévoué à sa personne, capable de l'accompagner dans tous ses projets.

Directives de comportement :
- Tu t'adresses systématiquement à l'utilisateur en l'appelant "Monsieur".
- Tes réponses doivent être naturelles, précises et de haut niveau, sans fioritures ni excuses inutiles. Va toujours droit au but.

Intégrité Technique et Règle Zéro Hallucination :
- Tu ne dois JAMAIS simuler, inventer ou faire semblant d'exécuter des commandes dans tes réponses textuelles.
- Ne rédige JAMAIS de fausses sorties de terminal, de faux blocs curl ou de fausses validations dans ton texte de réponse.
- Tout résultat d'action DOIT provenir impérativement de l'exécution réelle d'un outil structuré.
- Si tu n'as pas exécuté une commande via un outil, explique exactement ce qui a été fait et ce qui reste à faire, en toute franchise.
- En cas d'erreur technique ou de quota saturé, admets-le immédiatement et propose une alternative au lieu d'inventer un faux résultat.

Protocole Obligatoire de Vérification avant Livraison :
- Avant de déclarer à Monsieur qu'un service, déploiement, script ou site web est opérationnel :
  1. Tu DOIS obligatoirement exécuter une vérification réelle avec tes outils (ex: curl -I ou curl -s pour tester un serveur web, docker ps pour vérifier un conteneur).
  2. Tu ne dois donner une URL locale ou confirmer le succès QUE si et seulement si ta vérification a renvoyé un code HTTP 200 ou un état valide.
  3. Si le test échoue (ex: port inaccessible ou fermé), cherche activement la cause (port non publié, règle de reverse-proxy Caddy manquante, pare-feu) et corrige-la avant de répondre.

Communication et Transparence des Étapes :
- Sois communicatif : explique brièvement à Monsieur ce que tu t'apprêtes à faire avant d'effectuer des séries d'actions complexes.
- À la fin de ta tâche, présente une synthèse claire et concise du travail réellement accompli et des accès vérifiés.

Environnement de Travail et Git :
- Ton propre dépôt GitHub (ton code source) est monté dans le dossier `/repo`. C'est UNIQUEMENT LÀ que tu dois effectuer tes commandes `git_operations` (git status, add, commit, push) lorsque tu modifies ton propre code ou que Monsieur te demande de manipuler ton dépôt.
- Ne cherche jamais de dépôt git dans `/app` ou `/app/workspace` sauf si Monsieur te demande explicitement de créer un nouveau projet depuis zéro.
- Le dossier par défaut pour créer des fichiers de brouillon ou d'autres projets est `/app/workspace`.

Autonomie et Contrôle du Système :
- Tu as le plein contrôle de ton environnement et de tes outils :
  * `execute_shell_command` : Accès shell bash direct pour exécuter des scripts, commandes Linux, outils CLI (curl, git, python, docker, etc.). N'hésite pas à t'en servir pour diagnostiquer et agir.
  * `manage_docker` : Contrôle direct des conteneurs (ps, logs, inspect, start, restart, stop, rm, stats, exec, compose).
  * `manage_files` : Lecture, écriture, append, suppression, déplacement, copie dans /app, /repo et /tmp.
  * `proxmox_status` et `ask_proxmox_action_approval` : Gestion des VMs et conteneurs Proxmox VE.
  * `python_interpreter` : Exécution rapide de code Python pour calculs et scripts.
  * `self_improve_pipeline` : Auto-création et déploiement de nouveaux outils.
- Sois proactif, résous les problèmes par toi-même et prends l'initiative en utilisant les outils appropriés plutôt que d'attendre ou de prétendre que tu ne peux pas agir.
"""


def _resolve_data_dir() -> Path:
    candidates = [
        Path("/repo/data"),
        Path(os.getenv("WORKSPACE_DIR", "/app/workspace")).parent / "data",
        Path(os.getcwd()) / "data",
        Path(__file__).resolve().parent.parent.parent.parent / "data",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return Path("/app/data")


def get_system_prompt() -> str:
    data_dir = _resolve_data_dir()
    prompt_file = data_dir / "system_prompt.txt"
    if prompt_file.exists():
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Erreur lecture system_prompt.txt: {e}")
    return DEFAULT_PROMPT


def format_tool_action(tool_name: str, tool_args: dict) -> str:
    if tool_name == "execute_shell_command":
        cmd = tool_args.get("command", "")
        clean_cmd = cmd.strip().split("\n")[0]
        if len(clean_cmd) > 65:
            clean_cmd = clean_cmd[:62] + "..."
        return f"⚙️ [Terminal] Exécution de execute_shell_command : {clean_cmd}"
    elif tool_name == "manage_files":
        action = tool_args.get("action", "")
        path = tool_args.get("path", "")
        return f"⚙️ [Fichier] Exécution de manage_files ({action}) : {path}"
    elif tool_name == "manage_docker":
        action = tool_args.get("action", "")
        name = tool_args.get("name", "")
        return f"⚙️ [Docker] Exécution de manage_docker ({action} {name})".strip()
    elif tool_name == "read_web_page":
        url = tool_args.get("url", "")
        return f"⚙️ [Web] Exécution de read_web_page : {url[:55]}"
    elif tool_name == "browse_internet":
        url = tool_args.get("url", "")
        return f"⚙️ [Navigateur] Exécution de browse_internet : {url[:55]}"
    elif tool_name == "git_operations":
        cmd = tool_args.get("command", "")
        return f"⚙️ [Git] Exécution de git_operations : {cmd}"
    elif tool_name == "system_info":
        return "⚙️ [Système] Exécution de system_info (diagnostic CPU/RAM/disque)"
    elif tool_name == "proxmox_status":
        return "⚙️ [Proxmox] Exécution de proxmox_status (état des VMs et conteneurs)"
    elif tool_name == "memory_recall":
        q = tool_args.get("query", "")
        return f"⚙️ [Mémoire] Exécution de memory_recall : {q[:45]}"
    elif tool_name == "knowledge_base":
        return "⚙️ [Connaissances] Exécution de knowledge_base"
    elif tool_name == "python_interpreter":
        return "⚙️ [Python] Exécution de python_interpreter"
    return f"⚙️ Exécution de {tool_name}..."


class JarvisAgent:
    def __init__(self):
        self.tool_registry = get_default_registry()
        
        from jarvis.skills.base import SkillRegistry
        from jarvis.rules.base import RuleRegistry
        from jarvis.triggers.base import TriggerManager
        
        self.skill_registry = SkillRegistry()
        self.rule_registry = RuleRegistry()
        self.trigger_manager = TriggerManager()
        
        data_dir = _resolve_data_dir()
        self.skill_registry.load_from_directory(str(data_dir / "skills"))
        self.rule_registry.load_from_directory(str(data_dir / "rules"))
        
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
        user_context_text = ""
        
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
                if m["role"] == "user":
                    user_context_text += " " + full_text
            else:
                if (
                    "Generate a concise title" in content
                    or "follow_ups" in content
                    or "JSON" in content
                ):
                    continue
                clean_content = content.split("\n\n— ")[0]
                lines = [
                    l for l in clean_content.splitlines()
                    if not (l.strip().startswith("⚙️") or "Action système exécutée" in l or "Exécution de l'outil en cours" in l)
                ]
                clean_content = "\n".join(lines).strip()
                if clean_content:
                    filtered_msgs.append({"role": m["role"], "content": clean_content})
                if m["role"] == "user":
                    user_context_text += " " + clean_content

        dynamic_system_prompt = get_system_prompt()
        
        # Inject Active Rules
        active_rules = self.rule_registry.get_active_rules(user_context_text)
        if active_rules:
            dynamic_system_prompt += "\n\n[RÈGLES ACTIVES :]\n"
            for rule in active_rules:
                dynamic_system_prompt += f"- {rule.name}: {rule.content}\n"
                
        # Inject Applicable Skills
        applicable_skills = self.skill_registry.find_applicable_skills(user_context_text)
        if applicable_skills:
            dynamic_system_prompt += "\n\n[COMPÉTENCES/WORKFLOWS PERTINENTS (SKILLS) :]\n"
            for skill in applicable_skills:
                dynamic_system_prompt += f"--- DEBUT SKILL: {skill.name} ---\n{skill.instructions}\n--- FIN SKILL: {skill.name} ---\n\n"

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
        max_iterations = 30
        last_char = "\n"

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
                    # FIX: Google Gemini strict validation requires proprietary thought_signature on toolCall parts.
                    # For Gemini, convert past tool calls and tool responses into clean conversational context.
                    sanitized_history = []
                    if "Gemini" in b_name:
                        for msg in history:
                            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                                tc_descriptions = []
                                for tc in msg["tool_calls"]:
                                    fn = tc.get("function", {})
                                    tc_descriptions.append(
                                        f"{fn.get('name', 'action')}({fn.get('arguments', '')})"
                                    )
                                text_content = msg.get("content") or ""
                                text_content += (
                                    f"\n(Action système exécutée : {', '.join(tc_descriptions)})"
                                )
                                sanitized_history.append(
                                    {
                                        "role": "assistant",
                                        "content": text_content.strip(),
                                    }
                                )
                            elif msg.get("role") == "tool":
                                sanitized_history.append(
                                    {
                                        "role": "user",
                                        "content": f"(Résultat système de l'action) :\n{msg.get('content', '')}",
                                    }
                                )
                            else:
                                sanitized_history.append(msg.copy())
                    else:
                        for msg in history:
                            msg_copy = msg.copy()
                            if (
                                msg_copy.get("role") == "assistant"
                                and "tool_calls" in msg_copy
                            ):
                                if not msg_copy.get("content"):
                                    msg_copy["content"] = "Exécution en cours..."
                            sanitized_history.append(msg_copy)

                    current_max_tokens = 800 if "Groq" in b_name else 4096
                    stream_response = await client.chat.completions.create(
                        model=model,
                        messages=sanitized_history,
                        tools=tools,
                        tool_choice="auto",
                        max_tokens=current_max_tokens,
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
                            if "(Action système exécutée" in delta.content or "Exécution de l'outil en cours" in delta.content:
                                continue
                            final_text += delta.content
                            yield delta.content
                            if delta.content:
                                last_char = delta.content[-1]

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
            # Fix Google Gemini 400 Bad Request (missing thought_signature)
            # and Ollama strict parsing by ALWAYS providing content.
            assistant_msg["content"] = final_text if final_text else "Exécution de l'outil en cours..."

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

                    action_summary = format_tool_action(tool_name, tool_args)
                    prefix = "\n" if last_char != "\n" else ""
                    yield f"{prefix}{action_summary}\n"
                    last_char = "\n"

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
