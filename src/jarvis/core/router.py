import logging
import time

import httpx
from openai import AsyncOpenAI

from jarvis.core.config import (
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    LM_STUDIO_MODEL,
    LM_STUDIO_URL,
    OLLAMA_LOCAL_MODEL,
    OLLAMA_LOCAL_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)

logger = logging.getLogger(__name__)


# --- Registre d'Intelligence ---
# Note: Ces scores sont indicatifs (basés sur ELO Chatbot Arena)
def get_model_stats(model_name: str) -> dict:
    name_lower = model_name.lower()
    stats = {"score": 50, "speed": "medium"}  # Défaut

    # Gemini
    if "gemini" in name_lower:
        if "pro" in name_lower:
            stats = {"score": 92, "speed": "slow"}
        elif "flash" in name_lower:
            stats = {"score": 88, "speed": "fast"}
    # LLaMA (Groq / Local)
    elif "llama" in name_lower or "llama3" in name_lower:
        if "70b" in name_lower or "405b" in name_lower:
            stats = {"score": 90, "speed": "fast"}
        else:
            stats = {"score": 75, "speed": "fast"}
    # Mixtral (Groq / Local)
    elif "mixtral" in name_lower:
        stats = {"score": 85, "speed": "fast"}
    # Qwen
    # Qwen
    elif "qwen" in name_lower:
        if (
            "72b" in name_lower
            or "235b" in name_lower
            or "max" in name_lower
            or "plus" in name_lower
        ):
            stats = {"score": 88, "speed": "medium"}
        elif "27b" in name_lower or "32b" in name_lower or "14b" in name_lower:
            stats = {"score": 80, "speed": "fast"}
        else:
            stats = {"score": 60, "speed": "fast"}
    # Llama
    elif "llama" in name_lower:
        if "405b" in name_lower:
            stats = {"score": 90, "speed": "medium"}
        elif "70b" in name_lower:
            stats = {"score": 85, "speed": "fast"}
        else:
            stats = {"score": 75, "speed": "fast"}
    # Claude/Mistral via OpenRouter (au cas où)
    elif "claude-3.5" in name_lower:
        stats = {"score": 95, "speed": "medium"}
    elif "mistral-large" in name_lower:
        stats = {"score": 85, "speed": "medium"}

    return stats


# --- Circuit Breaker Gradué ---
_dead_models = {}


def mark_model_dead(model_name: str, error_str: str):
    error_lower = error_str.lower()
    cooldown = 300  # Défaut: 5 minutes

    if "404" in error_lower:
        cooldown = 315360000  # 10 ans (Modèle supprimé)
        logger.info(f"Circuit Breaker: {model_name} banni (404 Not Found).")
    elif "429" in error_lower:
        if "day" in error_lower or "quota" in error_lower:
            cooldown = 86400  # 24h
            logger.info(
                f"Circuit Breaker: {model_name} banni pour 24h (Quota Journalier Atteint)."
            )
        elif "upstream" in error_lower or "provider" in error_lower:
            cooldown = 300  # 5m
            logger.info(
                f"Circuit Breaker: {model_name} banni pour 5m (Serveur Upstream Congestionné)."
            )
        else:
            cooldown = 60  # 1m
            logger.info(f"Circuit Breaker: {model_name} banni pour 1m (Rate Limit).")
    elif "503" in error_lower or "502" in error_lower:
        cooldown = 900  # 15m
        logger.info(
            f"Circuit Breaker: {model_name} banni pour 15m (Surcharge Serveur)."
        )
    else:
        logger.info(f"Circuit Breaker: {model_name} banni pour 5m (Erreur indéfinie).")

    _dead_models[model_name] = time.time() + cooldown


