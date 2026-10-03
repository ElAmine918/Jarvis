import asyncio
import logging
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class GitTool(Tool):
    @property
    def name(self) -> str:
        return "git_operations"

    @property
    def description(self) -> str:
        return (
            "Exécute des commandes Git (status, add, commit, diff, log, pull). "
            "Ne demande jamais d'approbation pour les opérations de lecture (status, diff). "
            "Par défaut, le dossier de travail est /app."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "command": {
                    "type": "string",
                    "description": "La commande git complète (ex: 'git status', 'git commit -m \"Fix\"').",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Le dossier cible (par défaut: /app).",
                },
            },
            "required": ["command"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        import shlex

        from jarvis.tools.filesystem import _safe_path

        command = kwargs.get("command")
        working_dir = kwargs.get("working_dir", "/app")

        safe_dir = _safe_path(working_dir)
        if safe_dir is None or not safe_dir.is_dir():
            return f"🚫 Sécurité: Le dossier '{working_dir}' est interdit ou invalide. Opérations Git limitées à /app."

        if not command.startswith("git "):
            return "❌ Erreur : La commande doit commencer par 'git '."

        try:
            args = shlex.split(command)
        except ValueError as e:
            return f"❌ Erreur de syntaxe dans la commande: {e}"

        if args[0] != "git":
            return "❌ Erreur de sécurité: Seul le binaire git est autorisé."

        # Security: Allowlist des sous-commandes autorisées
        _GIT_ALLOWED_SUBCOMMANDS = {
            "status",
            "add",
            "commit",
            "diff",
            "log",
            "pull",
            "push",
            "branch",
            "checkout",
            "merge",
            "fetch",
            "show",
            "stash",
            "remote",
            "tag",
            "describe",
            "rev-parse",
            "ls-files",
        }
        # Security: Options dangereuses permettant l'exécution de code arbitraire
        _GIT_DANGEROUS_FLAGS = {
            "-c",
            "--config",
            "--exec-path",
            "--git-dir",
            "--work-tree",
        }

        subcommand = args[1] if len(args) > 1 else ""
        if subcommand not in _GIT_ALLOWED_SUBCOMMANDS:
            return (
                f"🚫 Sécurité : sous-commande git '{subcommand}' non autorisée. "
                f"Commandes permises : {', '.join(sorted(_GIT_ALLOWED_SUBCOMMANDS))}."
            )

        for arg in args[2:]:
            flag = arg.split("=")[0]  # normalise --config=core.pager → --config
            if flag in _GIT_DANGEROUS_FLAGS:
                return (
                    f"🚫 Sécurité : l'option '{flag}' est interdite car elle peut exécuter "
                    f"du code arbitraire via les hooks git ou les commandes configurées."
                )

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(safe_dir),
            )
            stdout, stderr = await proc.communicate()

            output = ""
            if stdout:
                output += stdout.decode("utf-8")
            if stderr:
                output += "\n(Stderr): " + stderr.decode("utf-8")

            return (
                output if output else "✅ Commande exécutée avec succès (sans sortie)."
            )
        except Exception as e:
            return f"❌ Erreur Git: {e!s}"
