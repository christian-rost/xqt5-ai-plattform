import logging
import re
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

# ---------------------------------------------------------------------------
# Chunking — Markdown-section-aware, token-based (Ansatz A + B)
# ---------------------------------------------------------------------------

# Matches markdown headings: "## Title", "### 1.1 Subsection", etc.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Bullet / numbered list items (treated as atomic units, never split mid-item)
_BULLET_RE = re.compile(r"^\s*[-*•]\s+|^\s*\d+[.)]\s+")

# Sentence boundary: ./?/! followed by space + uppercase or digit.
# Deliberately simple — overlaps prevent hard boundary errors.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ\d\"])")

# Module-level tiktoken encoder (lazy-loaded once, then cached)
_encoder = None


def _get_encoder():
    """Lazy-load and cache the cl100k_base tiktoken encoder."""
    global _encoder
    if _encoder is None:
        import tiktoken  # noqa: PLC0415
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def _tok(text: str) -> int:
    """Return the token count of *text* using the cl100k_base tokenizer."""
    return len(_get_encoder().encode(text))


def _breadcrumb(stack: List[Tuple[int, str]]) -> str:
    """Format a heading stack as a human-readable breadcrumb prefix.

    Example: [(2, "3. Projektrollen"), (3, "3.1 Projektleiter")]
          -> "## 3. Projektrollen > ### 3.1 Projektleiter"
    """
    return " > ".join(f"{'#' * lvl} {txt}" for lvl, txt in stack)


