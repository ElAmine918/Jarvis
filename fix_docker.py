import asyncio
import logging
import os
import shlex
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

class DockerTool(Tool):
    """Gestion complète des conteneurs Docker via le socket proxy sécurisé."""

    @property
    def name(self) -> str:
        return "manage_docker"

    @property
    def description(self) -> str:
        return "Gère les conteneurs Docker."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ps", "logs", "inspect", "start", "restart", "stop", "rm", "stats", "exec", "compose"],
                    "description": "L'action Docker à exécuter.",
                },
                "container_name": {
                    "type": "string",
                    "description": "Nom ou ID du conteneur.",
                },
                "command": {
                    "type": "string",
                    "description": "Commande à exécuter.",
                },
                "lines": {
                    "type": "integer",
                    "description": "Nombre de lignes de logs.",
                },
            },
            "required": ["action"],
            "type": "object",
        }

    async def _run(self, *args: str, timeout: float = 30.0) -> str:
        # SECURE: Always use docker proxy socket to prevent root access to docker.sock
        env = {**os.environ, "DOCKER_HOST": os.getenv("DOCKER_HOST", "tcp://127.0.0.1:2375")}
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                return f"❌ Erreur Docker (code {proc.returncode}) :\n{err or out}"

            result = out or "✅ OK"
            if len(result) > 10000:
                result = result[:10000] + "\n...[tronqué]"
            return result
        except asyncio.TimeoutError:
            return f"⏱️ Timeout Docker ({timeout}s)."
        except Exception as e:
            return f"❌ Erreur d'exécution Docker : {e}"

    async def execute(
        self,
        action: str,
        container_name: str = None,
        command: str = None,
        lines: int = 100,
        **kwargs,
    ) -> str:
        if action == "ps":
            return await self._run("docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}")
        elif action == "logs":
            if not container_name: return "❌ 'container_name' requis."
            lines = min(max(lines or 100, 1), 500)
            return await self._run("docker", "logs", "--tail", str(lines), container_name)
        elif action == "inspect":
            if not container_name: return "❌ 'container_name' requis."
            return await self._run("docker", "inspect", container_name, "--format", "{{json .State}}")
        elif action in ("start", "restart", "stop"):
            if not container_name: return "❌ 'container_name' requis."
            return await self._run("docker", action, container_name)
        elif action == "rm":
            if not container_name: return "❌ 'container_name' requis."
            return await self._run("docker", "rm", "-f", container_name)
        elif action == "stats":
            if container_name:
                return await self._run("docker", "stats", "--no-stream", container_name)
            return await self._run("docker", "stats", "--no-stream")
        elif action == "exec":
            if not container_name or not command: return "❌ 'container_name' et 'command' requis."
            try: cmd_parts = shlex.split(command)
            except Exception: cmd_parts = ["sh", "-c", command]
            return await self._run("docker", "exec", container_name, *cmd_parts, timeout=45.0)
        elif action == "compose":
            subcmd = command or "ps"
            try: compose_args = shlex.split(subcmd)
            except Exception: compose_args = [subcmd]
            return await self._run("docker", "compose", *compose_args, timeout=60.0)

        return f"❌ Action Docker inconnue : '{action}'"
