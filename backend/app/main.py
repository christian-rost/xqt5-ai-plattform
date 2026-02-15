import asyncio
import json
import logging
import os
from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_user_by_id,
    register_user,
)
from .config import CORS_ORIGINS_LIST, DEFAULT_MODEL, DEFAULT_TEMPERATURE
from .llm import call_llm, get_available_models, LLMError, parse_model_string, stream_llm
from .models import (
    CreateConversationRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SendMessageRequest,
    UpdateConversationRequest,
)
from . import storage
from .token_tracking import record_usage

logger = logging.getLogger(__name__)

app = FastAPI(title="XQT5 AI Plattform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Cache-Control", "Connection"],
)


# ── Public Endpoints ──


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "xqt5-ai-plattform-backend"}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "healthy", "env": os.getenv("ENVIRONMENT", "development")}


@app.get("/api/models")
async def list_models() -> list:
    return get_available_models()


# ── Auth Endpoints ──


@app.post("/api/auth/register", response_model=None)
async def register(request: RegisterRequest):
    user = register_user(request.username, request.email, request.password)
    access_token = create_access_token(user["id"], user.get("is_admin", False))
    refresh_token = create_refresh_token(user["id"])
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


@app.post("/api/auth/login", response_model=None)
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(user["id"], user.get("is_admin", False))
    refresh_token = create_refresh_token(user["id"])
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


@app.post("/api/auth/refresh", response_model=None)
async def refresh(request: RefreshRequest):
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access_token = create_access_token(user["id"], user.get("is_admin", False))
    return {
        "access_token": access_token,
        "user": user,
    }


@app.get("/api/auth/me", response_model=None)
async def get_me(current_user: Dict = Depends(get_current_user)):
    user = get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Protected Endpoints ──


@app.get("/api/conversations")
async def list_conversations(current_user: Dict = Depends(get_current_user)) -> list:
    return storage.list_conversations(user_id=current_user["id"])


@app.post("/api/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: Dict = Depends(get_current_user),
) -> dict:
    return storage.create_conversation(
        title=request.title or "New Conversation",
        user_id=current_user["id"],
        model=request.model,
        temperature=request.temperature,
    )


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: Dict = Depends(get_current_user),
) -> dict:
    if not storage.verify_conversation_owner(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: Dict = Depends(get_current_user),
) -> dict:
    if not storage.verify_conversation_owner(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")

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
async def delete_conversation(
    conversation_id: str,
    current_user: Dict = Depends(get_current_user),
) -> dict:
    if not storage.verify_conversation_owner(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
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
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: Dict = Depends(get_current_user),
):
    if not storage.verify_conversation_owner(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")

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
            _stream_response(
                conversation_id, llm_messages, model, temperature,
                is_first_message, request.content, current_user["id"],
            ),
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

    # Record token usage
    usage = result.get("usage", {})
    if usage:
        provider, _ = parse_model_string(model)
        record_usage(
            user_id=current_user["id"],
            chat_id=conversation_id,
            model=model,
            provider=provider,
            prompt_tokens=usage.get("prompt_tokens", usage.get("input_tokens", 0)),
            completion_tokens=usage.get("completion_tokens", usage.get("output_tokens", 0)),
        )

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
    user_id: str,
):
    full_content = ""
    usage = {}
    try:
        async for chunk in stream_llm(llm_messages, model, temperature):
            if isinstance(chunk, dict):
                # Usage data from final chunk
                usage = chunk.get("usage", {})
            else:
                full_content += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n"

        # Store the complete assistant message
        storage.add_assistant_message(conversation_id, full_content, model=model)

        # Record token usage
        if usage:
            provider, _ = parse_model_string(model)
            record_usage(
                user_id=user_id,
                chat_id=conversation_id,
                model=model,
                provider=provider,
                prompt_tokens=usage.get("prompt_tokens", usage.get("input_tokens", 0)),
                completion_tokens=usage.get("completion_tokens", usage.get("output_tokens", 0)),
            )

        yield f"data: {json.dumps({'done': True, 'content': full_content})}\n\n"

        # Auto-name in background after stream completes
        if is_first_message:
            asyncio.create_task(_auto_name_conversation(conversation_id, user_content))

    except LLMError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'error': 'An unexpected error occurred'})}\n\n"


# ── Usage Endpoint ──


@app.get("/api/usage", response_model=None)
async def get_usage(current_user: Dict = Depends(get_current_user)):
    from .token_tracking import get_user_usage_summary
    return get_user_usage_summary(current_user["id"])
