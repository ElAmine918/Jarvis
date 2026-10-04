import asyncio
import logging
import os
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class ShellTool(Tool):
    """Exécute des commandes shell bash directement dans l'environnement Jarvis."""

    @property
    def name(self) -> str:
        return "execute_shell_command"

    @property
    def description(self) -> str:
        return (
            "Exécute une commande shell bash directement sur le système hôte/conteneur. "
            "Permet d'exécuter des scripts, commandes Linux, outils CLI (curl, git, docker, python, apt, etc.). "
            "Retourne stdout et stderr combinés."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "command": {
                    "type": "string",
                    "description": "La commande shell bash à exécuter.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Le répertoire d'exécution (par défaut /app ou /repo).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout en secondes (défaut: 60).",
                },
            },
            "required": ["command"],
            "type": "object",
        }

    async def execute(self, command: str = "", cwd: str = None, timeout: int = 60, **kwargs) -> str:
        if not command.strip():
            return "❌ Commande shell vide."

        working_dir = cwd or "/app"
        if not os.path.isdir(working_dir):
            if os.path.isdir("/repo"):
                working_dir = "/repo"
            else:
                working_dir = os.getcwd()

        logger.info(f"Exécution shell: {command!r} (dans {working_dir})")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )

            out_text = stdout.decode("utf-8", errors="replace").strip()
            err_text = stderr.decode("utf-8", errors="replace").strip()

            result_parts = []
            if out_text:
                result_parts.append(out_text)
            if err_text:
                result_parts.append(f"--- STDERR ---\n{err_text}")

            full_output = "\n".join(result_parts) if result_parts else "✅ Commande exécutée (aucun retour)."

            if proc.returncode != 0:
                full_output = f"⚠️ Code de retour {proc.returncode} :\n{full_output}"

            if len(full_output) > 10000:
                full_output = full_output[:10000] + "\n...[tronqué]"

            return full_output

        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return f"⏱️ Timeout : la commande a dépassé la limite de {timeout} secondes."
        except Exception as e:
            return f"❌ Erreur lors de l'exécution shell : {e}"
