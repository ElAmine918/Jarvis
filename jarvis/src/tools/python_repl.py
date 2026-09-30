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
        
        code = kwargs.get("code")
        script_name = f"script_{uuid.uuid4().hex[:8]}.py"
        script_path = os.path.join("/app/workspace", script_name)
        
        try:
            with open(script_path, "w") as f:
                f.write(code)
                
            # SECURITY FIX: Bubblewrap (bwrap) isolation
            # Only /app/workspace is mounted rw. /app/src is NOT mounted! 
            # No network, completely isolated process tree.
            bwrap_cmd = [
                "bwrap",
                "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/bin", "/bin",
                "--ro-bind", "/lib", "/lib",
                "--ro-bind", "/lib64", "/lib64",
                "--ro-bind", "/etc/resolv.conf", "/etc/resolv.conf",
                "--bind", "/app/workspace", "/app/workspace",
                "--unshare-all", # Drop all namespaces (network, ipc, pid)
                "--die-with-parent",
                "python3", script_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *bwrap_cmd,
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
                    return f"✅ Exécution réussie (Bac à sable bwrap).
{output}"
                else:
                    return f"❌ Erreur d'exécution (Code {proc.returncode}).
{output}"
            except asyncio.TimeoutError:
                proc.kill()
                return "❌ Erreur : Le script a dépassé le temps limite de 15 secondes (boucle infinie ?)."
                
        except Exception as e:
            # Fallback if bwrap is missing/blocked
            return f"❌ Erreur système lors de l'exécution: {str(e)}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
