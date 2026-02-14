import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import CORS_ORIGINS_LIST
from .models import CreateConversationRequest, SendMessageRequest
from . import storage

app = FastAPI(title="XQT5 AI Plattform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "service": "xqt5-ai-plattform-backend"}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "healthy", "env": os.getenv("ENVIRONMENT", "development")}


@app.get("/api/conversations")
async def list_conversations() -> list:
    return storage.list_conversations()


@app.post("/api/conversations")
async def create_conversation(request: CreateConversationRequest) -> dict:
    return storage.create_conversation(title=request.title or "New Conversation")


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest) -> dict:
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    storage.add_user_message(conversation_id, request.content)

    # Minimal placeholder response for initial scaffold.
    assistant_reply = (
        "Platzhalter-Antwort: Hier wird im nächsten Schritt ein externer "
        "llm-council-API-Adapter angebunden."
    )
    storage.add_assistant_message(conversation_id, assistant_reply, metadata={"mode": "placeholder"})

    updated = storage.get_conversation(conversation_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to load updated conversation")

    return updated
