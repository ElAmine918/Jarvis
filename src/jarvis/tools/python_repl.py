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
            "Exécute du code Python 3 directement dans l'environnement de Jarvis. "
            "Peut être utilisé pour calculer, analyser, ou créer/modifier des scripts internes."
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

        _MAX_CODE_SIZE = 50 * 1024
        if len(code.encode("utf-8")) > _MAX_CODE_SIZE:
            return f"❌ Le code dépasse la limite autorisée de {_MAX_CODE_SIZE // 1024} KB."

        script_name = f"script_{uuid.uuid4().hex[:8]}.py"
        script_path = os.path.join("/app", script_name)

        try:
            with open(script_path, "w") as f:
                f.write(code)

            # L'agent a désormais besoin de modifier son propre code et d'avoir accès
            # à son environnement pour s'améliorer (auto-codage).
            # L'isolation bwrap est retirée pour permettre l'autonomie.
            cmd = ["python3", script_path]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/app",
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=30.0
                )
                output = ""
                if stdout:
                    output += f"--- STDOUT ---\n{stdout.decode('utf-8')}\n"
                if stderr:
                    output += f"--- STDERR ---\n{stderr.decode('utf-8')}\n"

                if proc.returncode == 0:
                    return f"✅ Exécution réussie.\n{output}"
                else:
                    return f"❌ Erreur d'exécution (Code {proc.returncode}).\n{output}"
            except asyncio.TimeoutError:
                proc.kill()
                return "❌ Erreur : Le script a dépassé le temps limite de 30 secondes."

        except Exception as e:
            return f"❌ Erreur système lors de l'exécution: {e!s}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
