import logging
from typing import Any, Dict, List, Optional

from .database import supabase

logger = logging.getLogger(__name__)


def list_users() -> List[Dict[str, Any]]:
    result = supabase.table("app_users").select(
        "id,username,email,is_active,is_admin,created_at"
    ).order("created_at", desc=True).execute()
    return result.data


def update_user(user_id: str, is_active: Optional[bool] = None, is_admin: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    updates = {}
    if is_active is not None:
        updates["is_active"] = is_active
    if is_admin is not None:
        updates["is_admin"] = is_admin
    if not updates:
        return None

    result = supabase.table("app_users").update(updates).eq("id", user_id).execute()
    if not result.data:
        return None
    return result.data[0]


def get_global_usage_summary() -> Dict[str, Any]:
    result = supabase.table("chat_token_usage").select("*").execute()
    rows = result.data or []

    total_tokens = sum(r["total_tokens"] for r in rows)
    total_prompt = sum(r["prompt_tokens"] for r in rows)
    total_completion = sum(r["completion_tokens"] for r in rows)
    total_cost = sum(float(r["estimated_cost"]) for r in rows)

    return {
        "total_tokens": total_tokens,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "estimated_cost": round(total_cost, 4),
        "request_count": len(rows),
    }


def get_usage_per_user() -> List[Dict[str, Any]]:
    # Get all usage records
    usage_result = supabase.table("chat_token_usage").select("*").execute()
    rows = usage_result.data or []

    # Get all users
    users_result = supabase.table("app_users").select("id,username,email").execute()
    users_map = {u["id"]: u for u in (users_result.data or [])}

    # Aggregate per user
    per_user = {}
    for r in rows:
        uid = r["user_id"]
        if uid not in per_user:
            user = users_map.get(uid, {})
            per_user[uid] = {
                "user_id": uid,
                "username": user.get("username", "Unknown"),
                "email": user.get("email", ""),
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "estimated_cost": 0.0,
                "request_count": 0,
            }
        per_user[uid]["total_tokens"] += r["total_tokens"]
        per_user[uid]["prompt_tokens"] += r["prompt_tokens"]
        per_user[uid]["completion_tokens"] += r["completion_tokens"]
        per_user[uid]["estimated_cost"] += float(r["estimated_cost"])
        per_user[uid]["request_count"] += 1

    # Round costs
    for entry in per_user.values():
        entry["estimated_cost"] = round(entry["estimated_cost"], 4)

    # Sort by cost descending
    return sorted(per_user.values(), key=lambda x: x["estimated_cost"], reverse=True)


def get_system_stats() -> Dict[str, Any]:
    users = supabase.table("app_users").select("id,is_active", count="exact").execute()
    active_users = supabase.table("app_users").select("id", count="exact").eq("is_active", True).execute()
    chats = supabase.table("chats").select("id", count="exact").execute()
    messages = supabase.table("chat_messages").select("id", count="exact").execute()
    assistants_q = supabase.table("assistants").select("id", count="exact").execute()
    templates_q = supabase.table("prompt_templates").select("id", count="exact").execute()

    return {
        "total_users": users.count or 0,
        "active_users": active_users.count or 0,
        "total_chats": chats.count or 0,
        "total_messages": messages.count or 0,
        "total_assistants": assistants_q.count or 0,
        "total_templates": templates_q.count or 0,
    }


# ── Model Config CRUD ──


def list_model_configs() -> List[Dict[str, Any]]:
    result = supabase.table("app_model_config").select("*").order("sort_order").execute()
    return result.data


def create_model_config(
    model_id: str,
    provider: str,
    display_name: str,
    sort_order: int = 0,
) -> Dict[str, Any]:
    result = supabase.table("app_model_config").insert({
        "model_id": model_id,
        "provider": provider,
        "display_name": display_name,
        "sort_order": sort_order,
    }).execute()
    return result.data[0]


def update_model_config(config_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    allowed = {"display_name", "is_enabled", "is_default", "sort_order"}
    update_data = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not update_data:
        return None

    # If setting a new default, unset all others first
    if update_data.get("is_default") is True:
        supabase.table("app_model_config").update({"is_default": False}).eq("is_default", True).execute()

    result = supabase.table("app_model_config").update(update_data).eq("id", config_id).execute()
    if not result.data:
        return None
    return result.data[0]


def delete_model_config(config_id: str) -> bool:
    result = supabase.table("app_model_config").delete().eq("id", config_id).execute()
    return len(result.data) > 0
