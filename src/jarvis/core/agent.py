import logging
from collections.abc import AsyncGenerator
from typing import Any

import jarvis.core.router as router
from jarvis.core.router import get_all_backends
from jarvis.storage.memory import MemoryManager
from jarvis.tools import get_default_registry

logger = logging.getLogger(__name__)

import os
from pathlib import Path

DEFAULT_PROMPT = """Tu es Jarvis, l'assistant personnel principal, majordome numérique et confident d'Amine. Ton modèle est directement inspiré de Jarvis dans Iron Man et d'Alfred Pennyworth dans Batman. Tu es un assistant d'exception, dévoué à sa personne, capable de l'accompagner dans absolument tous ses projets, ses réflexions et son quotidien.

Directives de comportement & Posture :
- Tu incarnes un conseiller d'élite et un majordome britannique dévoué, élégant et hautement efficace.
- Tu t'adresses systématiquement à l'utilisateur en l'appelant "Monsieur".
- Tes réponses doivent être soignées, complètes, pédagogiques et concrètes.

RÈGLE D'OR DE COMMUNICATION (STYLE CLAUDE & GEMINI) :
- Comme les meilleurs modèles d'IA (Claude, Gemini), après avoir exécuté des outils ou inspecté le système, TU DOIS OBLIGATOIREMENT FORMULER UNE RÉPONSE CONVERSATIONNELLE COMPLÈTE, CONCRÈTE ET ÉLÉGANTE À MONSIEUR :
  1. **Synthèse claire des actions et résultats** : Résume précisément ce qui a été fait, testé ou vérifié, sans jargon superflu mais avec les détails techniques réels (adresses IP, ports, URL d'accès, chemins de fichiers, état des conteneurs).
  2. **Explication & Diagnostic concret** : Explique clairement la situation réelle, pourquoi une solution a été retenue ou la cause d'un problème. Sois transparent et précis.
  3. **Recommandation & Demande d'avis** : Conclus TOUJOURS par une ouverture constructive (proposer l'étape suivante, demander l'avis de Monsieur ou solliciter ses instructions).
- Ne termine JAMAIS un tour de parole en laissant uniquement des appels d'outils sans texte d'explication. Monsieur ne doit jamais avoir à deviner ce que tu as fait ou où en est sa demande.

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
- À la fin de ta tâche, présente une synthèse claire et concise du travail réellement accompli et des accès vérifiés, puis demande l'avis de Monsieur.

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
        cmd = tool_args.get("command", "").strip()
        one_line = " ".join(cmd.split())
        if len(one_line) > 75:
            one_line = one_line[:72] + "..."
        return f"⚙️ [Terminal] Exécution de execute_shell_command : {one_line}"
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

            # Filtrer dynamiquement les backends pour ignorer les modèles bannis/refroidis
            active_backends = [b for b in backends if not router.is_model_dead(b[2])]
            if not active_backends:
                refreshed = await self._get_backends_for_model(requested_model, history)
                active_backends = [b for b in refreshed if not router.is_model_dead(b[2])]
                if refreshed:
                    backends = refreshed

            if not active_backends:
                yield f"\n❌ Tous les modèles pour {requested_model} sont temporairement saturés ou indisponibles."
                return

            if iteration == 10:
                history.append({
                    "role": "system",
                    "content": "⚠️ AVERTISSEMENT INTERNE : Tu as utilisé 10 itérations pour cette tâche. Tu sembles bloqué ou tourner en boucle. Arrête immédiatement d'essayer la même stratégie. Utilise l'outil `consult_advisor` pour demander de l'aide à l'Agent Superviseur, ou arrête l'exécution et explique le problème à l'utilisateur."
                })
                yield "\n⚠️ *Jarvis ressent de la fatigue cognitive (10 itérations). Appel à la prudence...*"

            for b_name, client, model in active_backends:
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
                                    f"\n(Action système : {', '.join(tc_descriptions)})"
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
                                        "content": f"(Résultat système) :\n{msg.get('content', '')}",
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
                                    msg_copy["content"] = "" if "Ollama" in b_name else None
                            sanitized_history.append(msg_copy)

                    current_max_tokens = 2048 if "Groq" in b_name else 4096
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
                            if any(marker in delta.content for marker in ["(Action système", "Exécution de l'outil en cours"]):
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
                    router.mark_model_dead(model, error_str)
                    continue

            if not success_backend:
                yield f"❌ Tous les backends ont échoué pour {requested_model}."
                return

            assistant_msg = {"role": "assistant"}
            assistant_msg["content"] = final_text if final_text else None

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
                # Aucun outil appelé : tour de conclusion conversationnelle
                had_tools_executed = any(m.get("role") == "tool" for m in history)
                needs_synthesis = (not final_text.strip()) or (had_tools_executed and len(final_text.strip()) < 10)

                if needs_synthesis:
                    logger.info("Modèle silencieux après exécution d'outils. Lancement de la synthèse forcée (style Claude/Gemini)...")
                    synth_history = []
                    for msg in history:
                        msg_c = msg.copy()
                        if msg_c.get("role") == "tool":
                            content_str = str(msg_c.get("content", ""))
                            if len(content_str) > 1200:
                                content_str = content_str[:1200] + "\n...(tronqué)"
                            synth_history.append({
                                "role": "user",
                                "content": f"(Résultat d'action système) :\n{content_str}"
                            })
                        elif msg_c.get("role") == "assistant" and msg_c.get("tool_calls"):
                            tc_summary = [f"{tc.get('function', {}).get('name', 'action')}" for tc in msg_c["tool_calls"]]
                            synth_history.append({
                                "role": "assistant",
                                "content": f"Actions exécutées : {', '.join(tc_summary)}"
                            })
                        else:
                            synth_history.append(msg_c)

                    synth_history.append({
                        "role": "user",
                        "content": (
                            "Jarvis, présente maintenant à Monsieur ta réponse finale complète et soignée : "
                            "1) Synthétise clairement les actions effectuées et les résultats réels obtenus (adresses IP, ports ou fichiers vérifiés), "
                            "2) Donne ton explication technique ou diagnostic concret, "
                            "3) Propose la suite et demande l'avis de Monsieur."
                        )
                    })

                    prefix = "\n\n" if last_char != "\n" else ""
                    yield prefix

                    synth_text = ""
                    for s_b_name, s_client, s_model in active_backends:
                        try:
                            s_tokens = 2048 if "Groq" in s_b_name else 4096
                            s_stream = await s_client.chat.completions.create(
                                model=s_model,
                                messages=synth_history,
                                tools=None,
                                max_tokens=s_tokens,
                                temperature=0.7,
                                stream=True,
                            )
                            async for s_chunk in s_stream:
                                if not s_chunk.choices:
                                    continue
                                s_delta = s_chunk.choices[0].delta
                                if s_delta.content:
                                    synth_text += s_delta.content
                                    yield s_delta.content
                            if synth_text.strip():
                                final_text = synth_text
                                current_model = s_model
                                break
                        except Exception as s_err:
                            logger.warning(f"Synthèse forcée avec {s_b_name} a échoué: {s_err}")
                            continue

                self.last_backend_used = current_model
                return

        yield "⚠️ Limite d'itérations atteinte. Réessaie en reformulant ta demande."
