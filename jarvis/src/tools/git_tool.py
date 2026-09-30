import logging
import asyncio
from typing import Dict, Any
from .base import Tool

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
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "command": {
                    "type": "string",
                    "description": "La commande git complète (ex: 'git status', 'git commit -m \"Fix\"')."
                },
                "working_dir": {
                    "type": "string",
                    "description": "Le dossier cible (par défaut: /app)."
                }
            },
            "required": ["command"],
            "type": "object"
        }

    async def execute(self, **kwargs) -> str:
        command = kwargs.get("command")
        working_dir = kwargs.get("working_dir", "/app")
        
        import shlex
        if not command.startswith("git "):
            return "❌ Erreur : La commande doit commencer par 'git '."
            
        # SECURITY FIX: Parse safely to avoid shell injection (e.g. 'git status ; rm -rf /')
        try:
            args = shlex.split(command)
        except ValueError as e:
            return f"❌ Erreur de syntaxe dans la commande: {e}"
            
        if args[0] != "git":
            return "❌ Erreur de sécurité: Seul le binaire git est autorisé."
            
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            stdout, stderr = await proc.communicate()
            
            output = ""
            if stdout:
                output += stdout.decode('utf-8')
            if stderr:
                output += "\n(Stderr): " + stderr.decode('utf-8')
                
            return output if output else "✅ Commande exécutée avec succès (sans sortie)."
        except Exception as e:
            return f"❌ Erreur Git: {str(e)}"
