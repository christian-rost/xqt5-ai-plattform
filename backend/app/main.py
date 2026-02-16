import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_admin,
    get_current_user,
    get_user_by_id,
    register_user,
)
from .config import CORS_ORIGINS_LIST, DEFAULT_MODEL, DEFAULT_TEMPERATURE, MAX_UPLOAD_SIZE_MB
from .llm import call_llm, get_available_models, LLMError, parse_model_string, stream_llm
from .models import (
    CreateAssistantRequest,
    CreateConversationRequest,
    CreateModelConfigRequest,
    CreateTemplateRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SendMessageRequest,
    UpdateAssistantRequest,
    UpdateConversationRequest,
    UpdateModelConfigRequest,
    UpdateTemplateRequest,
    UpdateUserRequest,
)
from . import admin as admin_crud
from . import assistants as assistants_crud
from . import audit
from . import documents as documents_mod
from . import providers as providers_mod
from . import rag as rag_mod
from . import storage
from . import templates as templates_crud
from .token_tracking import record_usage

logger = logging.getLogger(__name__)

app = FastAPI(title="XQT5 AI-Workplace API")

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
    return {"status": "ok", "service": "xqt5-ai-workplace-backend"}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "healthy", "env": os.getenv("ENVIRONMENT", "development")}


@app.get("/api/models")
async def list_models() -> list:
    return get_available_models()


# ── Auth Endpoints ──


@app.post("/api/auth/register", response_model=None)
async def register(request: RegisterRequest, req: Request):
    user = register_user(request.username, request.email, request.password)
    access_token = create_access_token(user["id"], user.get("is_admin", False))
    refresh_token = create_refresh_token(user["id"])
    audit.log_event(audit.AUTH_REGISTER, user_id=user["id"], ip_address=req.client.host)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }


