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

async def get_all_backends() -> list:
    backends = []
    
    # 1. Priorité absolue : LM Studio (Mac M4)
    if await check_endpoint(LM_STUDIO_URL, 4.0):
        backends.append(("LM Studio (Mac)", AsyncOpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio"), LM_STUDIO_MODEL))
        
    # 2. Cloud Gratuit : OpenRouter (Qwen 3.8 27B)
    if OPENROUTER_API_KEY:
        backends.append(("OpenRouter (Cloud)", AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY), OPENROUTER_MODEL))

    # 3. Cloud Fallback : Gemini Flash
    if GEMINI_API_KEY:
        backends.append(("Gemini Flash (Cloud)", AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY), GEMINI_MODEL))
        
    # 4. Survie locale : Ollama (Toshiba)
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
