import json
import logging
import os
import secrets
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from jarvis.interfaces.cli_admin import admin_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Jarvis API", version="1.0.0")

app.include_router(admin_router)

# --- CORS : restreindre aux origines internes connues (M-05) ---
_CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
if not _CORS_ORIGINS:
    # Fallback : uniquement le réseau interne Docker (open-webui → jarvis)
    _CORS_ORIGINS = [
        "http://open-webui:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Authentification API (C-02) ---
_API_KEY = os.getenv("JARVIS_API_KEY", "")
_bearer_scheme = HTTPBearer(auto_error=False)


async def _verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """Vérifie la clé API Bearer sur tous les endpoints /v1/*."""
    if not _API_KEY:
        return  # Mode développement : on passe sans clé

    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), _API_KEY.encode()
    ):
        logger.warning(
            f"Tentative d'accès API non-autorisée depuis {request.client.host}"
        )
        raise HTTPException(status_code=401, detail="Clé API invalide ou manquante.")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "jarvis-auto"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = 0.7
    max_tokens: int | None = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "jarvis"


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/v1/models", dependencies=[Depends(_verify_api_key)])
async def list_models():
    return {
        "object": "list",
        "data": [
            ModelInfo(id="jarvis-auto", created=int(time.time())),
            ModelInfo(id="jarvis-openrouter", created=int(time.time())),
            ModelInfo(id="jarvis-gemini", created=int(time.time())),
            ModelInfo(id="jarvis-ollama", created=int(time.time())),
            ModelInfo(id="jarvis-mac", created=int(time.time())),
        ],
    }


@app.post("/v1/chat/completions", dependencies=[Depends(_verify_api_key)])
async def chat_completions(request: Request, body: ChatCompletionRequest):
    agent = app.state.agent

    if not body.messages:
        raise HTTPException(status_code=400, detail="messages est vide")

    messages_dicts = [
        {"role": msg.role, "content": msg.content} for msg in body.messages
    ]

    if body.stream:

        async def generate_agent_stream():
            try:
                full_response = ""
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

                async for chunk_text in agent.process_message(
                    messages_dicts, body.model
                ):
                    full_response += chunk_text
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": body.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"role": "assistant", "content": chunk_text},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                from jarvis.storage.logger_db import log_conversation

                last_user_msg = next(
                    (
                        m["content"]
                        for m in reversed(messages_dicts)
                        if m["role"] == "user"
                    ),
                    "",
                )
                # H-12 : correction signature — session_id ajouté (6 args)
                log_conversation(
                    "open-webui",
                    "open-webui",
                    "api",
                    last_user_msg,
                    full_response,
                    agent.last_backend_used,
                )

                end_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": body.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(end_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Erreur agent stream: {e}", exc_info=True)
                # M-03 : masquer les détails d'erreur dans le stream SSE
                err = {
                    "error": {
                        "message": "Erreur interne du serveur.",
                        "type": "server_error",
                    }
                }
                yield f"data: {json.dumps(err)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_agent_stream(), media_type="text/event-stream"
        )

    try:
        response_text = ""
        async for chunk_text in agent.process_message(messages_dicts, body.model):
            response_text += chunk_text

        from jarvis.storage.logger_db import log_conversation

        last_user_msg = next(
            (m["content"] for m in reversed(messages_dicts) if m["role"] == "user"), ""
        )
        # H-12 : correction signature — session_id ajouté (6 args)
        log_conversation(
            "open-webui",
            "open-webui",
            "api",
            last_user_msg,
            response_text,
            agent.last_backend_used,
        )
    except Exception as e:
        logger.error(f"Erreur agent: {e}", exc_info=True)
        # M-02 : ne pas exposer les détails d'erreur internes
        raise HTTPException(status_code=500, detail="Erreur interne du serveur.")

    return ChatCompletionResponse(
        id=f"jarvis-{uuid.uuid4().hex[:8]}",
        created=int(time.time()),
        model=body.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop",
            )
        ],
    )
