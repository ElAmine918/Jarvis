"""
Outil d'information système — métriques fiables et multi-plateformes avec psutil.
Données en lecture seule, garanties sans risque d'injection.
"""

import asyncio
import logging
import os
import shutil
from typing import Any

import psutil

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


async def _run_command(*args: str, timeout: float = 5.0) -> str:
    """Exécute une commande binaire fixe avec timeout de sécurité."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"Erreur : {e}"


class SystemInfoTool(Tool):
    """Informations système en lecture seule."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return (
            "Retourne des informations système détaillées en lecture seule : "
            "cpu, memory, disk, processes, containers, network_ports, ou 'all'. "
            "Données sûres, multi-plateformes (Linux, macOS, Docker)."
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
                    "description": "Catégorie d'information à récupérer.",
                }
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "all", **kwargs) -> str:
        parts = []

        # --- CPU ---
        if query in ("cpu", "all"):
            try:
                load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
                cores = psutil.cpu_count(logical=True) or 1
                physical = psutil.cpu_count(logical=False) or cores
                usage = psutil.cpu_percent(interval=0.1)
                out = (
                    f"Utilisation globale: {usage}%\n"
                    f"Cœurs: {cores} logiques ({physical} physiques)\n"
                    f"Load Average (1m, 5m, 15m): {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
                )
                parts.append(f"### CPU\n{out}")
            except Exception as e:
                parts.append(f"### CPU\n❌ {e}")

        # --- MEMORY ---
        if query in ("memory", "all"):
            try:
                vm = psutil.virtual_memory()
                total_gb = vm.total / (1024**3)
                used_gb = vm.used / (1024**3)
                avail_gb = vm.available / (1024**3)
                swap = psutil.swap_memory()
                swap_used_gb = swap.used / (1024**3)
                swap_total_gb = swap.total / (1024**3)

                out = (
                    f"RAM: {used_gb:.2f} Go / {total_gb:.2f} Go ({vm.percent}% utilisé, {avail_gb:.2f} Go disponibles)\n"
                    f"Swap: {swap_used_gb:.2f} Go / {swap_total_gb:.2f} Go ({swap.percent}%)"
                )
                parts.append(f"### Mémoire\n{out}")
            except Exception as e:
                parts.append(f"### Mémoire\n❌ {e}")

        # --- DISK ---
        if query in ("disk", "all"):
            try:
                root_usage = psutil.disk_usage("/")
                total_gb = root_usage.total / (1024**3)
                used_gb = root_usage.used / (1024**3)
                free_gb = root_usage.free / (1024**3)
                out = f"Partition racine (/): {used_gb:.1f} Go / {total_gb:.1f} Go ({root_usage.percent}% utilisé, {free_gb:.1f} Go libres)"
                parts.append(f"### Disque\n{out}")
            except Exception as e:
                parts.append(f"### Disque\n❌ {e}")

        # --- PROCESSES ---
        if query in ("processes", "all"):
            try:
                procs = []
                for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
                    try:
                        info = p.info
                        procs.append(info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Trier par utilisation mémoire décroissante
                procs.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)
                top = procs[:12]
                lines = [f"{p['pid']:<7} {p.get('memory_percent', 0.0):>5.1f}% RAM  {p.get('name', 'unknown')}" for p in top]
                header = f"{'PID':<7} {'%MEM':>5}      {'COMMANDE'}"
                parts.append(f"### Processus (Top 12 par RAM)\n{header}\n" + "\n".join(lines))
            except Exception as e:
                parts.append(f"### Processus\n❌ {e}")

        # --- CONTAINERS ---
        if query in ("containers", "all"):
            if shutil.which("docker"):
                try:
                    out = await _run_command(
                        "docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.Image}}"
                    )
                    parts.append(f"### Conteneurs Docker\n{out if out else 'Aucun conteneur.'}")
                except Exception as e:
                    parts.append(f"### Conteneurs Docker\n❌ {e}")
            else:
                parts.append("### Conteneurs Docker\nDocker CLI non présent dans l'environnement local.")

        # --- NETWORK PORTS ---
        if query in ("network_ports", "all"):
            try:
                # Utiliser psutil pour lister les ports en écoute
                listening = []
                try:
                    for conn in psutil.net_connections(kind="inet"):
                        if conn.status == psutil.CONN_LISTEN:
                            laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
                            listening.append(f"{conn.type.name:<4} {laddr:<22} (PID: {conn.pid})")
                except (psutil.AccessDenied, Exception):
                    # Fallback sur ss ou netstat si les permissions noyau bloquent
                    if shutil.which("ss"):
                        out = await _run_command("ss", "-tlnp")
                        listening = out.splitlines()[:15]
                    elif shutil.which("lsof"):
                        out = await _run_command("lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n")
                        listening = out.splitlines()[:15]

                if listening:
                    parts.append(f"### Ports en écoute\n" + "\n".join(listening[:15]))
                else:
                    parts.append("### Ports en écoute\nAucun port détecté ou permissions restreintes.")
            except Exception as e:
                parts.append(f"### Ports en écoute\n❌ {e}")

        return "\n\n".join(parts) if parts else f"❌ Requête inconnue: '{query}'"
