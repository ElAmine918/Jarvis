"""
Outil Filesystem pour Jarvis.
Gère la lecture, l'écriture, l'ajout, la suppression, le déplacement et le listage
des fichiers dans l'environnement (/app, /repo, /tmp).
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

import tempfile

ALLOWED_ROOTS = [
    Path("/app").resolve(),
    Path("/repo").resolve(),
    Path("/tmp").resolve(),
    Path(tempfile.gettempdir()).resolve(),
]


def _safe_path(raw: str) -> Path | None:
    """
    Résout le chemin et vérifie qu'il est bien sous un des répertoires de travail (/app, /repo, /tmp).
    Si le chemin est relatif, il est résolu par rapport à /app.
    """
    try:
        raw_path = Path(raw)
        if not raw_path.is_absolute():
            # Si le dossier /repo existe et le chemin commence par src, etc., tenter /repo
            if os.path.isdir("/repo") and (raw.startswith("src/") or raw.startswith("tests/")):
                raw_path = Path("/repo") / raw
            else:
                raw_path = Path("/app") / raw

        resolved = raw_path.resolve()
        for root in ALLOWED_ROOTS:
            if resolved == root or resolved.is_relative_to(root):
                return resolved
        return None
    except Exception:
        return None


class FileSystemTool(Tool):
    """Opérations complètes sur les fichiers dans /app, /repo et /tmp."""

    @property
    def name(self) -> str:
        return "manage_files"

    @property
    def description(self) -> str:
        return (
            "Permet de lire, écrire, ajouter (append), supprimer, déplacer/renommer, copier, "
            "lister et inspecter des fichiers ou dossiers dans /app, /repo et /tmp."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "read",
                        "write",
                        "append",
                        "delete",
                        "rm",
                        "list",
                        "mkdir",
                        "stat",
                        "move",
                        "rename",
                        "copy",
                    ],
                    "description": "Action sur les fichiers.",
                },
                "path": {
                    "type": "string",
                    "description": "Chemin du fichier ou dossier (ex: 'data/test.txt', '/repo/src/...').",
                },
                "content": {
                    "type": "string",
                    "description": "Contenu texte pour 'write' ou 'append'.",
                },
                "dest_path": {
                    "type": "string",
                    "description": "Chemin de destination pour 'move' ou 'copy'.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Ligne de début pour la lecture partielle (optionnel, 1-indexé).",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ligne de fin pour la lecture partielle (optionnel).",
                },
            },
            "required": ["action", "path"],
            "type": "object",
        }

    async def execute(
        self,
        action: str,
        path: str = ".",
        content: str = None,
        dest_path: str = None,
        start_line: int = None,
        end_line: int = None,
        **kwargs,
    ) -> str:
        safe = _safe_path(path)
        if safe is None:
            logger.warning(f"Chemin en dehors de l'espace autorisé: {path!r}")
            return f"🚫 Chemin interdit : '{path}' sort de l'environnement (/app, /repo, /tmp)."

        if action == "list":
            try:
                target = safe if safe.is_dir() else safe.parent
                if not target.exists():
                    return f"❌ Dossier introuvable : {target}"
                entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name))
                lines = []
                for e in entries:
                    if e.is_dir():
                        lines.append(f"          DIR  {e.name}/")
                    else:
                        size = f"{e.stat().st_size:>10} B"
                        lines.append(f"{size}  {e.name}")
                return f"Contenu de {target} :\n" + "\n".join(lines)
            except Exception as e:
                return f"❌ Erreur lors du listage : {e}"

        elif action == "read":
            if not safe.exists():
                return f"❌ Fichier introuvable : {safe}"
            if not safe.is_file():
                return f"❌ '{safe}' n'est pas un fichier (c'est un dossier)."
            try:
                text = safe.read_text(encoding="utf-8", errors="replace")
                lines_list = text.splitlines()
                if start_line is not None or end_line is not None:
                    s = max((start_line or 1) - 1, 0)
                    e = min(end_line or len(lines_list), len(lines_list))
                    lines_list = lines_list[s:e]
                    text = "\n".join(lines_list)
                if len(text) > 12000:
                    text = text[:12000] + f"\n...[tronqué, total {len(text)} caractères]"
                return text
            except Exception as e:
                return f"❌ Erreur lecture : {e}"

        elif action == "write":
            if content is None:
                return "❌ 'content' est requis pour l'action 'write'."
            try:
                safe.parent.mkdir(parents=True, exist_ok=True)
                safe.write_text(content, encoding="utf-8")
                return f"✅ Fichier écrit : {safe} ({len(content)} caractères)"
            except Exception as e:
                return f"❌ Erreur écriture : {e}"

        elif action == "append":
            if content is None:
                return "❌ 'content' est requis pour l'action 'append'."
            try:
                safe.parent.mkdir(parents=True, exist_ok=True)
                with open(safe, "a", encoding="utf-8") as f:
                    f.write(content)
                return f"✅ Contenu ajouté à : {safe} (+{len(content)} caractères)"
            except Exception as e:
                return f"❌ Erreur append : {e}"

        elif action in ("delete", "rm"):
            if not safe.exists():
                return f"❌ Cible introuvable : {safe}"
            try:
                if safe.is_dir():
                    shutil.rmtree(safe)
                    return f"✅ Dossier supprimé : {safe}"
                else:
                    safe.unlink()
                    return f"✅ Fichier supprimé : {safe}"
            except Exception as e:
                return f"❌ Erreur suppression : {e}"

        elif action == "mkdir":
            try:
                safe.mkdir(parents=True, exist_ok=True)
                return f"✅ Dossier créé : {safe}"
            except Exception as e:
                return f"❌ Erreur mkdir : {e}"

        elif action == "stat":
            if not safe.exists():
                return f"❌ Chemin introuvable : {safe}"
            try:
                st = safe.stat()
                return (
                    f"Chemin  : {safe}\n"
                    f"Type    : {'Dossier' if safe.is_dir() else 'Fichier'}\n"
                    f"Taille  : {st.st_size} octets\n"
                    f"Modifié : {st.st_mtime}"
                )
            except Exception as e:
                return f"❌ Erreur stat : {e}"

        elif action in ("move", "rename"):
            if not dest_path:
                return "❌ 'dest_path' requis pour move/rename."
            safe_dest = _safe_path(dest_path)
            if not safe_dest:
                return f"🚫 Destination interdite : '{dest_path}' sort de l'environnement."
            try:
                safe_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(safe), str(safe_dest))
                return f"✅ Déplacé avec succès : {safe} -> {safe_dest}"
            except Exception as e:
                return f"❌ Erreur move : {e}"

        elif action == "copy":
            if not dest_path:
                return "❌ 'dest_path' requis pour copy."
            safe_dest = _safe_path(dest_path)
            if not safe_dest:
                return f"🚫 Destination interdite : '{dest_path}' sort de l'environnement."
            try:
                safe_dest.parent.mkdir(parents=True, exist_ok=True)
                if safe.is_dir():
                    shutil.copytree(str(safe), str(safe_dest), dirs_exist_ok=True)
                else:
                    shutil.copy2(str(safe), str(safe_dest))
                return f"✅ Copié avec succès : {safe} -> {safe_dest}"
            except Exception as e:
                return f"❌ Erreur copy : {e}"

        return f"❌ Action inconnue : '{action}'"
