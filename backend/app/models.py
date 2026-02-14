from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50000)


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
