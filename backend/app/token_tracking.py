import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from .database import supabase

logger = logging.getLogger(__name__)

# Cost per 1M tokens (input, output) in USD
COST_PER_1M_TOKENS = {
    # OpenAI
    "gpt-5.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    # Anthropic
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-haiku-3-5": {"input": 0.80, "output": 4.00},
    # Google
    "gemini-3-pro-preview": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    # Mistral
    "mistral-large-latest": {"input": 2.00, "output": 6.00},
    # X.AI
    "grok-4": {"input": 3.00, "output": 15.00},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    # Strip provider prefix if present
    model_name = model.split("/", 1)[-1] if "/" in model else model
    costs = COST_PER_1M_TOKENS.get(model_name, {"input": 1.0, "output": 3.0})
    input_cost = (prompt_tokens / 1_000_000) * costs["input"]
    output_cost = (completion_tokens / 1_000_000) * costs["output"]
    return round(input_cost + output_cost, 6)


def record_usage(
    user_id: str,
    chat_id: Optional[str],
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost(model, prompt_tokens, completion_tokens)

    try:
        supabase.table("chat_token_usage").insert({
            "user_id": user_id,
            "chat_id": chat_id,
            "model": model,
            "provider": provider,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": cost,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to record token usage: {e}")


def get_user_usage_summary(user_id: str) -> Dict[str, Any]:
    result = supabase.table("chat_token_usage").select("*").eq("user_id", user_id).execute()
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
