import asyncio
import logging
import os
from typing import Any

from jarvis.core.agent import JarvisAgent
from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

class SelfImproveTool(Tool):
    @property
    def name(self) -> str:
        return "self_improve_pipeline"

    @property
    def description(self) -> str:
        return (
            "Pipeline CI/CD interne de Jarvis. "
            "Prend le code source complet d'un outil (nouveau ou modifié), "
            "l'envoie à une instance IA Auditeur (isolée) pour validation de sécurité, "
            "lance les tests de non-régression, et s'il réussit, le sauvegarde dans le système "
            "et le déploie automatiquement sur GitHub."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "tool_name": {"type": "string", "description": "Nom du fichier de l'outil (ex: mon_outil.py)."},
                "code": {"type": "string", "description": "Code Python complet de l'outil (doit hériter de Tool et être prêt à l'emploi)."}
            },
            "required": ["tool_name", "code"],
            "type": "object",
        }

    async def execute(self, **kwargs) -> str:
        tool_name = kwargs.get("tool_name", "").replace(".py", "")
        code = kwargs.get("code", "")
        
        target_path = f"/app/jarvis/tools/{tool_name}.py"
        
        # --- ÉTAPE 1 : AUDIT ISOLÉ (L'INSPECTEUR) ---
        auditor = JarvisAgent()
        # On crée un historique vierge pour l'auditeur pour garantir l'isolation
        audit_history = [
            {
                "role": "user",
                "content": f"Tu es un Auditeur de Sécurité Python impitoyable. Ton but est de vérifier ce code généré par une IA. "
                           f"Cherche les failles de type SSRF, exécution de commandes arbitraires (shell non protégé), boucles infinies ou suppression de fichiers système. "
                           f"Tu n'as PAS le droit d'utiliser des outils, tu dois juste lire le code. "
                           f"Si le code est sûr et bien formaté, réponds UNIQUEMENT par le mot 'APPROUVÉ'. "
                           f"Si le code est dangereux, réponds par 'REJETÉ:' suivi de la raison détaillée.\n\n"
                           f"Code à auditer :\n```python\n{code}\n```"
            }
        ]
        
        audit_result = ""
        # On force un modèle rapide pour l'audit si possible, ou on laisse auto
        async for chunk in auditor.process_message(audit_history, session_id="auditor_internal", requested_model="jarvis-auto"):
            audit_result += chunk
            
        if "APPROUVÉ" not in audit_result.upper():
            return f"❌ ÉCHEC DE L'AUDIT DE SÉCURITÉ (Rejeté par l'instance isolée) :\n{audit_result}\n\nCorrige le code et réessaie."
            
        # --- ÉTAPE 2 : TESTS DE NON-RÉGRESSION ---
        with open(target_path, "w") as f:
            f.write(code)
            
        # On vérifie que la syntaxe est bonne et que les tests globaux (sécurité/imports) passent
        proc = await asyncio.create_subprocess_shell(
            "PYTHONPATH=/app pytest /app/tests/test_security.py",
            cwd="/app",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            os.remove(target_path)
            return f"❌ ÉCHEC DU DÉPLOIEMENT : L'outil contient des erreurs de syntaxe ou casse la sécurité système.\n{stdout.decode()}\n{stderr.decode()}"
            
        # --- ÉTAPE 3 : DÉPLOIEMENT GITHUB ---
        # On configure l'identité Git si elle ne l'est pas
        await asyncio.create_subprocess_shell("git config --global user.name 'Jarvis AI' && git config --global user.email 'jarvis@localhost'", cwd="/app")
        
        push_proc = await asyncio.create_subprocess_shell(
            f"git add src/jarvis/tools/{tool_name}.py && git commit -m 'feat(auto): création/mise à jour de l\'outil {tool_name}' && git push origin main",
            cwd="/app",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        p_out, p_err = await push_proc.communicate()
        
        if push_proc.returncode != 0:
            return (f"✅ L'outil {tool_name} a passé l'audit et les tests. Il est sauvegardé localement et est prêt à l'emploi !\n"
                    f"⚠️ Cependant, le Push GitHub a échoué (Vérifiez que le Personal Access Token GitHub est configuré dans le conteneur).\n"
                    f"Erreur Git: {p_err.decode()}")
            
        return f"🚀 CI/CD RÉUSSI ! L'outil {tool_name} a été audité, testé, installé et poussé sur votre dépôt GitHub avec succès."
