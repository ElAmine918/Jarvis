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
            ModelInfo(id="jarvis-openrouter", created=int(time.time())),
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
        async def generate_agent_stream():
            try:
                full_response = ""
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                
                async for chunk_text in agent.process_message(messages_dicts, body.model):
                    full_response += chunk_text
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": body.model,
                        "choices": [{"index": 0, "delta": {"role": "assistant", "content": chunk_text}, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                from .logger_db import log_conversation
                last_user_msg = next((m["content"] for m in reversed(messages_dicts) if m["role"] == "user"), "")
                log_conversation("open-webui", "local", last_user_msg, full_response, agent.last_backend_used)
                
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
        response_text = ""
        async for chunk_text in agent.process_message(messages_dicts, body.model):
            response_text += chunk_text
            
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
