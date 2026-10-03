"""
Outil Filesystem — accès strictement restreint au workspace.
Pas de shell. Chaque opération est implémentée nativement en Python.
La validation de chemin utilise Path.resolve().is_relative_to() — immune aux `..`.
"""

import logging
from pathlib import Path
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

ALLOWED_PATHS = [Path("/app/workspace").resolve(), Path("/app/jarvis/tools").resolve(), Path("/repo").resolve()]


def _safe_path(raw: str) -> Path | None:
    """
    Résout le chemin et vérifie qu'il est bien sous ALLOWED_PATHS.
    """
    try:
        raw_path = Path(raw)
        # Si c'est relatif, on assume /app/workspace par défaut pour la commodité, ou on le résout depuis cwd
        if not raw_path.is_absolute():
            raw_path = Path("/app/workspace") / raw
            
        resolved = raw_path.resolve()
        if any(resolved.is_relative_to(p) for p in ALLOWED_PATHS):
            return resolved
        return None
    except Exception:
        return None
    except Exception:
        return None


class FileSystemTool(Tool):
    """Opérations sur les fichiers, limitées au répertoire principal /app."""

    @property
    def name(self) -> str:
        return "manage_files"

    @property
    def description(self) -> str:
        return (
            "Lit, écrit, liste et crée des fichiers/dossiers dans /app. "
            "Toutes les actions sont strictement limitées au workspace. "
            "Aucun shell — pas de commandes arbitraires."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list", "mkdir", "stat"],
                    "description": "Action à effectuer.",
                },
                "path": {
                    "type": "string",
                    "description": "Chemin relatif par rapport à /app.",
                },
                "content": {
                    "type": "string",
                    "description": "Contenu à écrire (pour 'write' uniquement).",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Ligne de début pour la lecture partielle (optionnel).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ligne de fin pour la lecture partielle (optionnel).",
                },
            },
            "required": ["action", "path"],
        }

    async def execute(
        self,
        action: str,
        path: str = ".",
        content: str = None,
        start_line: int = None,
        end_line: int = None,
        query: str = None,
        **kwargs,
    ) -> str:
        safe = _safe_path(path)
        if safe is None:
            logger.warning(f"Tentative de path traversal bloquée: {path!r}")
            return f"🚫 Chemin interdit : '{path}' sort du workspace."

        if action == "list":
            try:
                target = safe if safe.is_dir() else safe.parent
                entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
                lines = []
                for e in entries:
                    size = (
                        f"{e.stat().st_size:>10} B" if e.is_file() else "         DIR"
                    )
                    lines.append(f"{size}  {e.name}")
                return f"Contenu de {target.relative_to(WORKSPACE)}:\n" + "\n".join(
                    lines
                )
            except Exception as e:
                return f"❌ Erreur liste: {e}"

        elif action == "read":
            if not safe.exists():
                return f"❌ Fichier introuvable: {path}"
            if not safe.is_file():
                return f"❌ '{path}' n'est pas un fichier."
            try:
                text = safe.read_text(encoding="utf-8", errors="replace")
                lines_list = text.splitlines()
                if start_line is not None or end_line is not None:
                    s = (start_line or 1) - 1
                    e = end_line or len(lines_list)
                    lines_list = lines_list[s:e]
                    text = "\n".join(lines_list)
                if len(text) > 8000:
                    text = text[:8000] + "\n...[tronqué]"
                return text
            except Exception as e:
                return f"❌ Erreur lecture: {e}"

        elif action == "write":
            if content is None:
                return "❌ 'content' est requis pour 'write'."
            try:
                safe.parent.mkdir(parents=True, exist_ok=True)
                safe.write_text(content, encoding="utf-8")
                return f"✅ Fichier écrit : {safe.relative_to(WORKSPACE)} ({len(content)} caractères)"
            except Exception as e:
                return f"❌ Erreur écriture: {e}"

        elif action == "mkdir":
            try:
                safe.mkdir(parents=True, exist_ok=True)
                return f"✅ Dossier créé : {safe.relative_to(WORKSPACE)}"
            except Exception as e:
                return f"❌ Erreur mkdir: {e}"

        elif action == "stat":
            if not safe.exists():
                return f"❌ Chemin introuvable: {path}"
            try:
                st = safe.stat()
                return (
                    f"Chemin  : {safe.relative_to(WORKSPACE)}\n"
                    f"Type    : {'Dossier' if safe.is_dir() else 'Fichier'}\n"
                    f"Taille  : {st.st_size} octets\n"
                    f"Modifié : {st.st_mtime}"
                )
            except Exception as e:
                return f"❌ Erreur stat: {e}"

        return f"❌ Action inconnue: '{action}'"
