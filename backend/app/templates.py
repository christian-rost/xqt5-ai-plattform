from typing import Any, Dict, List, Optional
from .database import supabase


def create_template(
    user_id: str,
    name: str,
    description: str,
    content: str,
    category: str = "general",
    is_global: bool = False,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "name": name,
        "description": description,
        "content": content,
        "category": category,
        "is_global": is_global,
    }
    result = supabase.table("prompt_templates").insert(payload).execute()
    return result.data[0]


def list_templates(user_id: str) -> List[Dict[str, Any]]:
    """Return user's own templates + all global templates."""
    own = supabase.table("prompt_templates").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    global_q = supabase.table("prompt_templates").select("*").eq("is_global", True).neq("user_id", user_id).order("created_at", desc=True).execute()
    return own.data + global_q.data


def get_template(template_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get template if user owns it or it's global."""
    result = supabase.table("prompt_templates").select("*").eq("id", template_id).execute()
    if not result.data:
        return None
    template = result.data[0]
    if template["user_id"] == user_id or template.get("is_global"):
        return template
    return None


def update_template(template_id: str, user_id: str, is_admin: bool = False, **fields: Any) -> Optional[Dict[str, Any]]:
    """Update template. Only owner can update own; admins can update global."""
    template = supabase.table("prompt_templates").select("*").eq("id", template_id).execute()
    if not template.data:
        return None
    t = template.data[0]
    if t["user_id"] != user_id and not (is_admin and t.get("is_global")):
        return None

    allowed = {"name", "description", "content", "category"}
    update_data = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not update_data:
        return t

    result = supabase.table("prompt_templates").update(update_data).eq("id", template_id).execute()
    return result.data[0] if result.data else None


def delete_template(template_id: str, user_id: str, is_admin: bool = False) -> bool:
    """Delete template. Only owner can delete own; admins can delete global."""
    template = supabase.table("prompt_templates").select("*").eq("id", template_id).execute()
    if not template.data:
        return False
    t = template.data[0]
    if t["user_id"] != user_id and not (is_admin and t.get("is_global")):
        return False

    result = supabase.table("prompt_templates").delete().eq("id", template_id).execute()
    return len(result.data) > 0
