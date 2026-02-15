from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    model: Optional[str] = None
    temperature: Optional[float] = None


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50000)
    model: Optional[str] = None
    temperature: Optional[float] = None
    stream: bool = False


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None


class AvailableModel(BaseModel):
    id: str
    provider: str
    name: str
    available: bool


class ConversationMetadata(BaseModel):
    id: str
    created_at: str
    title: str
    message_count: int


class ConversationResponse(BaseModel):
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    temperature: Optional[float] = None
