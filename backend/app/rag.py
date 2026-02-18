import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    RAG_SIMILARITY_THRESHOLD,
    RAG_TOP_K,
)
from .database import supabase
from . import documents as documents_mod
from . import providers as providers_mod
from .token_tracking import record_usage

logger = logging.getLogger(__name__)

IMAGE_QUERY_KEYWORDS = {
    "image", "images", "picture", "pictures", "photo", "photos", "figure", "figures",
    "chart", "charts", "graph", "graphs", "diagram", "diagrams", "screenshot", "screenshots",
    "bild", "bilder", "grafik", "grafiken", "abbildung", "abbildungen", "diagramm", "diagramme",
    "chartanalyse", "visual", "visuell", "tabellenbild", "plot",
}

SUMMARY_QUERY_KEYWORDS = {
    "summarize", "summary", "overview", "abstract", "recap",
    "zusammenfassen", "zusammenfassung", "fasse", "überblick", "ueberblick",
}


def detect_query_intent(query: str) -> str:
    """Return a coarse retrieval intent: summary or fact."""
    q = (query or "").lower()
    if any(keyword in q for keyword in SUMMARY_QUERY_KEYWORDS):
        return "summary"
    return "fact"


def should_use_image_retrieval(query: str, image_mode: str) -> bool:
    """Decide whether image retrieval should run for a query."""
    mode = (image_mode or "auto").lower()
    if mode == "off":
        return False
    if mode == "on":
        return True

    q = (query or "").lower()
    return any(keyword in q for keyword in IMAGE_QUERY_KEYWORDS)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into chunks, preferring paragraph boundaries."""
    if not text or not text.strip():
        return []

    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= chunk_size:
            current = current + "\n\n" + para if current else para
        else:
            if current:
                chunks.append(current)
            # If paragraph itself is too long, hard-split it
            if len(para) > chunk_size:
                while para:
                    chunks.append(para[:chunk_size])
                    para = para[max(0, chunk_size - overlap):]
                    if len(para) <= overlap:
                        break
                current = ""
            else:
                # Start new chunk with overlap from previous
                if chunks and overlap > 0:
                    prev = chunks[-1]
                    overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                    current = overlap_text + "\n\n" + para
                else:
                    current = para

    if current:
        chunks.append(current)

    return chunks


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings via OpenAI API."""
    api_key = providers_mod.get_api_key("openai")
    if not api_key:
        raise RuntimeError("OpenAI API key not configured — required for embeddings")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": texts,
                "dimensions": EMBEDDING_DIMENSIONS,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI Embedding API error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

    embeddings = [item["embedding"] for item in data["data"]]
    return embeddings


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


async def process_document(document_id: str, text: str, user_id: str) -> Tuple[int, int]:
    """Chunk text, generate embeddings, store in DB. Returns (chunk_count, total_tokens)."""
    chunks = chunk_text(text)
    if not chunks:
        documents_mod.update_document_status(document_id, "error", error_message="No text extracted")
        return 0, 0

    try:
        embeddings = await generate_embeddings(chunks)
    except Exception as e:
        documents_mod.update_document_status(document_id, "error", error_message=str(e))
        raise

    total_tokens = 0
    rows = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        token_count = _estimate_tokens(chunk)
        total_tokens += token_count
        rows.append({
            "document_id": document_id,
            "chunk_index": i,
            "content": chunk,
            "token_count": token_count,
            "embedding": str(embedding),
        })

    # Batch insert chunks
    supabase.table("app_document_chunks").insert(rows).execute()

    documents_mod.update_document_status(document_id, "ready", chunk_count=len(chunks))

    # Record embedding token usage
    record_usage(
        user_id=user_id,
        chat_id=None,
        model=EMBEDDING_MODEL,
        provider="openai",
        prompt_tokens=total_tokens,
        completion_tokens=0,
    )

    return len(chunks), total_tokens


