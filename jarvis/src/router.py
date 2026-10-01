import httpx
import logging
from openai import AsyncOpenAI
from .config import (
    LM_STUDIO_URL, LM_STUDIO_MODEL, LM_STUDIO_HEALTH_TIMEOUT,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
    GEMINI_BASE_URL, GEMINI_API_KEY, GEMINI_MODEL,
    OLLAMA_LOCAL_URL, OLLAMA_LOCAL_MODEL
)

logger = logging.getLogger(__name__)

async def check_endpoint(url: str, timeout: float = 3.5) -> bool:
    try:
        check_url = url
        if check_url.endswith("/chat/completions"):
            check_url = check_url.replace("/chat/completions", "/models")
        elif check_url.endswith("/v1") or check_url.endswith("/v1/"):
            check_url = check_url.rstrip("/") + "/models"
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(check_url, timeout=timeout)
            return resp.status_code == 200
    except Exception:
        return False

import time

_gemini_models_cache = []
_gemini_models_cache_time = 0

async def get_dynamic_gemini_models(api_key: str, primary_model: str) -> list:
    global _gemini_models_cache, _gemini_models_cache_time
    
    # Utilisation du cache (valide 1 heure) pour ne pas spammer l'API
    if _gemini_models_cache and (time.time() - _gemini_models_cache_time) < 3600:
        models = _gemini_models_cache
    else:
        try:
            async with httpx.AsyncClient() as client:
                # Endpoint natif Google API pour lister les modèles (documentation Gemini API)
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                res = await client.get(url, timeout=3.0)
                if res.status_code == 200:
                    data = res.json()
                    models = []
                    for m in data.get("models", []):
                        name = m.get("name", "").replace("models/", "")
                        # On filtre pour ne garder que les modèles de génération de texte "Flash" ou "Pro"
                        # et on exclut explicitement les modèles spécialisés image/audio/lite pour éviter les erreurs.
                        name_lower = name.lower()
                        if "generateContent" in m.get("supportedGenerationMethods", []):
                            if ("flash" in name_lower or "pro" in name_lower) and \
                               "image" not in name_lower and \
                               "tts" not in name_lower and \
                               "lite" not in name_lower:
                                models.append(name)
                    _gemini_models_cache = models
                    _gemini_models_cache_time = time.time()
                else:
                    models = []
        except Exception as e:
            logger.warning(f"Impossible de récupérer dynamiquement les modèles Gemini : {e}")
            models = []
            
    # Fallback robuste en cas d'échec de l'API
    if not models:
        models = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        
    # S'assurer que le modèle principal choisi dans le .env est toujours en premier
    final_models = [primary_model]
    for m in models:
        if m not in final_models:
            final_models.append(m)
            
    return final_models

_dead_models = {}

def mark_model_dead(model_name: str, duration_seconds: int = 86400):
    """Marque un modèle comme 'mort' (ex: Quota 429 atteint) pour l'exclure pendant X secondes."""
    _dead_models[model_name] = time.time() + duration_seconds
    logger.info(f"Circuit Breaker: Le modèle {model_name} est désactivé pour {duration_seconds}s.")

async def get_all_backends() -> list:
    backends = []
    current_time = time.time()
    
    # 1. Priorité absolue : Cloud Performant (Gemini Flash Cascade Dynamique)
    if GEMINI_API_KEY:
        gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY)
        gemini_models = await get_dynamic_gemini_models(GEMINI_API_KEY, GEMINI_MODEL)
        
        for m in gemini_models:
            # Vérifier le Circuit Breaker
            if m in _dead_models and current_time < _dead_models[m]:
                continue
            backends.append((f"Gemini ({m})", gemini_client, m))
        
    # 2. Fallback Cloud : OpenRouter (Qwen 3.8 27B, etc.)
    if OPENROUTER_API_KEY:
        backends.append(("OpenRouter (Cloud)", AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY), OPENROUTER_MODEL))

    # 3. Fallback Local Hautes Performances : LM Studio (Mac M4)
    if await check_endpoint(LM_STUDIO_URL, 4.0):
        backends.append(("LM Studio (Mac)", AsyncOpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio"), LM_STUDIO_MODEL))
        
    # 4. Survie locale absolue : Ollama (Toshiba)
    if await check_endpoint(OLLAMA_LOCAL_URL, 2.0):
        # Vérifie quel modèle est réellement dispo dans Ollama
        chosen_model = OLLAMA_LOCAL_MODEL
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(OLLAMA_LOCAL_URL.rstrip("/") + "/models", timeout=1.5)
                if res.status_code == 200:
                    models_data = [m["id"] for m in res.json().get("data", [])]
                    if OLLAMA_LOCAL_MODEL not in models_data:
                        # Fallback automatique sur le premier modèle valide
                        for preferred in ["qwen2.5:7b", "llama3.2:1b", "qwen2.5:1.5b", "gemma2:2b"]:
                            if preferred in models_data:
                                chosen_model = preferred
                                break
                        else:
                            if models_data:
                                chosen_model = models_data[0]
        except Exception:
            pass

        backends.append(("Ollama (Toshiba SLM)", AsyncOpenAI(base_url=OLLAMA_LOCAL_URL, api_key="ollama"), chosen_model))
        
    return backends
