import os
import sys
from typing import List

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# H-08 : Pas de mot de passe par défaut — forcer la configuration explicite
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    # Log un warning sévère mais ne bloque pas le démarrage (compatibilité)
    import logging as _logging
    _logging.getLogger(__name__).critical(
        "ADMIN_PASSWORD non défini dans .env — le dashboard admin est DÉSACTIVÉ. "
        "Définissez ADMIN_PASSWORD dans votre .env pour accéder au dashboard."
    )
ALLOWED_TELEGRAM_USER_IDS: List[int] = [
    int(uid.strip()) for uid in os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").split(",") if uid.strip()
]

# --- Proxmox ---
PROXMOX_HOST = os.getenv("PROXMOX_HOST", "192.168.2.100")
PROXMOX_USER = os.getenv("PROXMOX_USER", "root@pam")
PROXMOX_TOKEN_NAME = os.getenv("PROXMOX_TOKEN_NAME", "jarvis")
PROXMOX_TOKEN_VALUE = os.getenv("PROXMOX_TOKEN_VALUE", "")

# --- LM Studio (local, sur le Mac via Tailscale) ---
# URL de l'API OpenAI-compatible de LM Studio
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://100.x.x.x:1234/v1")
# Modèle à utiliser dans LM Studio (ex: "qwen2.5-14b-instruct")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")
# Timeout pour le health check (en secondes) — court pour ne pas bloquer
LM_STUDIO_HEALTH_TIMEOUT = float(os.getenv("LM_STUDIO_HEALTH_TIMEOUT", "2.0"))

# --- OpenRouter (Cloud gratuit & multi-fournisseurs) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free")

# --- Gemini (free tier, fallback quand Mac est éteint) ---
# Clé API Google AI Studio (gratuit) : https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Chemins des données (pour Docker) ---
SKILLS_DIR = os.getenv("SKILLS_DIR", "/app/data/skills")
MEMORY_DB_PATH = os.getenv("MEMORY_DB_PATH", "/app/data/memory.db")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/app/workspace")

# --- Serveur API interne (pour Open WebUI) ---
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# --- Ollama Survie (Local Toshiba) ---
OLLAMA_LOCAL_URL = os.getenv("OLLAMA_LOCAL_URL", "http://ollama:11434/v1")
OLLAMA_LOCAL_MODEL = os.getenv("OLLAMA_LOCAL_MODEL", "qwen2.5:7b")

# --- Voice (STT/TTS) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
VOICE_TTS_ENABLED = os.getenv("VOICE_TTS_ENABLED", "true").lower() == "true"
# --- Local Voice ---
LOCAL_STT_URL = os.getenv("LOCAL_STT_URL", "")
LOCAL_TTS_URL = os.getenv("LOCAL_TTS_URL", "")
