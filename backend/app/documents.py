import base64
import io
import logging
from typing import Any, Dict, List, Optional

import httpx

from .database import supabase

logger = logging.getLogger(__name__)

OCR_MIN_CHARS = 50
IMAGE_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def is_supported_image(filename: str) -> bool:
    lower = (filename or "").lower()
    return any(lower.endswith(ext) for ext in IMAGE_MIME_BY_EXT)


def guess_image_mime(filename: str) -> str:
    lower = (filename or "").lower()
    for ext, mime in IMAGE_MIME_BY_EXT.items():
        if lower.endswith(ext):
            return mime
    return "image/png"


async def extract_text(filename: str, file_bytes: bytes) -> str:
    """Extract text from PDF or TXT file.

    For PDFs, tries pypdf first. If fewer than OCR_MIN_CHARS characters are
    extracted (e.g. scanned PDFs), falls back to Mistral OCR API.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        result = "\n\n".join(pages)
        if len(result.strip()) < OCR_MIN_CHARS:
            logger.info("pypdf extracted < %d chars for %s, trying Mistral OCR", OCR_MIN_CHARS, filename)
            result = await _ocr_pdf_mistral(file_bytes, filename)
        return result
    elif lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace")
    elif is_supported_image(lower):
        return await _ocr_image_mistral(file_bytes, filename, guess_image_mime(filename))
    else:
        raise ValueError(f"Unsupported file type: {filename}")


async def _ocr_pdf_mistral(file_bytes: bytes, filename: str) -> str:
    """Run OCR on a PDF via the Mistral OCR API."""
    from . import providers as providers_mod

    api_key = providers_mod.get_api_key("mistral")
    if not api_key:
        raise ValueError(
            "Mistral API-Key nicht konfiguriert — gescannte PDFs können nicht verarbeitet werden. "
            "Bitte Key unter Admin > Provider hinterlegen."
        )

    b64 = base64.b64encode(file_bytes).decode("ascii")
    document_url = f"data:application/pdf;base64,{b64}"
    return await _mistral_ocr_document(api_key, document_url, filename, len(file_bytes))


async def _ocr_image_mistral(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """Run OCR / visual extraction on a single image via Mistral OCR API."""
    from . import providers as providers_mod

    api_key = providers_mod.get_api_key("mistral")
    if not api_key:
        raise ValueError(
            "Mistral API-Key nicht konfiguriert — Bilder können nicht verarbeitet werden. "
            "Bitte Key unter Admin > Provider hinterlegen."
        )

    b64 = base64.b64encode(file_bytes).decode("ascii")
    document_url = f"data:{mime_type};base64,{b64}"
    return await _mistral_ocr_document(api_key, document_url, filename, len(file_bytes))


async def _mistral_ocr_document(api_key: str, document_url: str, filename: str, byte_length: int) -> str:
    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": document_url,
        },
    }

    logger.info("OCR via Mistral for %s (%d bytes)", filename, byte_length)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "https://api.mistral.ai/v1/ocr",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code != 200:
        detail = resp.text[:300]
        logger.error("Mistral OCR failed (%d): %s", resp.status_code, detail)
        raise ValueError(f"Mistral OCR fehlgeschlagen (HTTP {resp.status_code})")

    data = resp.json()
    pages = data.get("pages", [])
    texts = [p.get("markdown", "") for p in pages if p.get("markdown")]
    return "\n\n".join(texts)


def create_document(
    user_id: str,
    chat_id: Optional[str],
    filename: str,
    file_type: str,
    file_size_bytes: int,
    extracted_text: str,
    pool_id: Optional[str] = None,
) -> Dict[str, Any]:
    row = {
        "user_id": user_id,
        "filename": filename,
        "file_type": file_type,
        "file_size_bytes": file_size_bytes,
        "extracted_text": extracted_text,
        "status": "processing",
    }
    if chat_id:
        row["chat_id"] = chat_id
    if pool_id:
        row["pool_id"] = pool_id
    result = supabase.table("app_documents").insert(row).execute()
    return result.data[0]


def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int = 0,
    error_message: Optional[str] = None,
) -> None:
    updates: Dict[str, Any] = {"status": status, "chunk_count": chunk_count}
    if error_message:
        updates["error_message"] = error_message
    supabase.table("app_documents").update(updates).eq("id", document_id).execute()


def list_documents(
    user_id: str,
    chat_id: Optional[str] = None,
    scope: str = "all",
) -> List[Dict[str, Any]]:
    """List documents. scope: 'chat' (only chat_id), 'global' (chat_id IS NULL), 'all' (both)."""
    query = supabase.table("app_documents").select(
        "id,filename,file_type,file_size_bytes,chunk_count,status,error_message,chat_id,created_at"
    ).eq("user_id", user_id)

    if scope == "chat" and chat_id:
        query = query.eq("chat_id", chat_id)
    elif scope == "global":
        query = query.is_("chat_id", "null")
    elif scope == "all" and chat_id:
        query = query.or_(f"chat_id.eq.{chat_id},chat_id.is.null")

    result = query.order("created_at", desc=True).execute()
    return result.data or []


def get_document(document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    result = supabase.table("app_documents").select("*").eq(
        "id", document_id
    ).eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def delete_document(document_id: str, user_id: str) -> bool:
    result = supabase.table("app_documents").delete().eq(
        "id", document_id
    ).eq("user_id", user_id).execute()
    return bool(result.data)


def has_ready_documents(user_id: str, chat_id: Optional[str] = None) -> bool:
    """Quick check if user has any ready documents (chat-specific or global)."""
    query = supabase.table("app_documents").select("id", count="exact").eq(
        "user_id", user_id
    ).eq("status", "ready")

    if chat_id:
        query = query.or_(f"chat_id.eq.{chat_id},chat_id.is.null")
    else:
        query = query.is_("chat_id", "null")

    result = query.limit(1).execute()
    return bool(result.data)


def create_document_asset(
    document_id: str,
    user_id: str,
    file_bytes: bytes,
    mime_type: str,
    filename: str,
    caption: str,
    ocr_text: str,
    embedding: Optional[List[float]] = None,
    pool_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Store an inline image asset for multimodal retrieval.

    Uses a data URI in storage_path as MVP, so no separate object storage is required.
    """
    data_b64 = base64.b64encode(file_bytes).decode("ascii")
    storage_path = f"data:{mime_type};base64,{data_b64}"
    row: Dict[str, Any] = {
        "document_id": document_id,
        "user_id": user_id,
        "pool_id": pool_id,
        "asset_type": "upload_image",
        "storage_path": storage_path,
        "mime_type": mime_type,
        "caption": (caption or "")[:4000],
        "ocr_text": (ocr_text or "")[:20000],
    }
    if embedding:
        row["embedding"] = str(embedding)

    try:
        result = supabase.table("app_document_assets").insert(row).execute()
    except Exception as e:
        logger.info("Asset table unavailable or insert failed (skipping image asset): %s", e)
        return None

    return result.data[0] if result.data else None