@app.post("/api/auth/login", response_model=None)
async def login(request: LoginRequest, req: Request):
    user = authenticate_user(request.username, request.password)
    if not user:
        audit.log_event(
            audit.AUTH_LOGIN_FAILED,
            metadata={"username": request.username},
            ip_address=req.client.host,
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(user["id"], user.get("is_admin", False))
    refresh_token = create_refresh_token(user["id"])
    audit.log_event(audit.AUTH_LOGIN, user_id=user["id"], ip_address=req.client.host)
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
    model = request.model
    temperature = request.temperature

    # If assistant_id is provided, use its defaults
    if request.assistant_id:
        assistant = assistants_crud.get_assistant(request.assistant_id, current_user["id"])
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")
        if not model and assistant.get("model"):
            model = assistant["model"]
        if temperature is None and assistant.get("temperature") is not None:
            temperature = assistant["temperature"]

    result = storage.create_conversation(
        title=request.title or "New Conversation",
        user_id=current_user["id"],
        model=model,
        temperature=temperature,
        assistant_id=request.assistant_id,
    )
    audit.log_event(
        audit.CHAT_CONVERSATION_CREATE,
        user_id=current_user["id"],
        target_type="conversation",
        target_id=result.get("id"),
    )
    return result


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
    audit.log_event(
        audit.CHAT_CONVERSATION_DELETE,
        user_id=current_user["id"],
        target_type="conversation",
        target_id=conversation_id,
    )
    return {"deleted": True}


def _build_llm_messages(
    conversation_messages: List[Dict],
    system_prompt: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Convert stored messages to LLM-compatible format, optionally prepending a system prompt."""
    llm_messages = []
    if system_prompt:
        llm_messages.append({"role": "system", "content": system_prompt})
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

    # Load assistant if linked
    system_prompt = None
    assistant = None
    if conversation.get("assistant_id"):
        assistant = assistants_crud.get_assistant(conversation["assistant_id"], current_user["id"])
        if assistant:
            system_prompt = assistant.get("system_prompt")

    # Determine model and temperature: message-level > conversation-level > assistant > default
    model = request.model or conversation.get("model") or (assistant.get("model") if assistant else None) or DEFAULT_MODEL
    temperature = request.temperature if request.temperature is not None else (
        conversation.get("temperature") if conversation.get("temperature") is not None else (
            assistant.get("temperature") if assistant and assistant.get("temperature") is not None else DEFAULT_TEMPERATURE
        )
    )

    # Store user message
    storage.add_user_message(conversation_id, request.content)

    # Check if this is the first user message (for auto-naming)
    is_first_message = all(m["role"] != "user" for m in conversation.get("messages", []))

    # Build LLM message history (with system prompt if assistant)
    llm_messages = _build_llm_messages(conversation.get("messages", []), system_prompt=system_prompt)
    llm_messages.append({"role": "user", "content": request.content})

    # RAG: inject relevant document context
    rag_sources = []
    try:
        if documents_mod.has_ready_documents(current_user["id"], conversation_id):
            chunks = await rag_mod.search_similar_chunks(
                query=request.content,
                user_id=current_user["id"],
                chat_id=conversation_id,
            )
            if chunks:
                rag_context = rag_mod.build_rag_context(chunks)
                rag_sources = [
                    {"filename": c["filename"], "similarity": round(c["similarity"], 3)}
                    for c in chunks
                ]
                # Inject as system message (or append to existing system prompt)
                if llm_messages and llm_messages[0]["role"] == "system":
                    llm_messages[0]["content"] += "\n\n" + rag_context
                else:
                    llm_messages.insert(0, {"role": "system", "content": rag_context})
    except Exception as e:
        logger.warning(f"RAG injection failed: {e}")

    if request.stream:
        return StreamingResponse(
            _stream_response(
                conversation_id, llm_messages, model, temperature,
                is_first_message, request.content, current_user["id"],
                rag_sources=rag_sources,
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

    # Audit log (metadata only, no content)
    audit.log_event(
        audit.CHAT_MESSAGE_SEND,
        user_id=current_user["id"],
        target_type="conversation",
        target_id=conversation_id,
        metadata={"model": model},
    )

    # Auto-name in background
    if is_first_message:
        asyncio.create_task(_auto_name_conversation(conversation_id, request.content))

    updated = storage.get_conversation(conversation_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to load updated conversation")
    if rag_sources:
        updated["rag_sources"] = rag_sources
    return updated


async def _stream_response(
    conversation_id: str,
    llm_messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    is_first_message: bool,
    user_content: str,
    user_id: str,
    rag_sources: Optional[List[Dict]] = None,
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

        # Audit log (metadata only, no content)
        audit.log_event(
            audit.CHAT_MESSAGE_SEND,
            user_id=user_id,
            target_type="conversation",
            target_id=conversation_id,
            metadata={"model": model},
        )

        done_data = {'done': True, 'content': full_content}
        if rag_sources:
            done_data['sources'] = rag_sources
        yield f"data: {json.dumps(done_data)}\n\n"

        # Auto-name in background after stream completes
        if is_first_message:
            asyncio.create_task(_auto_name_conversation(conversation_id, user_content))

    except LLMError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'error': 'An unexpected error occurred'})}\n\n"


# ── Assistants Endpoints ──


@app.get("/api/assistants", response_model=None)
async def list_assistants(current_user: Dict = Depends(get_current_user)):
    return assistants_crud.list_assistants(current_user["id"])


@app.post("/api/assistants", response_model=None)
async def create_assistant(
    request: CreateAssistantRequest,
    current_user: Dict = Depends(get_current_user),
):
    if request.is_global and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Only admins can create global assistants")
    return assistants_crud.create_assistant(
        user_id=current_user["id"],
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        model=request.model,
        temperature=request.temperature,
        is_global=request.is_global,
        icon=request.icon,
    )


@app.get("/api/assistants/{assistant_id}", response_model=None)
async def get_assistant(
    assistant_id: str,
    current_user: Dict = Depends(get_current_user),
):
    assistant = assistants_crud.get_assistant(assistant_id, current_user["id"])
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return assistant


@app.patch("/api/assistants/{assistant_id}", response_model=None)
async def update_assistant(
    assistant_id: str,
    request: UpdateAssistantRequest,
    current_user: Dict = Depends(get_current_user),
):
    updates = request.model_dump(exclude_none=True)
    result = assistants_crud.update_assistant(
        assistant_id, current_user["id"],
        is_admin=current_user.get("is_admin", False),
        **updates,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Assistant not found or no permission")
    return result


@app.delete("/api/assistants/{assistant_id}", response_model=None)
async def delete_assistant(
    assistant_id: str,
    current_user: Dict = Depends(get_current_user),
):
    deleted = assistants_crud.delete_assistant(
        assistant_id, current_user["id"],
        is_admin=current_user.get("is_admin", False),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Assistant not found or no permission")
    return {"deleted": True}


# ── Templates Endpoints ──


@app.get("/api/templates", response_model=None)
async def list_templates(current_user: Dict = Depends(get_current_user)):
    return templates_crud.list_templates(current_user["id"])


@app.post("/api/templates", response_model=None)
async def create_template(
    request: CreateTemplateRequest,
    current_user: Dict = Depends(get_current_user),
):
    if request.is_global and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Only admins can create global templates")
    return templates_crud.create_template(
        user_id=current_user["id"],
        name=request.name,
        description=request.description,
        content=request.content,
        category=request.category,
        is_global=request.is_global,
    )


@app.get("/api/templates/{template_id}", response_model=None)
async def get_template(
    template_id: str,
    current_user: Dict = Depends(get_current_user),
):
    template = templates_crud.get_template(template_id, current_user["id"])
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.patch("/api/templates/{template_id}", response_model=None)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    current_user: Dict = Depends(get_current_user),
):
    updates = request.model_dump(exclude_none=True)
    result = templates_crud.update_template(
        template_id, current_user["id"],
        is_admin=current_user.get("is_admin", False),
        **updates,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Template not found or no permission")
    return result


@app.delete("/api/templates/{template_id}", response_model=None)
async def delete_template(
    template_id: str,
    current_user: Dict = Depends(get_current_user),
):
    deleted = templates_crud.delete_template(
        template_id, current_user["id"],
        is_admin=current_user.get("is_admin", False),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found or no permission")
    return {"deleted": True}


# ── Document / RAG Endpoints ──


@app.post("/api/documents/upload", response_model=None)
async def upload_document(
    file: UploadFile = File(...),
    chat_id: Optional[str] = Form(None),
    current_user: Dict = Depends(get_current_user),
):
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    lower = file.filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

    # Read and validate size
    file_bytes = await file.read()
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_UPLOAD_SIZE_MB}MB limit")

    # Verify chat ownership if chat_id provided
    if chat_id:
        if not storage.verify_conversation_owner(chat_id, current_user["id"]):
            raise HTTPException(status_code=404, detail="Conversation not found")

    # Extract text
    try:
        extracted_text = documents_mod.extract_text(file.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not extract text: {e}")

    if not extracted_text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from file")

    file_type = "pdf" if lower.endswith(".pdf") else "txt"

    # Create document record
    doc = documents_mod.create_document(
        user_id=current_user["id"],
        chat_id=chat_id,
        filename=file.filename,
        file_type=file_type,
        file_size_bytes=len(file_bytes),
        extracted_text=extracted_text,
    )

    # Process: chunk + embed (async but awaited)
    try:
        chunk_count, tokens_used = await rag_mod.process_document(
            doc["id"], extracted_text, current_user["id"],
        )
        doc["chunk_count"] = chunk_count
        doc["status"] = "ready"
    except Exception as e:
        logger.error(f"RAG processing failed for {doc['id']}: {e}")
        doc["status"] = "error"
        doc["error_message"] = str(e)

    return doc


@app.get("/api/documents", response_model=None)
async def list_documents(
    chat_id: Optional[str] = None,
    scope: str = "all",
    current_user: Dict = Depends(get_current_user),
):
    return documents_mod.list_documents(
        user_id=current_user["id"],
        chat_id=chat_id,
        scope=scope,
    )


@app.delete("/api/documents/{document_id}", response_model=None)
async def delete_document(
    document_id: str,
    current_user: Dict = Depends(get_current_user),
):
    deleted = documents_mod.delete_document(document_id, current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


@app.post("/api/rag/search", response_model=None)
async def rag_search(
    request: Request,
    current_user: Dict = Depends(get_current_user),
):
    body = await request.json()
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    chat_id = body.get("chat_id")
    chunks = await rag_mod.search_similar_chunks(
        query=query,
        user_id=current_user["id"],
        chat_id=chat_id,
    )
    return {"chunks": chunks}


# ── Usage Endpoint ──


@app.get("/api/usage", response_model=None)
async def get_usage(current_user: Dict = Depends(get_current_user)):
    from .token_tracking import get_user_usage_summary
    return get_user_usage_summary(current_user["id"])


# ── Admin Endpoints ──


@app.get("/api/admin/users", response_model=None)
async def admin_list_users(admin: Dict = Depends(get_current_admin)):
    return admin_crud.list_users()


@app.patch("/api/admin/users/{user_id}", response_model=None)
async def admin_update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: Dict = Depends(get_current_admin),
):
    # Self-protection: admin cannot deactivate or de-admin themselves
    if user_id == admin["id"]:
        if request.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
        if request.is_admin is False:
            raise HTTPException(status_code=400, detail="Cannot remove your own admin status")

    result = admin_crud.update_user(user_id, is_active=request.is_active, is_admin=request.is_admin)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    # Audit log for user toggles
    if request.is_active is not None:
        action = audit.ADMIN_USER_ACTIVATE if request.is_active else audit.ADMIN_USER_DEACTIVATE
        audit.log_event(action, user_id=admin["id"], target_type="user", target_id=user_id)
    if request.is_admin is not None:
        action = audit.ADMIN_USER_GRANT_ADMIN if request.is_admin else audit.ADMIN_USER_REVOKE_ADMIN
        audit.log_event(action, user_id=admin["id"], target_type="user", target_id=user_id)

    return result


@app.get("/api/admin/usage", response_model=None)
async def admin_get_usage(admin: Dict = Depends(get_current_admin)):
    return {
        "global": admin_crud.get_global_usage_summary(),
        "per_user": admin_crud.get_usage_per_user(),
    }


@app.get("/api/admin/stats", response_model=None)
async def admin_get_stats(admin: Dict = Depends(get_current_admin)):
    return admin_crud.get_system_stats()


@app.get("/api/admin/models", response_model=None)
async def admin_list_models(admin: Dict = Depends(get_current_admin)):
    return admin_crud.list_model_configs()


@app.post("/api/admin/models", response_model=None)
async def admin_create_model(
    request: CreateModelConfigRequest,
    admin: Dict = Depends(get_current_admin),
):
    result = admin_crud.create_model_config(
        model_id=request.model_id,
        provider=request.provider,
        display_name=request.display_name,
        sort_order=request.sort_order,
        deployment_name=request.deployment_name,
    )
    audit.log_event(
        audit.ADMIN_MODEL_CREATE,
        user_id=admin["id"],
        target_type="model_config",
        target_id=result.get("id"),
        metadata={"model_id": request.model_id},
    )
    return result


@app.patch("/api/admin/models/{model_config_id}", response_model=None)
async def admin_update_model(
    model_config_id: str,
    request: UpdateModelConfigRequest,
    admin: Dict = Depends(get_current_admin),
):
    updates = request.model_dump(exclude_none=True)
    result = admin_crud.update_model_config(model_config_id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Model config not found")
    audit.log_event(
        audit.ADMIN_MODEL_UPDATE,
        user_id=admin["id"],
        target_type="model_config",
        target_id=model_config_id,
        metadata=updates,
    )
    return result


@app.delete("/api/admin/models/{model_config_id}", response_model=None)
async def admin_delete_model(
    model_config_id: str,
    admin: Dict = Depends(get_current_admin),
):
    deleted = admin_crud.delete_model_config(model_config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Model config not found")
    audit.log_event(
        audit.ADMIN_MODEL_DELETE,
        user_id=admin["id"],
        target_type="model_config",
        target_id=model_config_id,
    )
    return {"deleted": True}


# ── Provider Key Management ──


@app.get("/api/admin/providers", response_model=None)
async def admin_list_providers(admin: Dict = Depends(get_current_admin)):
    return providers_mod.list_providers()


@app.put("/api/admin/providers/{provider}/key", response_model=None)
async def admin_set_provider_key(
    provider: str,
    request: Request,
    admin: Dict = Depends(get_current_admin),
):
    body = await request.json()
    api_key = body.get("api_key", "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    endpoint_url = body.get("endpoint_url")
    api_version = body.get("api_version")
    providers_mod.set_provider_key(
        provider, api_key,
        endpoint_url=endpoint_url,
        api_version=api_version,
    )
    audit.log_event(
        "admin.provider.set_key",
        user_id=admin["id"],
        target_type="provider",
        target_id=provider,
    )
    return {"status": "saved", "provider": provider}


@app.delete("/api/admin/providers/{provider}/key", response_model=None)
async def admin_delete_provider_key(
    provider: str,
    admin: Dict = Depends(get_current_admin),
):
    deleted = providers_mod.delete_provider_key(provider)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provider key not found")
    audit.log_event(
        "admin.provider.delete_key",
        user_id=admin["id"],
        target_type="provider",
        target_id=provider,
    )
    return {"status": "deleted", "provider": provider}


@app.post("/api/admin/providers/{provider}/test", response_model=None)
async def admin_test_provider(
    provider: str,
    admin: Dict = Depends(get_current_admin),
):
    return await providers_mod.test_provider(provider)


@app.get("/api/admin/audit-logs", response_model=None)
async def admin_get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    admin: Dict = Depends(get_current_admin),
):
    return audit.list_audit_logs(
        limit=min(limit, 500),
        offset=offset,
        action_filter=action,
        user_id_filter=user_id,
    )
