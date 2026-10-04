import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from jarvis.tools.base import Tool

logger = logging.getLogger(__name__)

ALLOWED_ROOTS = [
    Path("/app").resolve(),
    Path("/repo").resolve(),
    Path("/tmp").resolve(),
    Path(tempfile.gettempdir()).resolve(),
    # For local execution without docker
    Path(os.getcwd()).resolve(),
]

def _safe_path(raw: str) -> Path | None:
    if not raw or "\0" in raw:
        return None
    # Anti-traversal sec check
    if ".." in raw:
        return None
    try:
        raw_path = Path(raw)
        if not raw_path.is_absolute():
            if os.path.isdir("/repo") and (raw.startswith("src/") or raw.startswith("tests/")):
                raw_path = Path("/repo") / raw
            else:
                raw_path = Path(os.getcwd()) / raw
        resolved = raw_path.resolve()
        for root in ALLOWED_ROOTS:
            # os.path.commonpath is bulletproof
            if os.path.commonpath([str(resolved), str(root)]) == str(root):
                return resolved
        return None
    except Exception:
        return None

class FileSystemTool(Tool):
    """Opérations complètes sur les fichiers."""
    @property
    def name(self) -> str: return "manage_files"
    @property
    def description(self) -> str: return "Gestion de fichiers sécurisée."
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "properties": {
                "action": {"type": "string", "enum": ["read", "write", "append", "delete", "rm", "list", "mkdir", "stat", "move", "rename", "copy"]},
                "path": {"type": "string"},
                "content": {"type": "string"},
                "dest_path": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            "required": ["action", "path"],
            "type": "object",
        }

    async def execute(self, action: str, path: str = ".", content: str = None, dest_path: str = None, start_line: int = None, end_line: int = None, **kwargs) -> str:
        safe = _safe_path(path)
        if safe is None: return f"🚫 Chemin interdit : '{path}'"

        if action == "list":
            try:
                target = safe if safe.is_dir() else safe.parent
                if not target.exists(): return f"❌ Introuvable : {target}"
                entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name))
                lines = [f"          DIR  {e.name}/" if e.is_dir() else f"{e.stat().st_size:>10} B  {e.name}" for e in entries]
                return f"Contenu de {target} :\n" + "\n".join(lines)
            except Exception as e: return f"❌ Erreur : {e}"
        elif action == "read":
            if not safe.is_file(): return "❌ Fichier introuvable."
            text = safe.read_text(encoding="utf-8", errors="replace")
            if start_line is not None or end_line is not None:
                lines = text.splitlines()
                text = "\n".join(lines[max((start_line or 1)-1, 0):end_line or len(lines)])
            return text[:12000] + ("\n[tronqué]" if len(text)>12000 else "")
        elif action == "write":
            if content is None: return "❌ content requis."
            safe.parent.mkdir(parents=True, exist_ok=True)
            safe.write_text(content, encoding="utf-8")
            return f"✅ Fichier écrit : {safe}"
        elif action == "append":
            if content is None: return "❌ content requis."
            safe.parent.mkdir(parents=True, exist_ok=True)
            with open(safe, "a", encoding="utf-8") as f: f.write(content)
            return f"✅ Ajouté : {safe}"
        elif action in ("delete", "rm"):
            if not safe.exists(): return "❌ Introuvable."
            if safe.is_dir(): shutil.rmtree(safe)
            else: safe.unlink()
            return f"✅ Supprimé : {safe}"
        elif action == "mkdir":
            safe.mkdir(parents=True, exist_ok=True)
            return f"✅ Créé : {safe}"
        elif action == "stat":
            if not safe.exists():
                return f"❌ Le fichier ou dossier n'existe pas : {safe}"
            st = safe.stat()
            file_type = "Dossier (Dir)" if safe.is_dir() else "Fichier (File)"
            return f"Chemin: {safe}\nTaille: {st.st_size}\nType: {file_type}"
        elif action in ("move", "rename"):
            safe_dest = _safe_path(dest_path)
            if not safe_dest: return "🚫 Destination interdite."
            safe_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(safe), str(safe_dest))
            return "✅ Déplacé."
        elif action == "copy":
            safe_dest = _safe_path(dest_path)
            if not safe_dest: return "🚫 Destination interdite."
            safe_dest.parent.mkdir(parents=True, exist_ok=True)
            if safe.is_dir(): shutil.copytree(str(safe), str(safe_dest), dirs_exist_ok=True)
            else: shutil.copy2(str(safe), str(safe_dest))
            return "✅ Copié."
        return f"❌ Action inconnue : {action}"
