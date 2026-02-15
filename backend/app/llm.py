import json
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx

from .config import PROVIDER_KEYS


class LLMError(Exception):
    pass


# Provider endpoint and header configuration
PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "chat_path": "/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "chat_path": "/messages",
        "auth_header": "x-api-key",
        "auth_prefix": "",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "chat_path": "/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "x-ai": {
        "base_url": "https://api.x.ai/v1",
        "chat_path": "/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
}

# Available models per provider
AVAILABLE_MODELS = [
    {"id": "openai/gpt-5.1", "provider": "openai", "name": "GPT-5.1"},
    {"id": "openai/gpt-4.1", "provider": "openai", "name": "GPT-4.1"},
    {"id": "openai/gpt-4.1-mini", "provider": "openai", "name": "GPT-4.1 Mini"},
    {"id": "anthropic/claude-sonnet-4-5", "provider": "anthropic", "name": "Claude Sonnet 4.5"},
    {"id": "anthropic/claude-haiku-3-5", "provider": "anthropic", "name": "Claude Haiku 3.5"},
    {"id": "google/gemini-3-pro-preview", "provider": "google", "name": "Gemini 3 Pro"},
    {"id": "google/gemini-2.5-flash", "provider": "google", "name": "Gemini 2.5 Flash"},
    {"id": "mistral/mistral-large-latest", "provider": "mistral", "name": "Mistral Large"},
    {"id": "x-ai/grok-4", "provider": "x-ai", "name": "Grok 4"},
]


def parse_model_string(model_string: str) -> Tuple[str, str]:
    if "/" not in model_string:
        raise LLMError(f"Invalid model format: {model_string}. Expected 'provider/model-name'.")
    provider, model_name = model_string.split("/", 1)
    if provider not in PROVIDER_CONFIG:
        raise LLMError(f"Unknown provider: {provider}")
    return provider, model_name


def get_available_models() -> List[Dict[str, Any]]:
    result = []
    for model in AVAILABLE_MODELS:
        available = bool(PROVIDER_KEYS.get(model["provider"]))
        result.append({**model, "available": available})
    return result


def _get_api_key(provider: str) -> str:
    key = PROVIDER_KEYS.get(provider, "")
    if not key:
        raise LLMError(f"No API key configured for provider: {provider}")
    return key


def _build_openai_compatible_request(
    messages: List[Dict[str, str]], model_name: str, temperature: float, stream: bool
) -> Dict[str, Any]:
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }


def _build_anthropic_request(
    messages: List[Dict[str, str]], model_name: str, temperature: float, stream: bool
) -> Dict[str, Any]:
    # Anthropic uses a different format: system message separate, messages array
    system_msg = None
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})

    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": chat_messages,
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": stream,
    }
    if system_msg:
        payload["system"] = system_msg
    return payload


def _build_google_request(
    messages: List[Dict[str, str]], temperature: float, stream: bool
) -> Dict[str, Any]:
    # Google Gemini uses a different format
    contents = []
    system_instruction = None
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        else:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    return payload


async def call_llm(
    messages: List[Dict[str, str]], model: str, temperature: float
) -> Dict[str, Any]:
    provider, model_name = parse_model_string(model)
    api_key = _get_api_key(provider)

    async with httpx.AsyncClient(timeout=60.0) as client:
        if provider == "google":
            return await _call_google(client, messages, model_name, temperature, api_key)
        elif provider == "anthropic":
            return await _call_anthropic(client, messages, model_name, temperature, api_key)
        else:
            return await _call_openai_compatible(client, messages, model_name, temperature, api_key, provider)


async def _call_openai_compatible(
    client: httpx.AsyncClient,
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float,
    api_key: str,
    provider: str,
) -> Dict[str, Any]:
    config = PROVIDER_CONFIG[provider]
    url = f"{config['base_url']}{config['chat_path']}"
    headers = {
        config["auth_header"]: f"{config['auth_prefix']}{api_key}",
        "Content-Type": "application/json",
    }
    payload = _build_openai_compatible_request(messages, model_name, temperature, stream=False)

    resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise LLMError(f"{provider} API error ({resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    return {
        "content": data["choices"][0]["message"]["content"],
        "usage": data.get("usage", {}),
    }


