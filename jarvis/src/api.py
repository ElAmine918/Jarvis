import time
import uuid
import logging
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from .admin_ui import admin_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Jarvis API", version="1.0.0")

app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "jarvis-auto"
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "jarvis"

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            ModelInfo(id="jarvis-auto", created=int(time.time())),
            ModelInfo(id="jarvis-gemini", created=int(time.time())),
            ModelInfo(id="jarvis-ollama", created=int(time.time())),
            ModelInfo(id="jarvis-mac", created=int(time.time()))
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    agent = app.state.agent

    if not body.messages:
        raise HTTPException(status_code=400, detail="messages est vide")

    messages_dicts = [{"role": msg.role, "content": msg.content} for msg in body.messages]

    if body.stream:
        # Seul Ollama fait du vrai streaming mot à mot (car il n'a pas accès aux outils d'exécution)
        if body.model == "jarvis-ollama":
            async def generate_true_stream():
                try:
                    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                    async for content in agent.process_message_stream(messages_dicts, body.model):
                        chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": body.model,
                            "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        
                    end_chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": body.model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                    }
                    yield f"data: {json.dumps(end_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"Erreur agent: {e}")
                    err = {"error": str(e)}
                    yield f"data: {json.dumps(err)}\n\n"
                    yield "data: [DONE]\n\n"
            return StreamingResponse(generate_true_stream(), media_type="text/event-stream")
        
        # Pour les vrais agents (Mac, Gemini, Auto) : on exécute d'abord les outils, puis on streame le résultat complet
        else:
            async def generate_agent_stream():
                try:
                    response_text = await agent.process_message(messages_dicts, body.model)
                    from .logger_db import log_conversation
                    last_user_msg = next((m["content"] for m in reversed(messages_dicts) if m["role"] == "user"), "")
                    log_conversation("open-webui", "local", last_user_msg, response_text, agent.last_backend_used)
                    
                    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": body.model,
                        "choices": [{"index": 0, "delta": {"role": "assistant", "content": response_text}, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    
                    end_chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": body.model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                    }
                    yield f"data: {json.dumps(end_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"Erreur agent: {e}")
                    err = {"error": str(e)}
                    yield f"data: {json.dumps(err)}\n\n"
                    yield "data: [DONE]\n\n"
            return StreamingResponse(generate_agent_stream(), media_type="text/event-stream")

    try:
        response_text = await agent.process_message(messages_dicts, body.model)
        from .logger_db import log_conversation
        last_user_msg = next((m["content"] for m in reversed(messages_dicts) if m["role"] == "user"), "")
        log_conversation("open-webui", "local", last_user_msg, response_text, agent.last_backend_used)
    except Exception as e:
        logger.error(f"Erreur agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        ]
    )