# --- Dispatcher de Complexité ---
def analyze_complexity(history: list) -> dict:
    if not history:
        return {"level": "SIMPLE", "threshold": 50}

    last_user_msg = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )

    complex_keywords = [
        "analyse",
        "code",
        "rapport",
        "explique",
        "compare",
        "système",
        "architecture",
        "script",
        "développe",
    ]

    # Très court, pas de mots clés -> TRIVIAL
    if len(last_user_msg) < 30 and not any(
        k in last_user_msg.lower() for k in complex_keywords
    ):
        return {"level": "TRIVIAL", "threshold": 40}

    # Moyen, ou contient au moins un mot clé -> COMPLEXE
    if len(last_user_msg) > 300 or any(
        k in last_user_msg.lower() for k in complex_keywords
    ):
        return {"level": "COMPLEXE", "threshold": 85}

    return {"level": "SIMPLE", "threshold": 70}


# --- Découverte Dynamique ---
_gemini_models_cache = []
_gemini_models_cache_time = 0


async def get_dynamic_gemini_models(api_key: str, primary_model: str) -> list:
    # Explicit list of text-out models from user dashboard (excluding lite)
    models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.1-pro",
        "gemini-3.0-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    
    final_models = [primary_model] if primary_model and primary_model not in models else []
    for m in models:
        final_models.append(m)
        
    return final_models


_openrouter_models_cache = []
_openrouter_models_cache_time = 0


_groq_models_cache = []
_groq_models_cache_time = 0

async def get_dynamic_groq_models(api_key: str, primary_model: str) -> list:
    global _groq_models_cache, _groq_models_cache_time
    import time
    if _groq_models_cache and (time.time() - _groq_models_cache_time) < 3600:
        models = _groq_models_cache
    else:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=4.0
                )
                if res.status_code == 200:
                    models = []
                    for m in res.json().get("data", []):
                        name = m.get("id", "")
                        # Filter out whisper (audio) and pure safeguard models
                        if "whisper" not in name and "safeguard" not in name and "guard" not in name:
                            models.append(name)
                    _groq_models_cache = models
                    _groq_models_cache_time = time.time()
                else:
                    models = []
        except Exception:
            models = []

    final_models = [primary_model] if primary_model else []
    for m in models:
        if m not in final_models:
            final_models.append(m)
    return final_models

async def get_dynamic_openrouter_models(api_key: str, primary_model: str) -> list:
    global _openrouter_models_cache, _openrouter_models_cache_time
    if (
        _openrouter_models_cache
        and (time.time() - _openrouter_models_cache_time) < 3600
    ):
        models = _openrouter_models_cache
    else:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://openrouter.ai/api/v1/models", timeout=4.0
                )
                if res.status_code == 200:
                    models = []
                    for m in res.json().get("data", []):
                        # Garder uniquement les modèles gratuits
                        if (
                            m.get("id", "").endswith(":free")
                            or m.get("pricing", {}).get("prompt", "") == "0"
                        ):
                            models.append(m["id"])
                    _openrouter_models_cache = models
                    _openrouter_models_cache_time = time.time()
                else:
                    models = []
        except Exception:
            models = []

    final_models = [primary_model] if primary_model else []
    for m in models:
        if m not in final_models:
            final_models.append(m)
    return final_models


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


# --- Routeur Principal ---
async def get_all_backends(history: list = None) -> list:
    available_pool = []
    current_time = time.time()

    complexity = analyze_complexity(history)
    req_score = complexity["threshold"]
    logger.info(
        f"Neural Router: Complexité {complexity['level']} (Score cible: {req_score})"
    )

    # 1. Collecter Gemini
    if GEMINI_API_KEY:
        gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY)
        gemini_models = await get_dynamic_gemini_models(GEMINI_API_KEY, GEMINI_MODEL)
        for m in gemini_models:
            if m in _dead_models and current_time < _dead_models[m]:
                continue
            stats = get_model_stats(m)
            available_pool.append(
                {
                    "name": f"Gemini ({m})",
                    "client": gemini_client,
                    "model": m,
                    "score": stats["score"],
                    "speed": stats["speed"],
                    "tier": 2,
                }
            )

