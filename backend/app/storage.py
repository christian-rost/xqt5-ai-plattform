import uuid
from typing import Any, Dict, List, Optional
from .database import supabase


def create_conversation(title: str = "New Conversation", user_id: Optional[str] = None) -> Dict[str, Any]:
    payload = {
        "id": str(uuid.uuid4()),
        "title": title,
        "user_id": user_id,
    }
    result = supabase.table("conversations").insert(payload).execute()
    row = result.data[0]
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "title": row["title"],
        "messages": [],
    }


def list_conversations(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = supabase.table("conversations").select("id,created_at,title,user_id").order("created_at", desc=True)
    if user_id:
        query = query.eq("user_id", user_id)

    result = query.execute()
    items: List[Dict[str, Any]] = []
    for row in result.data:
        count_result = supabase.table("messages").select("id", count="exact").eq("conversation_id", row["id"]).execute()
        items.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "title": row["title"],
                "message_count": count_result.count or 0,
            }
        )
    return items


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    conv_result = supabase.table("conversations").select("*").eq("id", conversation_id).execute()
    if not conv_result.data:
        return None

    conv = conv_result.data[0]
    msg_result = (
        supabase.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )

    messages: List[Dict[str, Any]] = []
    for msg in msg_result.data:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg.get("content", "")})
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.get("content"),
                    "stage1": msg.get("stage1"),
                    "stage2": msg.get("stage2"),
                    "stage3": msg.get("stage3"),
                    "metadata": msg.get("metadata"),
                }
            )

    return {
        "id": conv["id"],
        "created_at": conv["created_at"],
        "title": conv["title"],
        "messages": messages,
    }


def add_user_message(conversation_id: str, content: str) -> None:
    supabase.table("messages").insert(
        {"conversation_id": conversation_id, "role": "user", "content": content}
    ).execute()


def add_assistant_message(conversation_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": content,
        "stage1": [],
        "stage2": [],
        "stage3": {"answer": content},
    }
    if metadata:
        payload["metadata"] = metadata

    supabase.table("messages").insert(payload).execute()


def delete_conversation(conversation_id: str) -> bool:
    result = supabase.table("conversations").delete().eq("id", conversation_id).execute()
    return len(result.data) > 0
