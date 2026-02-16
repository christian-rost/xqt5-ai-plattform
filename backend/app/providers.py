import logging
from typing import Any, Dict, List, Optional

import httpx

from .config import PROVIDER_KEYS
from .database import supabase
from .encryption import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

# Known providers and their env-var key names
KNOWN_PROVIDERS = ["openai", "anthropic", "google", "mistral", "x-ai"]

PROVIDER_DISPLAY = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "mistral": "Mistral",
    "x-ai": "xAI",
}


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for provider. Priority: DB (active) > env var."""
    try:
        result = supabase.table("app_provider_keys").select(
            "api_key_encrypted,is_active"
        ).eq("provider", provider).execute()
        if result.data:
            row = result.data[0]
            if row["is_active"]:
                decrypted = decrypt_value(row["api_key_encrypted"])
                if decrypted:
                    return decrypted
    except Exception as e:
        logger.warning(f"Failed to load provider key from DB for {provider}: {e}")

    # Fallback to env var
    env_key = PROVIDER_KEYS.get(provider, "")
    return env_key if env_key else None


def list_providers() -> List[Dict[str, Any]]:
    """List all known providers with their key source status."""
    # Load DB keys
    db_keys = {}
    try:
        result = supabase.table("app_provider_keys").select(
            "provider,is_active,updated_at"
        ).execute()
        for row in (result.data or []):
            db_keys[row["provider"]] = row
    except Exception as e:
        logger.warning(f"Failed to load provider keys from DB: {e}")

    providers = []
    for provider in KNOWN_PROVIDERS:
        db_row = db_keys.get(provider)
        has_env = bool(PROVIDER_KEYS.get(provider, ""))

        if db_row and db_row["is_active"]:
            source = "db"
        elif has_env:
            source = "env"
        else:
            source = "none"

        providers.append({
            "provider": provider,
            "display_name": PROVIDER_DISPLAY.get(provider, provider),
            "source": source,
            "has_env": has_env,
            "has_db": bool(db_row and db_row["is_active"]),
            "updated_at": db_row["updated_at"] if db_row else None,
        })

    return providers


def set_provider_key(provider: str, api_key: str) -> Dict[str, Any]:
    """Encrypt and upsert a provider API key."""
    encrypted = encrypt_value(api_key)
    result = supabase.table("app_provider_keys").upsert({
        "provider": provider,
        "api_key_encrypted": encrypted,
        "is_active": True,
    }, on_conflict="provider").execute()
    return result.data[0] if result.data else {"provider": provider, "status": "saved"}


def delete_provider_key(provider: str) -> bool:
    """Soft-delete: set is_active=False."""
    result = supabase.table("app_provider_keys").update({
        "is_active": False,
    }).eq("provider", provider).execute()
    return bool(result.data)


async def test_provider(provider: str) -> Dict[str, Any]:
    """Minimal connectivity test for a provider."""
    from .llm import PROVIDER_CONFIG

    key = get_api_key(provider)
    if not key:
        return {"success": False, "error": "Kein API-Key konfiguriert"}

    config = PROVIDER_CONFIG.get(provider)
    if not config:
        return {"success": False, "error": f"Unbekannter Provider: {provider}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if provider == "google":
                url = f"{config['base_url']}/models?key={key}"
                resp = await client.get(url)
            else:
                url = f"{config['base_url']}/models"
                headers = {
                    config.get("auth_header", "Authorization"): f"{config.get('auth_prefix', 'Bearer ')}{key}",
                }
                if provider == "anthropic":
                    headers["anthropic-version"] = "2023-06-01"
                resp = await client.get(url, headers=headers)

            if resp.status_code == 200:
                return {"success": True, "message": "Verbindung erfolgreich"}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }
    except httpx.TimeoutException:
        return {"success": False, "error": "Timeout bei der Verbindung"}
    except Exception as e:
        return {"success": False, "error": str(e)}