# 2.a. Collecter Groq
    from jarvis.core.config import GROQ_API_KEY
    if GROQ_API_KEY:
        groq_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY
        )
        groq_models = await get_dynamic_groq_models(GROQ_API_KEY, "")
        for m in groq_models:
            if m in _dead_models and current_time < _dead_models[m]:
                continue
            stats = get_model_stats(m)
            # Groq is incredibly fast, so speed is 'fast' and tier is 1.5
            available_pool.append(
                {
                    "name": f"Groq ({m})",
                    "client": groq_client,
                    "model": m,
                    "score": stats["score"],
                    "speed": "fast",
                    "tier": 1.5,
                }
            )

    # 2.b. Collecter OpenRouter
    if OPENROUTER_API_KEY:
        or_client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY
        )
        or_models = await get_dynamic_openrouter_models(
            OPENROUTER_API_KEY, OPENROUTER_MODEL
        )
        for m in or_models:
            if m in _dead_models and current_time < _dead_models[m]:
                continue
            stats = get_model_stats(m)
            available_pool.append(
                {
                    "name": f"OpenRouter ({m})",
                    "client": or_client,
                    "model": m,
                    "score": stats["score"],
                    "speed": stats["speed"],
                    "tier": 1,
                }
            )

    # 3. Collecter LM Studio
    if await check_endpoint(LM_STUDIO_URL, 4.0):
        if (
            LM_STUDIO_MODEL not in _dead_models
            or current_time > _dead_models[LM_STUDIO_MODEL]
        ):
            stats = get_model_stats(LM_STUDIO_MODEL)
            available_pool.append(
                {
                    "name": "LM Studio (Mac)",
                    "client": AsyncOpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio"),
                    "model": LM_STUDIO_MODEL,
                    "score": stats["score"],
                    "speed": stats["speed"],
                    "tier": 3,
                }
            )

    # 4. Collecter Ollama (Survie absolue)
    if await check_endpoint(OLLAMA_LOCAL_URL, 2.0):
        chosen_model = OLLAMA_LOCAL_MODEL
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    OLLAMA_LOCAL_URL.rstrip("/") + "/models", timeout=1.5
                )
                if res.status_code == 200:
                    models_data = [m["id"] for m in res.json().get("data", [])]
                    if chosen_model not in models_data and models_data:
                        chosen_model = models_data[0]
        except Exception:
            pass

        if (
            chosen_model not in _dead_models
            or current_time > _dead_models[chosen_model]
        ):
            stats = get_model_stats(chosen_model)
            available_pool.append(
                {
                    "name": f"Ollama ({chosen_model})",
                    "client": AsyncOpenAI(base_url=OLLAMA_LOCAL_URL, api_key="ollama"),
                    "model": chosen_model,
                    "score": stats["score"],
                    "speed": "slow",
                    "tier": 4,
                }
            )

    if not available_pool:
        return []

    # Filtrer le pool par le score requis (on garde quand même ceux du même Tier si on n'a rien d'autre)
    # Pas de filtrage agressif. On trie simplement tout le pool.
    # Les modèles "faibles" (Ollama) seront en dernier recours.
    qualified_pool = available_pool

    # Tri du pool
    def sort_key(b):
        # 1. Tier (Gemini > OR > Mac > Ollama)
        # 2. Si Trivial -> Favoriser Speed ("fast" > "medium" > "slow")
        # 3. Si Complexe -> Favoriser Score
        speed_val = {"fast": 0, "medium": 1, "slow": 2}.get(b["speed"], 1)
        if complexity["level"] == "TRIVIAL":
            return (b["tier"], speed_val, -b["score"])
        elif complexity["level"] == "COMPLEXE":
            return (b["tier"], -b["score"], speed_val)
        else:
            return (b["tier"], -b["score"], speed_val)

    qualified_pool.sort(key=sort_key)

    # Convertir au format attendu par agent.py : [(nom, client, modèle)]
    return [(b["name"], b["client"], b["model"]) for b in qualified_pool]
