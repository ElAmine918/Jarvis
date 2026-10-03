import asyncio
import logging
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)


class PythonREPLTool(Tool):
    @property
    def name(self) -> str:
        return "python_interpreter"

    @property
    def description(self) -> str:
        return (
            "Exécute du code Python 3 dans un bac à sable (conteneur éphémère). "
            "Parfait pour les calculs mathématiques complexes, l'analyse de données, "
            "ou tester des algorithmes de manière sécurisée."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Le code Python à exécuter. Pense à utiliser `print()` pour afficher les résultats.",
                }
            },
            "required": ["code"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        import os
        import uuid

        code = kwargs.get("code", "")

        # Validation: Limite de taille du code (50 KB)
        _MAX_CODE_SIZE = 50 * 1024  # 50 KB
        if len(code.encode("utf-8")) > _MAX_CODE_SIZE:
            return f"❌ Le code dépasse la limite autorisée de {_MAX_CODE_SIZE // 1024} KB."

        script_name = f"script_{uuid.uuid4().hex[:8]}.py"
        script_path = os.path.join("/app/workspace", script_name)

        try:
            with open(script_path, "w") as f:
                f.write(code)

            # C-01 : Sandbox via bubblewrap (déjà installé dans le Dockerfile L27)
            # --unshare-net  → coupe l'accès réseau (pas de reverse shell, pas d'exfiltration)
            # --ro-bind / /  → filesystem en lecture seule
            # --tmpfs /tmp   → /tmp éphémère (nettoyé à chaque exécution)
            # --bind /app/workspace /app/workspace → seul workspace accessible en écriture
            # env={"PATH": ...} → uniquement PATH, toutes les clés API supprimées
            bwrap_cmd = [
                "bwrap",
                "--ro-bind",
                "/",
                "/",  # fs racine en lecture seule
                "--dev",
                "/dev",  # devices minimaux
                "--tmpfs",
                "/tmp",  # /tmp isolé et éphémère
                "--bind",
                "/app/workspace",
                "/app/workspace",  # workspace rw
                "--unshare-net",  # PAS de réseau
                "--unshare-pid",  # espace PID isolé
                "--die-with-parent",  # tué si Jarvis meurt
                "python3",
                script_path,
            ]

            # Garder uniquement PATH (pas de clés API, pas de tokens)
            safe_env = {"PATH": "/usr/local/bin:/usr/bin:/bin"}

            proc = await asyncio.create_subprocess_exec(
                *bwrap_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/app/workspace",
                env=safe_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=15.0
                )
                output = ""
                if stdout:
                    output += f"--- STDOUT ---\n{stdout.decode('utf-8')}\n"
                if stderr:
                    output += f"--- STDERR ---\n{stderr.decode('utf-8')}\n"

                if proc.returncode == 0:
                    return f"✅ Exécution réussie (sandbox bubblewrap — réseau coupé).\n{output}"
                else:
                    return f"❌ Erreur d'exécution (Code {proc.returncode}).\n{output}"
            except asyncio.TimeoutError:
                proc.kill()
                return "❌ Erreur : Le script a dépassé le temps limite de 15 secondes (boucle infinie ?)."

        except Exception as e:
            return f"❌ Erreur système lors de l'exécution: {e!s}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
