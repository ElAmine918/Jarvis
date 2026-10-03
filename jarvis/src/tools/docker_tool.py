"""
Outil Docker v5 — via docker-socket-proxy (pas de socket brut).
La variable DOCKER_HOST pointe vers le proxy filtré.
"""

import asyncio
import logging
import os
import re
from typing import Any

from .base import Tool

logger = logging.getLogger(__name__)

CONTAINER_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")

# docker-socket-proxy est configuré par DOCKER_HOST dans l'env
# docker-ce-cli le lira automatiquement


def _validate_name(name: str):
    if not CONTAINER_NAME_RE.match(name):
        return f"🚫 Nom invalide : '{name}'."
    if len(name) > 128:
        return "🚫 Nom trop long."
    return None


class DockerTool(Tool):
    @property
    def name(self) -> str:
        return "manage_docker"

    @property
    def description(self) -> str:
        return (
            "Gère Docker via un proxy sécurisé. "
            "Lecture : ps, logs (limités), inspect (.State uniquement). "
            "Actions : start, restart, stop — uniquement sur les conteneurs "
            "avec le label 'jarvis.manageable=true'. "
            "rm et compose-up n'existent pas."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ps", "logs", "inspect", "start", "restart", "stop"],
                },
                "container_name": {"type": "string"},
                "lines": {
                    "type": "integer",
                    "description": "Lignes de logs (max 200).",
                },
            },
            "required": ["action"],
        }

    async def _run(self, *args: str) -> str:
        env = {**os.environ}  # hérite DOCKER_HOST du conteneur
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            out = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()
            if proc.returncode != 0:
                return f"❌ Erreur (code {proc.returncode}):\n{err}"
            result = out or "✅ OK"
            return result[:8000] + ("\n...[tronqué]" if len(result) > 8000 else "")
        except asyncio.TimeoutError:
            return "⏱️ Timeout Docker."
        except Exception as e:
            return f"❌ {e}"

    async def _is_manageable(self, name: str) -> bool:
        out = await self._run(
            "docker",
            "inspect",
            name,
            "--format",
            '{{index .Config.Labels "jarvis.manageable"}}',
        )
        return out.strip() == "true"

    async def execute(
        self, action: str, container_name: str = None, lines: int = 100, **kwargs
    ) -> str:

        if container_name is not None:
            err = _validate_name(container_name)
            if err:
                return err

        if action == "ps":
            return await self._run(
                "docker",
                "ps",
                "-a",
                "--format",
                "table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}",
            )

        elif action == "logs":
            if not container_name:
                return "❌ container_name requis."
            lines = min(max(lines, 1), 200)
            return await self._run(
                "docker", "logs", "--tail", str(lines), container_name
            )

        elif action == "inspect":
            if not container_name:
                return "❌ container_name requis."
            return await self._run(
                "docker", "inspect", container_name, "--format", "{{json .State}}"
            )

        elif action in ("start", "restart", "stop"):
            if not container_name:
                return "❌ container_name requis."
            if not await self._is_manageable(container_name):
                return (
                    f"🛡️ Action '{action}' bloquée sur '{container_name}' : "
                    f"label 'jarvis.manageable=true' absent.\n"
                    f"Si cette action est absolument nécessaire, utilisez l'outil `ask_admin_approval` pour demander la permission à l'administrateur système."
                )
            return await self._run("docker", action, container_name)

        return f"❌ Action inconnue: '{action}'"
