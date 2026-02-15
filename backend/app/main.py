import asyncio
import json
import logging
import os
from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import CORS_ORIGINS_LIST, DEFAULT_MODEL, DEFAULT_TEMPERATURE
from .models import (
    CreateConversationRequest,
    SendMessageRequest,
    UpdateConversationRequest,
)
from .llm import call_llm, stream_llm, get_available_models, LLMError
from . import storage

logger = logging.getLogger(__name__)

app = FastAPI(title="XQT5 AI Plattform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Cache-Control", "Connection"],
)


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "xqt5-ai-plattform-backend"}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "healthy", "env": os.getenv("ENVIRONMENT", "development")}


@app.get("/api/models")
async def list_models() -> list:
    return get_available_models()


@app.get("/api/conversations")
async def list_conversations() -> list:
    return storage.list_conversations()


@app.post("/api/conversations")
async def create_conversation(request: CreateConversationRequest) -> dict:
    return storage.create_conversation(
        title=request.title or "New Conversation",
        model=request.model,
        temperature=request.temperature,
    )


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, request: UpdateConversationRequest) -> dict:
    updates = request.model_dump(exclude_none=True)
    if not updates:
        conversation = storage.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    result = storage.update_conversation(conversation_id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


def _build_llm_messages(conversation_messages: List[Dict]) -> List[Dict[str, str]]:
    """Convert stored messages to LLM-compatible format."""
    llm_messages = []
    for msg in conversation_messages:
        llm_messages.append({
            "role": msg["role"],
            "content": msg.get("content", ""),
        })
    return llm_messages


async def _auto_name_conversation(conversation_id: str, user_message: str) -> None:
    """Generate a short title for the conversation using the LLM."""
    try:
        messages = [
            {
                "role": "user",
                "content": (
                    f"Generate a very short title (max 6 words) for a conversation that starts with this message. "
                    f"Reply with ONLY the title, no quotes, no punctuation at the end.\n\n"
                    f"Message: {user_message[:500]}"
                ),
            }
        ]
        result = await call_llm(messages, DEFAULT_MODEL, temperature=0.3)
        title = result["content"].strip().strip('"').strip("'")[:100]
        if title:
            storage.update_conversation(conversation_id, title=title)
    except Exception as e:
        logger.warning(f"Auto-naming failed for {conversation_id}: {e}")


@app.post("/api/conversations/{conversation_id}/message", response_model=None)
async def send_message(conversation_id: str, request: SendMessageRequest):
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Determine model and temperature: message-level > conversation-level > default
    model = request.model or conversation.get("model") or DEFAULT_MODEL
    temperature = request.temperature if request.temperature is not None else (
        conversation.get("temperature") if conversation.get("temperature") is not None else DEFAULT_TEMPERATURE
    )

    # Store user message
    storage.add_user_message(conversation_id, request.content)

    # Check if this is the first user message (for auto-naming)
    is_first_message = all(m["role"] != "user" for m in conversation.get("messages", []))

    # Build LLM message history
    llm_messages = _build_llm_messages(conversation.get("messages", []))
    llm_messages.append({"role": "user", "content": request.content})

    if request.stream:
        return StreamingResponse(
            _stream_response(conversation_id, llm_messages, model, temperature, is_first_message, request.content),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming response
    try:
        result = await call_llm(llm_messages, model, temperature)
        assistant_content = result["content"]
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    storage.add_assistant_message(conversation_id, assistant_content, model=model)

    # Auto-name in background
    if is_first_message:
        asyncio.create_task(_auto_name_conversation(conversation_id, request.content))

    updated = storage.get_conversation(conversation_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to load updated conversation")
    return updated


async def _stream_response(
    conversation_id: str,
    llm_messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    is_first_message: bool,
    user_content: str,
):
    full_content = ""
    try:
        async for delta in stream_llm(llm_messages, model, temperature):
            full_content += delta
            yield f"data: {json.dumps({'delta': delta})}\n\n"

        # Store the complete assistant message
        storage.add_assistant_message(conversation_id, full_content, model=model)

        yield f"data: {json.dumps({'done': True, 'content': full_content})}\n\n"

        # Auto-name in background after stream completes
        if is_first_message:
            asyncio.create_task(_auto_name_conversation(conversation_id, user_content))

    except LLMError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'error': 'An unexpected error occurred'})}\n\n"
