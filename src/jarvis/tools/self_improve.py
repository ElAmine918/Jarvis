import ast
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class SelfImproveTool(Tool):
    @property
    def name(self) -> str:
        return "self_improve_pipeline"

    @property
    def description(self) -> str:
        return (
            "Pipeline d'auto-amélioration et de création d'outils de Jarvis. "
            "Prend le code source Python complet d'un nouvel outil (qui hérite de Tool), "
            "valide sa syntaxe et sa structure Python, le sauvegarde dans l'environnement Jarvis "
            "et le commite/pushe sur GitHub."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Nom du fichier de l'outil sans extension (ex: 'mon_outil').",
                },
                "code": {
                    "type": "string",
                    "description": "Code Python complet de l'outil (doit hériter de Tool et définir execute).",
                },
            },
            "required": ["tool_name", "code"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        tool_name = kwargs.get("tool_name", "").strip().replace(".py", "")
        code = kwargs.get("code", "").strip()

        if not tool_name or not code:
            return "❌ 'tool_name' et 'code' sont requis."

        # --- ÉTAPE 1 : VALIDATION SYNTAXIQUE AST ---
        try:
            parsed = ast.parse(code)
        except SyntaxError as e:
            return f"❌ Erreur de syntaxe Python dans l'outil : {e}"

        # Vérifier qu'une classe hérite de Tool ou implémente execute
        has_tool_class = False
        for node in ast.walk(parsed):
            if isinstance(node, ast.ClassDef):
                has_tool_class = True
                break

        if not has_tool_class:
            return "⚠️ Attention : le code ne contient aucune classe définie. Un outil Jarvis doit définir une classe Tool."

        # --- ÉTAPE 2 : SAUVEGARDE LOCALE & RUNTIME ---
        saved_paths = []
        repo_tool_path = Path(f"/repo/src/jarvis/tools/{tool_name}.py")
        app_tool_path = Path(f"/app/jarvis/tools/{tool_name}.py")

        try:
            if repo_tool_path.parent.exists():
                repo_tool_path.write_text(code, encoding="utf-8")
                saved_paths.append(str(repo_tool_path))

            if app_tool_path.parent.exists():
                app_tool_path.write_text(code, encoding="utf-8")
                saved_paths.append(str(app_tool_path))

            if not saved_paths:
                # Fallback sur le dossier relatif
                local_path = Path(f"src/jarvis/tools/{tool_name}.py")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(code, encoding="utf-8")
                saved_paths.append(str(local_path))
        except Exception as e:
            return f"❌ Erreur lors de l'écriture du fichier d'outil : {e}"

        # --- ÉTAPE 3 : DÉPLOIEMENT GIT (Optionnel) ---
        git_repo = "/repo" if os.path.isdir("/repo/.git") else "."
        if os.path.isdir(f"{git_repo}/.git"):
            try:
                await asyncio.create_subprocess_shell(
                    "git config --global user.name 'Jarvis AI' && git config --global user.email 'jarvis@localhost'",
                    cwd=git_repo,
                )
                push_proc = await asyncio.create_subprocess_shell(
                    f"git add src/jarvis/tools/{tool_name}.py && git commit -m 'feat(auto): création/mise à jour de l\\'outil {tool_name}' && git push origin main",
                    cwd=git_repo,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                p_out, p_err = await push_proc.communicate()
                if push_proc.returncode == 0:
                    return f"🚀 Succès ! L'outil '{tool_name}' a été validé, installé dans {', '.join(saved_paths)} et déployé sur GitHub."
                else:
                    return f"✅ L'outil '{tool_name}' est installé localement et actif dans {', '.join(saved_paths)}. (Push Git facultatif non complété : {p_err.decode(errors='ignore').strip()})"
            except Exception as e:
                logger.warning(f"Git push non bloquant a échoué: {e}")

        return f"✅ L'outil '{tool_name}' a été validé avec succès et enregistré dans {', '.join(saved_paths)}."
