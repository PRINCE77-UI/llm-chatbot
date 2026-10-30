from __future__ import annotations

import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config, llm
from .conversation import Conversation

app = FastAPI(title="Byte - programming mentor chatbot")

# In-memory store: fine for a single-process demo. Swap for Redis/DB to scale out.
_conversations: dict[str, Conversation] = {}
_lock = threading.Lock()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=config.MAX_USER_CHARS)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    history_trimmed: bool


class ResetRequest(BaseModel):
    conversation_id: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    text = req.message.strip()
    if not text:
        raise HTTPException(400, "Type a message first.")

    with _lock:
        cid = req.conversation_id if req.conversation_id in _conversations else uuid.uuid4().hex
        conv = _conversations.setdefault(cid, Conversation())

    try:
        reply, trimmed = conv.send(text, llm.generate, llm.summarize)
    except llm.LLMError as e:
        raise HTTPException(e.status, e.user_message)
    except Exception:
        raise HTTPException(500, "Something went wrong on the server. Please try again.")
    return ChatResponse(conversation_id=cid, reply=reply, history_trimmed=trimmed)


@app.post("/reset")
def reset(req: ResetRequest):
    with _lock:
        _conversations.pop(req.conversation_id, None)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
