import httpx
import logging
from openai import AsyncOpenAI
from .config import (
    LM_STUDIO_URL, LM_STUDIO_MODEL, LM_STUDIO_HEALTH_TIMEOUT,
    GEMINI_BASE_URL, GEMINI_API_KEY, GEMINI_MODEL,
    OLLAMA_LOCAL_URL, OLLAMA_LOCAL_MODEL
)

logger = logging.getLogger(__name__)

async def check_endpoint(url: str, timeout: float = 2.0) -> bool:
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
    
    if await check_endpoint(LM_STUDIO_URL, LM_STUDIO_HEALTH_TIMEOUT):
        backends.append(("LM Studio (Mac)", AsyncOpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio"), LM_STUDIO_MODEL))
        
    if GEMINI_API_KEY:
        backends.append(("Gemini Flash (Cloud)", AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY), GEMINI_MODEL))
        
    if await check_endpoint(OLLAMA_LOCAL_URL, 2.0):
        backends.append(("Ollama (Toshiba SLM)", AsyncOpenAI(base_url=OLLAMA_LOCAL_URL, api_key="ollama"), OLLAMA_LOCAL_MODEL))
        
    return backends