def _split_into_units(text: str) -> List[str]:
    """Break prose into small atomic units for fine-grained chunk assembly.

    Rules (in order):
    1. Empty lines → preserved as empty strings (paragraph breaks).
    2. Bullet / numbered list items → one unit each.
    3. All other lines → sentence-split via _SENT_SPLIT_RE.
    """
    units: List[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            units.append("")
            continue
        if _BULLET_RE.match(stripped):
            units.append(line)
        else:
            parts = _SENT_SPLIT_RE.split(line)
            units.extend(parts)
    return units


def _overlap_tail(units: List[str], overlap_tokens: int) -> List[str]:
    """Return the trailing units that fit within *overlap_tokens*."""
    tail: List[str] = []
    budget = overlap_tokens
    for unit in reversed(units):
        cost = _tok(unit) + 1  # +1 for the joining newline
        if cost > budget:
            break
        tail.insert(0, unit)
        budget -= cost
    return tail


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """Markdown-section-aware chunker with token-based sizing and header injection.

    Improvements over the previous character-based chunker:

    A) **Markdown-section-aware**: The input text (Mistral OCR markdown) is split
       at heading boundaries (``#`` … ``######``).  Each section keeps its own
       heading stack so the embedding model always sees the structural context.

    B) **Header injection**: Every chunk is prefixed with a breadcrumb derived
       from the active heading stack, e.g.::

           ## 3. Projektrollen > ### 3.1 Projektleiter

           Der Projektleiter ist verantwortlich für…

       This ensures that retrieval for "Wer ist Projektleiter?" finds the right
       section even when the heading itself is not in the retrieved chunk.

    C) **Token-based sizing**: ``chunk_size`` and ``overlap`` are now measured in
       *tokens* (tiktoken cl100k_base, same family as text-embedding-3-small),
       not characters.  Default: 512 tokens / 50 tokens overlap.

    D) **Sentence-boundary respect**: When a section must be split, the chunker
       tries to break at sentence endings or bullet-item boundaries rather than
       at arbitrary character positions.
    """
    if not text or not text.strip():
        return []

    # ------------------------------------------------------------------
    # Step 1 — Parse into sections at heading boundaries
    # ------------------------------------------------------------------
    # Each section: (heading_stack, content_lines)
    sections: List[Tuple[List[Tuple[int, str]], List[str]]] = []
    heading_stack: List[Tuple[int, str]] = []
    current_lines: List[str] = []

    for raw_line in text.split("\n"):
        m = _HEADING_RE.match(raw_line)
        if m:
            # Flush previous section only when it has actual text content.
            # Empty sections (heading followed immediately by another heading)
            # are skipped — the parent heading is carried in the breadcrumb of
            # the child section via heading_stack.
            if any(line.strip() for line in current_lines):
                sections.append((list(heading_stack), list(current_lines)))
            current_lines = []
            level = len(m.group(1))
            title = m.group(2).strip()
            # Pop headings at the same or deeper level, then push new heading
            heading_stack = [(lvl, txt) for lvl, txt in heading_stack if lvl < level]
            heading_stack.append((level, title))
        else:
            current_lines.append(raw_line)

    # Flush last section
    if current_lines:
        sections.append((list(heading_stack), list(current_lines)))

    # ------------------------------------------------------------------
    # Step 2 — Convert sections to chunks
    # ------------------------------------------------------------------
    chunks: List[str] = []

    for h_stack, lines in sections:
        bc = _breadcrumb(h_stack)
        content = "\n".join(lines).strip()

        if not content and not bc:
            continue

        prefix = f"{bc}\n\n" if bc else ""
        prefix_tokens = _tok(prefix) if prefix else 0
        full_text = f"{prefix}{content}" if content else bc

        # Happy path: entire section fits in one chunk
        if _tok(full_text) <= chunk_size:
            chunks.append(full_text)
            continue

        # Section too large — split at unit boundaries
        units = _split_into_units(content)
        buf: List[str] = []
        buf_tokens = prefix_tokens

        for unit in units:
            unit_tokens = _tok(unit) + 1  # +1 for joining newline

            # Edge case: single unit exceeds budget → hard token-split
            if unit_tokens > chunk_size - prefix_tokens:
                if buf:
                    chunks.append(f"{prefix}{chr(10).join(buf).strip()}")
                    buf = _overlap_tail(buf, overlap)
                    buf_tokens = prefix_tokens + sum(_tok(u) + 1 for u in buf)

                enc = _get_encoder()
                encoded = enc.encode(unit)
                budget = chunk_size - prefix_tokens
                while encoded:
                    slice_enc = encoded[:budget]
                    encoded = encoded[max(0, budget - overlap):]
                    decoded = enc.decode(slice_enc)
                    chunks.append(f"{prefix}{decoded}")
                    if len(encoded) <= overlap:
                        break
                buf = []
                buf_tokens = prefix_tokens
                continue

            # Normal case: flush buffer when it would overflow
            if buf_tokens + unit_tokens > chunk_size and buf:
                chunks.append(f"{prefix}{chr(10).join(buf).strip()}")
                buf = _overlap_tail(buf, overlap)
                buf_tokens = prefix_tokens + sum(_tok(u) + 1 for u in buf)

            if unit.strip():  # skip empty lines after a flush
                buf.append(unit)
                buf_tokens += unit_tokens

        # Flush remaining buffer
        if buf:
            tail = "\n".join(buf).strip()
            if tail:
                chunks.append(f"{prefix}{tail}")

    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# End of chunking helpers
# ---------------------------------------------------------------------------

IMAGE_QUERY_KEYWORDS = {
    "image", "images", "picture", "pictures", "photo", "photos", "figure", "figures",
    "chart", "charts", "graph", "graphs", "diagram", "diagrams", "screenshot", "screenshots",
    "bild", "bilder", "grafik", "grafiken", "abbildung", "abbildungen", "diagramm", "diagramme",
    "chartanalyse", "visual", "visuell", "tabellenbild", "plot",
}

_GERMAN_STOPWORDS: frozenset = frozenset({
    "aber", "als", "also", "am", "an", "auch", "auf", "aus", "bei", "bin",
    "bis", "bitte", "da", "damit", "dann", "das", "dass", "dem", "den", "der",
    "des", "dessen", "die", "dies", "diese", "diesem", "diesen", "dieser",
    "dieses", "doch", "dort", "du", "durch", "ein", "eine", "einem", "einen",
    "einer", "eines", "einige", "er", "es", "etwa", "euch", "falls", "für",
    "gegen", "gibt", "haben", "hat", "hatte", "hatten", "hier", "ihm", "ihn",
    "ihnen", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres", "im", "in",
    "ins", "ist", "ja", "jede", "jedem", "jeden", "jeder", "jedes", "jetzt",
    "kann", "kein", "keine", "keinem", "keinen", "keiner", "keines", "können",
    "könnte", "man", "manche", "manchem", "manchen", "mancher", "manches",
    "mehr", "mein", "meine", "meinem", "meinen", "meiner", "meines", "mich",
    "mir", "mit", "muss", "nach", "nicht", "nichts", "noch", "nun", "nur",
    "ob", "oder", "ohne", "per", "schon", "sehr", "sein", "seine", "seinem",
    "seinen", "seiner", "seines", "sich", "sie", "sind", "so", "solche",
    "solchem", "solchen", "solcher", "solches", "soll", "sollte", "sonst",
    "sowie", "über", "um", "und", "uns", "unter", "vom", "von", "vor", "war",
    "waren", "was", "weg", "weil", "weit", "welche", "welchem", "welchen",
    "welcher", "welches", "wenn", "wer", "werden", "wie", "wieder", "will",
    "wir", "wird", "wo", "worden", "wäre", "während", "zu", "zum", "zur",
    "zwar", "zwischen",
    # English stopwords (queries may be mixed)
    "a", "about", "all", "are", "be", "been", "by", "can", "do", "for",
    "from", "get", "give", "has", "have", "how", "i", "if", "in", "is",
    "it", "its", "list", "me", "my", "no", "not", "of", "on", "or",
    "please", "show", "tell", "that", "the", "their", "them", "there",
    "they", "this", "to", "us", "was", "we", "what", "which", "who",
    "with", "you", "your",
})

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
    """Exact token count via tiktoken (cl100k_base)."""
    return max(1, _tok(text))


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


def _rpc_chunks(
    embedding: List[float],
    user_id: str,
    chat_id: Optional[str],
    pool_id: Optional[str],
    top_k: int,
    threshold: float,
) -> List[Dict[str, Any]]:
    """Execute match_document_chunks RPC with a pre-computed embedding."""
    params: Dict[str, Any] = {
        "query_embedding": str(embedding),
        "match_user_id": user_id,
        "match_threshold": threshold,
        "match_count": top_k,
    }
    if chat_id is not None:
        params["match_chat_id"] = chat_id
    if pool_id is not None:
        params["match_pool_id"] = pool_id
    result = supabase.rpc("match_document_chunks", params).execute()
    return result.data or []


async def search_similar_chunks(
    query: str,
    user_id: str,
    chat_id: Optional[str] = None,
    pool_id: Optional[str] = None,
    top_k: int = RAG_TOP_K,
    threshold: float = RAG_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Search for similar chunks using the Supabase RPC."""
    embeddings = await generate_embeddings([query])
    return _rpc_chunks(embeddings[0], user_id, chat_id, pool_id, top_k, threshold)


def _extract_query_keywords(query: str, max_keywords: int = 3) -> List[str]:
    """Extract significant keywords from a query for ILIKE supplement search.

    Removes stopwords and short words, returns at most max_keywords terms
    sorted by length (longer = more specific first).
    """
    tokens = re.split(r"[\s,;?!.]+", query.lower())
    keywords = [
        t for t in tokens
        if len(t) >= 4 and t not in _GERMAN_STOPWORDS
    ]
    # Sort longest first (more specific)
    keywords = sorted(set(keywords), key=len, reverse=True)
    return keywords[:max_keywords]


def _keyword_supplement_chunks(
    user_id: str,
    chat_id: Optional[str],
    pool_id: Optional[str],
    keywords: List[str],
    limit: int,
    exclude_ids: set,
) -> List[Dict[str, Any]]:
    """Find chunks that literally contain one of the keywords (ILIKE).

    Scope mirrors the vector search: conversation, pool, or global.
    Returns chunks not already in exclude_ids, enriched with filename.
    Sets similarity=0.01 as a placeholder (will be reranked by Cohere or
    used as tiebreaker fallback).
    """
    if not keywords:
        return []

    # Resolve which document IDs are in scope
    try:
        doc_query = supabase.table("app_documents").select("id, filename").eq("status", "ready")
        if pool_id is not None:
            doc_query = doc_query.eq("pool_id", pool_id)
        elif chat_id is not None:
            doc_query = doc_query.eq("user_id", user_id).is_("pool_id", "null").eq("chat_id", chat_id)
        else:
            doc_query = doc_query.eq("user_id", user_id).is_("pool_id", "null").is_("chat_id", "null")
        doc_result = doc_query.execute()
        docs = doc_result.data or []
    except Exception as e:
        logger.warning("Keyword supplement: failed to fetch doc IDs: %s", e)
        return []

    if not docs:
        return []

    doc_id_to_filename = {d["id"]: d["filename"] for d in docs}
    doc_ids = list(doc_id_to_filename.keys())

    # Search chunks for each keyword, collect hits
    supplement: List[Dict[str, Any]] = []
    seen_chunk_ids: set = set()

    for keyword in keywords:
        if len(supplement) >= limit:
            break
        try:
            rows = (
                supabase.table("app_document_chunks")
                .select("id, document_id, chunk_index, content, token_count")
                .in_("document_id", doc_ids)
                .ilike("content", f"%{keyword}%")
                .limit(limit)
                .execute()
            )
            for row in rows.data or []:
                chunk_id = row.get("id")
                if chunk_id in seen_chunk_ids or chunk_id in exclude_ids:
                    continue
                seen_chunk_ids.add(chunk_id)
                row["filename"] = doc_id_to_filename.get(row.get("document_id", ""), "unknown")
                row["similarity"] = 0.01  # placeholder; Cohere will rerank
                supplement.append(row)
                if len(supplement) >= limit:
                    break
        except Exception as e:
            logger.warning("Keyword supplement: ILIKE query failed for '%s': %s", keyword, e)

    return supplement


async def _search_chunks_hybrid(
    query: str,
    user_id: str,
    chat_id: str,
    top_k: int,
    threshold: float,
) -> List[Dict[str, Any]]:
    """Hybrid chunk search for conversation scope.

    Phase 1 (vector): conversation-specific documents only.
    Phase 2 (keyword): ILIKE supplement for specific terms that vector search
                       may rank too low (e.g. exact section names like
                       "Projektrollen"). Merged results are passed to Cohere
                       reranker for final ordering.
    """
    embeddings = await generate_embeddings([query])
    embedding = embeddings[0]

    # Phase 1 — conversation-specific (vector)
    vector_chunks = _rpc_chunks(embedding, user_id, chat_id, None, top_k, threshold)

    # Phase 2 — keyword supplement (ILIKE)
    keywords = _extract_query_keywords(query)
    if keywords:
        seen_chunk_ids = {c.get("id") for c in vector_chunks}
        kw_chunks = _keyword_supplement_chunks(
            user_id=user_id,
            chat_id=chat_id,
            pool_id=None,
            keywords=keywords,
            limit=max(4, top_k),
            exclude_ids=seen_chunk_ids,
        )
        if kw_chunks:
            logger.info(
                "Hybrid: keyword supplement added %d chunks for keywords %s",
                len(kw_chunks),
                keywords,
            )
            vector_chunks = vector_chunks + kw_chunks

    return vector_chunks


async def retrieve_chunks_with_strategy(
    query: str,
    user_id: str,
    chat_id: Optional[str] = None,
    pool_id: Optional[str] = None,
    intent: str = "fact",
    rerank_settings: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Adaptive retrieval with fallback passes for generic/summary prompts.

    For conversation scope all documents are directly relevant, so we retrieve
    up to 50 chunks with no similarity threshold. This guarantees completeness
    even when specific section headings score poorly in vector space.
    Cohere reranker then selects the best subset.

    Pool/global scope uses threshold-filtered plans (may have many unrelated docs).
    """
    plans: List[Tuple[int, float]]

    if chat_id is not None:
        # Conversation: cast a wide net — retrieve all chunks, let Cohere rank
        plans = [(50, 0.0)]
    elif intent == "summary":
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
        if chat_id is not None:
            chunks = await _search_chunks_hybrid(
                query=query,
                user_id=user_id,
                chat_id=chat_id,
                top_k=top_k,
                threshold=threshold,
            )
        else:
            chunks = await search_similar_chunks(
                query=query,
                user_id=user_id,
                chat_id=None,
                pool_id=pool_id,
                top_k=top_k,
                threshold=threshold,
            )
            # Keyword supplement for pool/global path
            keywords = _extract_query_keywords(query)
            if keywords:
                seen_ids = {c.get("id") for c in chunks}
                kw_chunks = _keyword_supplement_chunks(
                    user_id=user_id,
                    chat_id=None,
                    pool_id=pool_id,
                    keywords=keywords,
                    limit=max(4, top_k),
                    exclude_ids=seen_ids,
                )
                if kw_chunks:
                    logger.info(
                        "Hybrid pool: keyword supplement added %d chunks for keywords %s",
                        len(kw_chunks),
                        keywords,
                    )
                    chunks = chunks + kw_chunks
        logger.info(
            "RAG search: %d chunks found (chat_id=%s, pool_id=%s, threshold=%.2f)",
            len(chunks),
            chat_id,
            pool_id,
            threshold,
        )
        if chunks:
            return await _apply_optional_rerank(query, chunks, rerank_settings)

    logger.warning(
        "RAG: no chunks found for query (chat_id=%s, pool_id=%s)", chat_id, pool_id
    )
    return []


async def _apply_optional_rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    rerank_settings: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    settings = rerank_settings or {}
    enabled = bool(settings.get("rerank_enabled", False))
    if not enabled or not chunks:
        # Without reranking, return all chunks in document order so the LLM
        # reads the document sequentially and no section is skipped. The count
        # is already bounded upstream (conversation: top_k=50, pool: top_k=5).
        return sorted(
            chunks,
            key=lambda c: (c.get("document_id", ""), c.get("chunk_index", 0)),
        )

    candidates = max(5, min(100, int(settings.get("rerank_candidates", 50))))
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


def _rpc_assets(
    embedding: List[float],
    user_id: str,
    chat_id: Optional[str],
    pool_id: Optional[str],
    top_k: int,
    threshold: float,
) -> List[Dict[str, Any]]:
    """Execute match_document_assets RPC with a pre-computed embedding."""
    params: Dict[str, Any] = {
        "query_embedding": str(embedding),
        "match_user_id": user_id,
        "match_threshold": threshold,
        "match_count": top_k,
    }
    if chat_id is not None:
        params["match_chat_id"] = chat_id
    if pool_id is not None:
        params["match_pool_id"] = pool_id
    result = supabase.rpc("match_document_assets", params).execute()
    return result.data or []


async def search_similar_assets(
    query: str,
    user_id: str,
    chat_id: Optional[str] = None,
    pool_id: Optional[str] = None,
    top_k: int = RAG_TOP_K,
    threshold: float = RAG_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Search for similar image assets (if multimodal schema is available).

    For conversation scope (chat_id provided) uses the same two-phase approach
    as chunk retrieval: conversation-specific assets first, global supplement
    if needed.
    """
    try:
        embeddings = await generate_embeddings([query])
        embedding = embeddings[0]

        if chat_id is not None:
            # Phase 1: conversation-specific assets
            conv_assets = _rpc_assets(embedding, user_id, chat_id, None, top_k, threshold)
            if len(conv_assets) >= top_k:
                return conv_assets
            # Phase 2: global supplement
            remaining = top_k - len(conv_assets)
            global_assets = _rpc_assets(embedding, user_id, None, None, remaining, threshold)
            seen = {a["document_id"] for a in conv_assets}
            global_assets = [a for a in global_assets if a["document_id"] not in seen]
            return conv_assets + global_assets[:remaining]

        # Pool or global-only path
        return _rpc_assets(embedding, user_id, chat_id, pool_id, top_k, threshold)

    except Exception as e:
        # Schema might not be migrated yet in some environments.
        logger.info("Image asset retrieval unavailable: %s", e)
        return []


async def rechunk_all_documents(
    progress_callback: Optional[Any] = None,
) -> Dict[str, int]:
    """Re-chunk all existing documents with the current chunker.

    Deletes old chunks from app_document_chunks and re-runs process_document()
    for every document that has extracted_text. Does NOT re-run OCR.

    progress_callback(done, total) is called after each document so callers
    can track live progress (e.g. for a status endpoint).

    Returns a dict with processed / failed / skipped / total counts.
    """
    result = (
        supabase.table("app_documents")
        .select("id, user_id, filename, extracted_text")
        .not_.is_("extracted_text", "null")
        .neq("extracted_text", "")
        .execute()
    )
    docs = result.data or []
    processed = 0
    failed = 0
    skipped = 0

    if progress_callback:
        progress_callback(0, len(docs))

    for doc in docs:
        doc_id = doc["id"]
        text = (doc.get("extracted_text") or "").strip()
        user_id = doc["user_id"]
        filename = doc.get("filename", doc_id)

        if not text:
            skipped += 1
        else:
            try:
                supabase.table("app_document_chunks").delete().eq("document_id", doc_id).execute()
                documents_mod.update_document_status(doc_id, "processing")
                await process_document(doc_id, text, user_id)
                processed += 1
                logger.info("Re-chunked: %s (%s)", filename, doc_id)
            except Exception as e:
                logger.error("Re-chunk failed for %s (%s): %s", filename, doc_id, e, exc_info=True)
                documents_mod.update_document_status(doc_id, "error", error_message=f"Re-chunk: {e}")
                failed += 1

        if progress_callback:
            progress_callback(processed + failed + skipped, len(docs))

    return {"processed": processed, "failed": failed, "skipped": skipped, "total": len(docs)}


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