async def search_similar_chunks(
    query: str,
    user_id: str,
    chat_id: Optional[str] = None,
    pool_id: Optional[str] = None,
    top_k: int = RAG_TOP_K,
    threshold: float = RAG_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Search for similar chunks using the Supabase RPC."""
    # Generate query embedding
    embeddings = await generate_embeddings([query])
    query_embedding = embeddings[0]

    params = {
        "query_embedding": str(query_embedding),
        "match_user_id": user_id,
        "match_chat_id": chat_id,
        "match_threshold": threshold,
        "match_count": top_k,
    }
    if pool_id:
        params["match_pool_id"] = pool_id

    result = supabase.rpc("match_document_chunks", params).execute()

    return result.data or []


async def retrieve_chunks_with_strategy(
    query: str,
    user_id: str,
    chat_id: Optional[str] = None,
    pool_id: Optional[str] = None,
    intent: str = "fact",
    rerank_settings: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Adaptive retrieval with fallback passes for generic/summary prompts."""
    plans: List[Tuple[int, float]]
    if intent == "summary":
        plans = [
            (max(RAG_TOP_K, 8), max(RAG_SIMILARITY_THRESHOLD * 0.7, 0.08)),
            (max(RAG_TOP_K * 2, 12), 0.0),
        ]
    else:
        plans = [
            (RAG_TOP_K, RAG_SIMILARITY_THRESHOLD),
            (max(RAG_TOP_K + 3, 8), max(RAG_SIMILARITY_THRESHOLD * 0.6, 0.08)),
        ]

    for top_k, threshold in plans:
        chunks = await search_similar_chunks(
            query=query,
            user_id=user_id,
            chat_id=chat_id,
            pool_id=pool_id,
            top_k=top_k,
            threshold=threshold,
        )
        if chunks:
            return await _apply_optional_rerank(query, chunks, rerank_settings)

    return []


async def _apply_optional_rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    rerank_settings: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    settings = rerank_settings or {}
    enabled = bool(settings.get("rerank_enabled", False))
    if not enabled or not chunks:
        return chunks

    candidates = max(5, min(100, int(settings.get("rerank_candidates", 20))))
    top_n = max(1, min(30, int(settings.get("rerank_top_n", 6))))
    model = str(settings.get("rerank_model", "rerank-v3.5")).strip() or "rerank-v3.5"
    if top_n > candidates:
        top_n = candidates

    key = providers_mod.get_api_key("cohere")
    if not key:
        logger.warning("Rerank enabled but no Cohere key configured; using vector ranking only")
        return chunks[:top_n]

    subset = chunks[:candidates]
    reranked = await _cohere_rerank(query, subset, key, model=model, top_n=top_n)
    return reranked or subset[:top_n]


async def _cohere_rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    api_key: str,
    model: str,
    top_n: int,
) -> List[Dict[str, Any]]:
    if not chunks:
        return []

    documents = [str(c.get("content", ""))[:8000] for c in chunks]
    payload = {
        "model": model,
        "query": query,
        "documents": documents,
        "top_n": min(top_n, len(documents)),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post("https://api.cohere.com/v2/rerank", headers=headers, json=payload)
        if resp.status_code != 200:
            logger.warning("Cohere rerank failed with HTTP %s: %s", resp.status_code, resp.text[:300])
            return []
        data = resp.json()
        results = data.get("results", []) or []
        reranked: List[Dict[str, Any]] = []
        for r in results:
            idx = r.get("index")
            if idx is None or idx < 0 or idx >= len(chunks):
                continue
            chunk = dict(chunks[idx])
            if "relevance_score" in r:
                chunk["rerank_score"] = float(r["relevance_score"])
            reranked.append(chunk)
        return reranked
    except Exception as e:
        logger.warning("Cohere rerank exception: %s", e)
        return []


async def search_similar_assets(
    query: str,
    user_id: str,
    chat_id: Optional[str] = None,
    pool_id: Optional[str] = None,
    top_k: int = RAG_TOP_K,
    threshold: float = RAG_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Search for similar image assets (if multimodal schema is available)."""
    embeddings = await generate_embeddings([query])
    query_embedding = embeddings[0]

    params = {
        "query_embedding": str(query_embedding),
        "match_user_id": user_id,
        "match_chat_id": chat_id,
        "match_threshold": threshold,
        "match_count": top_k,
    }
    if pool_id:
        params["match_pool_id"] = pool_id

    try:
        result = supabase.rpc("match_document_assets", params).execute()
    except Exception as e:
        # Schema might not be migrated yet in some environments.
        logger.info("Image asset retrieval unavailable: %s", e)
        return []

    return result.data or []


def build_rag_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not chunks:
        return ""

    parts = ["[Relevant documents for context:]"]
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.get("filename", "unknown")
        similarity = chunk.get("similarity", 0)
        content = chunk.get("content", "")
        parts.append(f"\n--- Source {i}: {filename} (relevance: {similarity:.0%}) ---\n{content}")

    return "\n".join(parts)


def build_image_rag_context(assets: List[Dict[str, Any]]) -> str:
    """Format image asset hits into a compact context string for the LLM."""
    if not assets:
        return ""

    parts = ["[Relevant image/document visual context:]"]
    for i, asset in enumerate(assets, 1):
        filename = asset.get("filename", "unknown")
        page = asset.get("page_number")
        similarity = asset.get("similarity", 0)
        caption = (asset.get("caption") or "").strip()
        page_info = f", page {page}" if page is not None else ""
        parts.append(
            f"\n--- Visual Source {i}: {filename}{page_info} (relevance: {similarity:.0%}) ---\n"
            f"{caption or 'No caption available.'}"
        )

    return "\n".join(parts)
