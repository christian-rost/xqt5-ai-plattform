from typing import Any, Dict, List, Optional
from .database import supabase


def create_assistant(
    user_id: str,
    name: str,
    description: str,
    system_prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    is_global: bool = False,
    icon: str = "\U0001f916",
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
        "is_global": is_global,
        "icon": icon,
    }
    if model is not None:
        payload["model"] = model
    if temperature is not None:
        payload["temperature"] = temperature

    result = supabase.table("assistants").insert(payload).execute()
    return result.data[0]


def list_assistants(user_id: str) -> List[Dict[str, Any]]:
    """Return user's own assistants + all global assistants."""
    own = supabase.table("assistants").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    global_q = supabase.table("assistants").select("*").eq("is_global", True).neq("user_id", user_id).order("created_at", desc=True).execute()
    return own.data + global_q.data


def get_assistant(assistant_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get assistant if user owns it or it's global."""
    result = supabase.table("assistants").select("*").eq("id", assistant_id).execute()
    if not result.data:
        return None
    assistant = result.data[0]
    if assistant["user_id"] == user_id or assistant.get("is_global"):
        return assistant
    return None


def update_assistant(assistant_id: str, user_id: str, is_admin: bool = False, **fields: Any) -> Optional[Dict[str, Any]]:
    """Update assistant. Only owner can update own; admins can update global."""
    assistant = supabase.table("assistants").select("*").eq("id", assistant_id).execute()
    if not assistant.data:
        return None
    a = assistant.data[0]
    if a["user_id"] != user_id and not (is_admin and a.get("is_global")):
        return None

    allowed = {"name", "description", "system_prompt", "model", "temperature", "icon"}
    update_data = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not update_data:
        return a

    result = supabase.table("assistants").update(update_data).eq("id", assistant_id).execute()
    return result.data[0] if result.data else None


def delete_assistant(assistant_id: str, user_id: str, is_admin: bool = False) -> bool:
    """Delete assistant. Only owner can delete own; admins can delete global."""
    assistant = supabase.table("assistants").select("*").eq("id", assistant_id).execute()
    if not assistant.data:
        return False
    a = assistant.data[0]
    if a["user_id"] != user_id and not (is_admin and a.get("is_global")):
        return False

    result = supabase.table("assistants").delete().eq("id", assistant_id).execute()
    return len(result.data) > 0
