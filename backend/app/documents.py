import base64
import logging
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from .config import MISTRAL_OCR_INCLUDE_IMAGE_BASE64, MISTRAL_OCR_STRUCTURED
from .database import supabase

logger = logging.getLogger(__name__)

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

    PDFs and images are always processed via Mistral OCR.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text, _ = await _ocr_pdf_mistral_with_assets(file_bytes, filename)
        return text
    elif lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace")
    elif is_supported_image(lower):
        return await _ocr_image_mistral(file_bytes, filename, guess_image_mime(filename))
    else:
        raise ValueError(f"Unsupported file type: {filename}")


async def extract_text_and_assets(filename: str, file_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text and OCR-derived image assets from a file."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return await _ocr_pdf_mistral_with_assets(file_bytes, filename)
    if lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace"), []
    if is_supported_image(lower):
        text = await _ocr_image_mistral(file_bytes, filename, guess_image_mime(filename))
        return text, []
    raise ValueError(f"Unsupported file type: {filename}")


async def _ocr_pdf_mistral(file_bytes: bytes, filename: str) -> str:
    """Run OCR on a PDF via the Mistral OCR API."""
    text, _ = await _ocr_pdf_mistral_with_assets(file_bytes, filename)
    return text


async def _ocr_pdf_mistral_with_assets(file_bytes: bytes, filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Run OCR on a PDF via the Mistral OCR API and return text + image assets."""
    from . import providers as providers_mod

    api_key = providers_mod.get_api_key("mistral")
    if not api_key:
        raise ValueError(
            "Mistral API-Key nicht konfiguriert — gescannte PDFs können nicht verarbeitet werden. "
            "Bitte Key unter Admin > Provider hinterlegen."
        )

    b64 = base64.b64encode(file_bytes).decode("ascii")
    document_url = f"data:application/pdf;base64,{b64}"
    return await _mistral_ocr_document_with_assets(api_key, document_url, filename, len(file_bytes))


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
    image_url = f"data:{mime_type};base64,{b64}"
    payload = _build_mistral_payload_image(image_url)

    logger.info("OCR via Mistral (image) for %s (%d bytes)", filename, len(file_bytes))

    async with httpx.AsyncClient(timeout=120.0) as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        resp = await client.post(
            "https://api.mistral.ai/v1/ocr",
            headers=headers,
            json=payload,
        )
        # Some API versions expect image_url as object: {"url": "..."}
        if resp.status_code == 422:
            payload_obj = _build_mistral_payload_image(image_url, as_object=True)
            resp = await client.post(
                "https://api.mistral.ai/v1/ocr",
                headers=headers,
                json=payload_obj,
            )

    if resp.status_code != 200:
        detail = resp.text[:600]
        logger.error("Mistral image OCR failed (%d): %s", resp.status_code, detail)
        raise ValueError(f"Mistral OCR fehlgeschlagen (HTTP {resp.status_code}): {detail}")

    data = resp.json()
    return _extract_text_from_mistral_response(data)


def _build_mistral_payload_document(document_url: str, include_type: bool = True) -> Dict[str, Any]:
    document: Dict[str, Any] = {"document_url": document_url}
    if include_type:
        document["type"] = "document_url"

    payload: Dict[str, Any] = {
        "model": "mistral-ocr-latest",
        "document": document,
    }
    if MISTRAL_OCR_STRUCTURED:
        payload.update(_mistral_annotation_formats())
    if MISTRAL_OCR_INCLUDE_IMAGE_BASE64:
        payload["include_image_base64"] = True
    return payload


def _build_mistral_payload_image(image_url: str, as_object: bool = False) -> Dict[str, Any]:
    image_value: Any = {"url": image_url} if as_object else image_url
    payload: Dict[str, Any] = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "image_url",
            "image_url": image_value,
        },
    }
    if MISTRAL_OCR_STRUCTURED:
        payload.update(_mistral_annotation_formats())
    if MISTRAL_OCR_INCLUDE_IMAGE_BASE64:
        payload["include_image_base64"] = True
    return payload


def _mistral_annotation_formats() -> Dict[str, Any]:
    return {
        "bbox_annotation_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "bbox_annotation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "title": "BBOXAnnotation",
                    "additionalProperties": False,
                    "required": ["document_type", "short_description", "summary"],
                    "properties": {
                        "document_type": {
                            "type": "string",
                            "title": "Document_Type",
                            "description": "The type of the image.",
                        },
                        "short_description": {
                            "type": "string",
                            "title": "Short_Description",
                            "description": "A description in German describing the image.",
                        },
                        "summary": {
                            "type": "string",
                            "title": "Summary",
                            "description": "Summarize the image in German.",
                        },
                    },
                },
            },
        },
        "document_annotation_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "document_annotation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "title": "DocumentAnnotation",
                    "additionalProperties": False,
                    "required": ["language", "chapter_titles", "urls"],
                    "properties": {
                        "language": {"type": "string", "title": "Language"},
                        "chapter_titles": {"type": "string", "title": "Chapter_Titles"},
                        "urls": {"type": "string", "title": "urls"},
                    },
                },
            },
        },
    }


def _extract_text_from_mistral_response(data: Dict[str, Any]) -> str:
    text, _ = _extract_text_and_assets_from_mistral_response(data)
    return text


def _extract_text_and_assets_from_mistral_response(data: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    pages = data.get("pages", []) or []
    updated_pages = _apply_summaries_to_pages(pages)
    extracted = _build_extracted_markdown(updated_pages)

    # Optional extra structured block from document-level annotation
    doc_anno = data.get("document_annotation")
    doc_anno_text = _document_annotation_to_text(doc_anno)
    if doc_anno_text:
        extracted = f"{extracted}\n\n{doc_anno_text}".strip()

    assets = _extract_image_assets_from_pages(updated_pages)
    return extracted, assets


def _build_extracted_markdown(pages: List[Dict[str, Any]]) -> str:
    sorted_pages = sorted(pages, key=lambda p: _safe_int(p.get("index")) or 0)
    page_blocks: List[str] = []

    for page in sorted_pages:
        markdown = _page_markdown_with_image_refs(page)
        if markdown:
            page_blocks.append(markdown)

    if page_blocks:
        # Keep OCR markdown structure as-is for better retrieval quality.
        return "\n\n".join(page_blocks).strip()

    # Fallback only if API returned no markdown.
    fallback_text = "\n\n".join(
        str(p.get("text", "")).strip()
        for p in sorted_pages
        if str(p.get("text", "")).strip()
    ).strip()
    return _normalize_markdown_text(fallback_text)


def _page_markdown_with_image_refs(page: Dict[str, Any]) -> str:
    markdown = str(page.get("markdown", "")).strip()
    images = page.get("images", []) or []
    if not images:
        return markdown

    refs_to_add: List[str] = []
    existing_ids = set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown))
    for idx, img in enumerate(images):
        img_id = str(img.get("id", "")).strip()
        if not img_id or img_id in existing_ids:
            continue
        refs_to_add.append(f"![img-{idx}]({img_id})")

    if not refs_to_add:
        return markdown
    if markdown:
        return f"{markdown}\n\n" + "\n".join(refs_to_add)
    return "\n".join(refs_to_add)


def _normalize_markdown_text(text: str) -> str:
    """Light markdown-aware normalization for cleaner retrieval chunks."""
    if not text:
        return ""

    t = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix OCR soft-hyphen line wraps: "Fachbe-\nreiche" -> "Fachbereiche"
    t = re.sub(r"([A-Za-zÄÖÜäöüß])-\n([A-Za-zÄÖÜäöüß])", r"\1\2", t)

    lines = [ln.rstrip() for ln in t.split("\n")]
    out: List[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            out.append("")
            continue

        # Drop common page boilerplate lines
        if re.match(r"^Seite\s+\d+\s*/\s*\d+$", s, flags=re.IGNORECASE):
            continue
        if re.match(r"^(Vorlagen-Version|Organisationseinheit|Bearbeiter)\s*:", s, flags=re.IGNORECASE):
            continue
        if re.match(r"^\d{2}\.\d{2}\.\d{4}\s+Version\s+\d+", s, flags=re.IGNORECASE):
            continue

        # Normalize bullets
        if s.startswith("• "):
            s = "- " + s[2:].strip()

        # Turn numbered section titles into markdown headings
        if re.match(r"^\d+(\.\d+)+\s+\S+", s):
            s = "### " + s

        out.append(s)

    # Compact excessive blank lines
    normalized = "\n".join(out)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    return normalized


def _apply_summaries_to_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []
    image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    for page in pages:
        markdown = str(page.get("markdown", ""))
        images = page.get("images", []) or []
        summary_by_id: Dict[str, str] = {}

        for img in images:
            img_id = img.get("id")
            if not img_id:
                continue
            summary = _clean_for_paren(_get_summary(img.get("image_annotation")))
            if summary:
                summary_by_id[str(img_id).strip()] = summary

        def repl(match: re.Match[str]) -> str:
            original = match.group(0)
            link_target = match.group(2).strip()
            summary = summary_by_id.get(link_target)
            if not summary:
                return original
            return f"{original} ({summary})"

        updated_markdown = image_pattern.sub(repl, markdown)
        updated.append({**page, "markdown": updated_markdown})

    return updated


def _get_summary(image_annotation: Any) -> str:
    if not image_annotation:
        return ""
    if isinstance(image_annotation, str):
        try:
            parsed = json.loads(image_annotation)
            return str(parsed.get("summary", "")).strip()
        except Exception:
            return ""
    if isinstance(image_annotation, dict):
        return str(image_annotation.get("summary", "")).strip()
    return ""


def _clean_for_paren(text: str) -> str:
    return (
        str(text or "")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .strip()
    )


def _document_annotation_to_text(annotation: Any) -> str:
    if not annotation:
        return ""
    obj: Dict[str, Any]
    if isinstance(annotation, str):
        try:
            obj = json.loads(annotation)
        except Exception:
            return ""
    elif isinstance(annotation, dict):
        obj = annotation
    else:
        return ""

    language = str(obj.get("language", "")).strip()
    chapters = str(obj.get("chapter_titles", "")).strip()
    urls = str(obj.get("urls", "")).strip()
    fields = []
    if language:
        fields.append(f"language: {language}")
    if chapters:
        fields.append(f"chapter_titles: {chapters}")
    if urls:
        fields.append(f"urls: {urls}")
    if not fields:
        return ""
    return "[Document annotation]\n" + "\n".join(f"- {f}" for f in fields)


def _extract_image_assets_from_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    assets: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    sorted_pages = sorted(pages, key=lambda p: _safe_int(p.get("index")) or 0)

    for page in sorted_pages:
        raw_page_index = page.get("index")
        page_number: Optional[int] = None
        if isinstance(raw_page_index, int):
            page_number = raw_page_index + 1
        elif isinstance(raw_page_index, str) and raw_page_index.isdigit():
            page_number = int(raw_page_index) + 1

        for img in page.get("images", []) or []:
            data_uri, mime_type = _image_data_uri_from_ocr_image(img)
            if not data_uri:
                continue

            img_id = str(img.get("id", "")).strip()
            dedupe_key = f"{page_number}:{img_id or data_uri[:96]}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            annotation = _parse_json_like(img.get("image_annotation"))
            summary = str(annotation.get("summary", "")).strip()
            short_description = str(annotation.get("short_description", "")).strip()
            document_type = str(annotation.get("document_type", "")).strip()

            caption = summary or short_description or document_type or "Bildquelle aus OCR"
            ocr_text_parts = [summary, short_description, document_type]
            ocr_text = "\n".join(part for part in ocr_text_parts if part).strip()

            width = _safe_int(img.get("width"))
            height = _safe_int(img.get("height"))

            assets.append(
                {
                    "asset_type": "embedded_image",
                    "storage_path": data_uri,
                    "mime_type": mime_type,
                    "page_number": page_number,
                    "width": width,
                    "height": height,
                    "caption": caption,
                    "ocr_text": ocr_text or caption,
                }
            )

    return assets


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_json_like(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _image_data_uri_from_ocr_image(image_obj: Dict[str, Any]) -> Tuple[str, str]:
    if not isinstance(image_obj, dict):
        return "", ""

    mime_type = str(image_obj.get("mime_type") or "image/png").strip() or "image/png"

    for key in ("image_base64", "base64"):
        raw = image_obj.get(key)
        if isinstance(raw, str) and raw.strip():
            value = raw.strip()
            if value.startswith("data:image/"):
                mime_match = re.match(r"^data:([^;]+);base64,", value)
                if mime_match:
                    mime_type = mime_match.group(1)
                return value, mime_type
            return f"data:{mime_type};base64,{value}", mime_type

    image_id = str(image_obj.get("id", "")).strip()
    if image_id.startswith("data:image/"):
        mime_match = re.match(r"^data:([^;]+);base64,", image_id)
        if mime_match:
            mime_type = mime_match.group(1)
        return image_id, mime_type

    return "", ""


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


def list_ready_document_texts(
    user_id: str,
    chat_id: Optional[str] = None,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Return ready document texts for fallback grounding."""
    query = supabase.table("app_documents").select(
        "id,filename,extracted_text,chat_id,created_at"
    ).eq("user_id", user_id).eq("status", "ready").is_("pool_id", "null")

    if chat_id:
        query = query.or_(f"chat_id.eq.{chat_id},chat_id.is.null")
    else:
        query = query.is_("chat_id", "null")

    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


def list_ready_pool_document_texts(
    pool_id: str,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Return ready pool document texts for fallback grounding."""
    result = (
        supabase.table("app_documents")
        .select("id,filename,extracted_text,created_at")
        .eq("pool_id", pool_id)
        .eq("status", "ready")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


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


def create_document_assets(
    document_id: str,
    user_id: str,
    assets: List[Dict[str, Any]],
    embeddings: Optional[List[Optional[List[float]]]] = None,
    pool_id: Optional[str] = None,
) -> int:
    """Store multiple OCR-derived image assets for a document."""
    if not assets:
        return 0

    rows: List[Dict[str, Any]] = []
    for idx, asset in enumerate(assets):
        storage_path = str(asset.get("storage_path", "")).strip()
        if not storage_path:
            continue

        row: Dict[str, Any] = {
            "document_id": document_id,
            "user_id": user_id,
            "pool_id": pool_id,
            "page_number": _safe_int(asset.get("page_number")),
            "asset_type": str(asset.get("asset_type", "embedded_image")).strip() or "embedded_image",
            "storage_path": storage_path,
            "mime_type": str(asset.get("mime_type", "image/png")).strip() or "image/png",
            "width": _safe_int(asset.get("width")),
            "height": _safe_int(asset.get("height")),
            "caption": str(asset.get("caption", "")).strip()[:4000],
            "ocr_text": str(asset.get("ocr_text", "")).strip()[:20000],
        }

        if embeddings and idx < len(embeddings) and embeddings[idx]:
            row["embedding"] = str(embeddings[idx])

        rows.append(row)

    if not rows:
        return 0

    try:
        result = supabase.table("app_document_assets").insert(rows).execute()
    except Exception as e:
        logger.info("Asset batch insert failed (skipping OCR assets): %s", e)
        return 0

    return len(result.data or [])


async def _mistral_ocr_document_with_assets(
    api_key: str,
    document_url: str,
    filename: str,
    byte_length: int,
) -> Tuple[str, List[Dict[str, Any]]]:
    payload = _build_mistral_payload_document(document_url)

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

    if resp.status_code == 422:
        payload_fallback = _build_mistral_payload_document(document_url, include_type=False)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.mistral.ai/v1/ocr",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload_fallback,
            )

    if resp.status_code != 200:
        detail = resp.text[:300]
        logger.error("Mistral OCR failed (%d): %s", resp.status_code, detail)
        raise ValueError(f"Mistral OCR fehlgeschlagen (HTTP {resp.status_code})")

    data = resp.json()
    return _extract_text_and_assets_from_mistral_response(data)


async def _mistral_ocr_document(api_key: str, document_url: str, filename: str, byte_length: int) -> str:
    text, _ = await _mistral_ocr_document_with_assets(api_key, document_url, filename, byte_length)
    return text
