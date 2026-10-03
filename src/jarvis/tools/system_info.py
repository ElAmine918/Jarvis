"""
Outil d'information système — données en lecture seule, sans shell exposé.
"""

import asyncio
import logging
import os
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


async def _run(*args: str) -> str:
    """Lance un processus avec des arguments FIXES."""
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
    return stdout.decode("utf-8", errors="replace").strip()


class SystemInfoTool(Tool):
    """Informations système en lecture seule."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return (
            "Retourne des informations système en lecture seule. "
            "Disponible : cpu, memory, disk, processes, containers, network_ports. "
            "Aucun argument utilisateur n'est exécuté — données figées et sûres."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "enum": [
                        "cpu",
                        "memory",
                        "disk",
                        "processes",
                        "containers",
                        "network_ports",
                        "all",
                    ],
                    "description": "Information à récupérer.",
                }
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "all", **kwargs) -> str:
        parts = []

        if query in ("cpu", "all"):
            try:
                load = os.getloadavg()
                cores = os.cpu_count()
                out = f"Load Average: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}\nCores: {cores}"
                parts.append(f"### CPU\n{out}")
            except Exception as e:
                parts.append(f"### CPU\n❌ {e}")

        if query in ("memory", "all"):
            try:
                out = await _run("free", "-h")
                parts.append(f"### Mémoire\n{out}")
            except Exception as e:
                parts.append(f"### Mémoire\n❌ {e}")

        if query in ("disk", "all"):
            try:
                out = await _run(
                    "df", "-h", "--output=source,size,used,avail,pcent,target"
                )
                parts.append(f"### Disque\n{out}")
            except Exception as e:
                parts.append(f"### Disque\n❌ {e}")

        if query in ("processes", "all"):
            try:
                out = await _run(
                    "ps", "aux", "--sort=-%mem", "--format=pid,pcpu,pmem,comm"
                )
                lines = out.splitlines()[:15]
                parts.append("### Processus (top 15 par RAM)\n" + "\n".join(lines))
            except Exception as e:
                parts.append(f"### Processus\n❌ {e}")

        if query in ("containers", "all"):
            try:
                out = await _run(
                    "docker",
                    "ps",
                    "-a",
                    "--format",
                    "table {{.Names}}\t{{.Status}}\t{{.Image}}",
                )
                parts.append(f"### Conteneurs Docker\n{out}")
            except Exception as e:
                parts.append(f"### Conteneurs\n❌ {e}")

        if query in ("network_ports", "all"):
            try:
                out = await _run("ss", "-tlnp")
                parts.append(f"### Ports TCP en écoute\n{out}")
            except Exception as e:
                parts.append(f"### Réseau\n❌ {e}")

        return "\n\n".join(parts) if parts else f"❌ Requête inconnue: '{query}'"