async def _call_anthropic(
    client: httpx.AsyncClient,
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float,
    api_key: str,
) -> Dict[str, Any]:
    config = PROVIDER_CONFIG["anthropic"]
    url = f"{config['base_url']}{config['chat_path']}"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = _build_anthropic_request(messages, model_name, temperature, stream=False)

    resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise LLMError(f"Anthropic API error ({resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    content_blocks = data.get("content", [])
    text = "".join(block["text"] for block in content_blocks if block.get("type") == "text")
    return {
        "content": text,
        "usage": data.get("usage", {}),
    }


async def _call_google(
    client: httpx.AsyncClient,
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float,
    api_key: str,
) -> Dict[str, Any]:
    url = f"{PROVIDER_CONFIG['google']['base_url']}/models/{model_name}:generateContent?key={api_key}"
    payload = _build_google_request(messages, temperature, stream=False)

    resp = await client.post(url, json=payload)
    if resp.status_code != 200:
        raise LLMError(f"Google API error ({resp.status_code}): {resp.text[:500]}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise LLMError("Google API returned no candidates")
    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    usage = data.get("usageMetadata", {})
    return {
        "content": text,
        "usage": {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        },
    }


async def stream_llm(
    messages: List[Dict[str, str]], model: str, temperature: float
) -> AsyncIterator[str]:
    provider, model_name = parse_model_string(model)
    api_key = _get_api_key(provider)

    async with httpx.AsyncClient(timeout=120.0) as client:
        if provider == "google":
            async for chunk in _stream_google(client, messages, model_name, temperature, api_key):
                yield chunk
        elif provider == "anthropic":
            async for chunk in _stream_anthropic(client, messages, model_name, temperature, api_key):
                yield chunk
        else:
            async for chunk in _stream_openai_compatible(client, messages, model_name, temperature, api_key, provider):
                yield chunk


async def _stream_openai_compatible(
    client: httpx.AsyncClient,
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float,
    api_key: str,
    provider: str,
) -> AsyncIterator[str]:
    config = PROVIDER_CONFIG[provider]
    url = f"{config['base_url']}{config['chat_path']}"
    headers = {
        config["auth_header"]: f"{config['auth_prefix']}{api_key}",
        "Content-Type": "application/json",
    }
    payload = _build_openai_compatible_request(messages, model_name, temperature, stream=True)

    async with client.stream("POST", url, headers=headers, json=payload) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            raise LLMError(f"{provider} API error ({resp.status_code}): {body.decode()[:500]}")

        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                delta = data["choices"][0].get("delta", {}).get("content", "")
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


async def _stream_anthropic(
    client: httpx.AsyncClient,
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float,
    api_key: str,
) -> AsyncIterator[str]:
    config = PROVIDER_CONFIG["anthropic"]
    url = f"{config['base_url']}{config['chat_path']}"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = _build_anthropic_request(messages, model_name, temperature, stream=True)

    async with client.stream("POST", url, headers=headers, json=payload) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            raise LLMError(f"Anthropic API error ({resp.status_code}): {body.decode()[:500]}")

        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {}).get("text", "")
                    if delta:
                        yield delta
            except (json.JSONDecodeError, KeyError):
                continue


async def _stream_google(
    client: httpx.AsyncClient,
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float,
    api_key: str,
) -> AsyncIterator[str]:
    url = f"{PROVIDER_CONFIG['google']['base_url']}/models/{model_name}:streamGenerateContent?alt=sse&key={api_key}"
    payload = _build_google_request(messages, temperature, stream=True)

    async with client.stream("POST", url, json=payload) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            raise LLMError(f"Google API error ({resp.status_code}): {body.decode()[:500]}")

        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text", "")
                        if text:
                            yield text
            except (json.JSONDecodeError, KeyError):
                continue
