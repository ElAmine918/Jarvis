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
        import os
        import uuid
        import asyncio
        
        code = kwargs.get("code")
        script_name = f"script_{uuid.uuid4().hex[:8]}.py"
        script_path = os.path.join("/app/workspace", script_name)
        
        try:
            with open(script_path, "w") as f:
                f.write(code)
                
            # Exécution isolée : on purge les variables d'environnement (API keys)
            proc = await asyncio.create_subprocess_exec(
                "python3", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/app/workspace",
                env={} # No env vars (API keys)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
                output = ""
                if stdout:
                    output += f"--- STDOUT ---
{stdout.decode('utf-8')}
"
                if stderr:
                    output += f"--- STDERR ---
{stderr.decode('utf-8')}
"
                
                if proc.returncode == 0:
                    return f"✅ Exécution réussie.
{output}"
                else:
                    return f"❌ Erreur d'exécution (Code {proc.returncode}).
{output}"
            except asyncio.TimeoutError:
                proc.kill()
                return "❌ Erreur : Le script a dépassé le temps limite de 15 secondes (boucle infinie ?)."
                
        except Exception as e:
            return f"❌ Erreur système lors de l'exécution: {str(e)}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)