import logging
import asyncio
from typing import Dict, Any
from .base import Tool

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
    def parameters(self) -> Dict[str, Any]:
        return {
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Le code Python à exécuter. Pense à utiliser `print()` pour afficher les résultats."
                }
            },
            "required": ["code"],
            "type": "object"
        }

    async def execute(self, **kwargs) -> str:
        code = kwargs.get("code")
        
        # Write code to a temp file in /app/workspace
        import os
        import uuid
        script_name = f"script_{uuid.uuid4().hex[:8]}.py"
        script_path = os.path.join("/app/workspace", script_name)
        
        try:
            with open(script_path, "w") as f:
                f.write(code)
                
            # Run the script using Python inside the workspace
            # We use asyncio.create_subprocess_exec
            # SECURITY FIX: Strip environment variables to prevent API key leakage
            proc = await asyncio.create_subprocess_exec(
                "python3", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/app/workspace",
                env={"PYTHONPATH": "/app/workspace"} # No access to TELEGRAM_BOT_TOKEN or GEMINI_API_KEY
            )
            
            # Timeout after 15 seconds to prevent infinite loops
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
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
                return "❌ Erreur : Le script a dépassé le temps limite de 15 secondes (boucle infinie ?)."
                
        except Exception as e:
            return f"❌ Erreur système lors de l'exécution: {str(e)}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
