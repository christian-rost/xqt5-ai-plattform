-- Scope-isolated RAG search for conversations vs global documents
--
-- Previously, match_document_chunks with match_chat_id=<uuid> returned
-- BOTH conversation-specific AND global (chat_id IS NULL) chunks, which
-- caused global documents to dilute or replace relevant conversation chunks.
--
-- New behaviour:
--   match_pool_id IS NOT NULL  → pool-only (unchanged)
--   match_chat_id IS NOT NULL  → conversation-specific ONLY (no global)
--   both NULL                  → global-only (chat_id IS NULL)
--
-- Python code in rag.py implements a two-phase search:
--   Phase 1: conversation-specific (match_chat_id = <uuid>)
--   Phase 2: supplement with global if Phase 1 returned < top_k chunks

CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(1536),
    match_user_id UUID,
    match_chat_id UUID DEFAULT NULL,
    match_pool_id UUID DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INT,
    content TEXT,
    token_count INT,
    filename TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF match_pool_id IS NOT NULL THEN
        -- Pool-scoped search: only documents belonging to the pool
        RETURN QUERY
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.token_count,
            d.filename,
            1 - (c.embedding <=> query_embedding) AS similarity
        FROM app_document_chunks c
        JOIN app_documents d ON d.id = c.document_id
        WHERE d.pool_id = match_pool_id
          AND d.status = 'ready'
          AND 1 - (c.embedding <=> query_embedding) > match_threshold
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count;

    ELSIF match_chat_id IS NOT NULL THEN
        -- Conversation-specific ONLY: no global documents
        RETURN QUERY
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.token_count,
            d.filename,
            1 - (c.embedding <=> query_embedding) AS similarity
        FROM app_document_chunks c
        JOIN app_documents d ON d.id = c.document_id
        WHERE d.user_id = match_user_id
          AND d.status = 'ready'
          AND d.pool_id IS NULL
          AND d.chat_id = match_chat_id
          AND 1 - (c.embedding <=> query_embedding) > match_threshold
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count;

    ELSE
        -- Global-only: documents without a conversation or pool scope
        RETURN QUERY
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.token_count,
            d.filename,
            1 - (c.embedding <=> query_embedding) AS similarity
        FROM app_document_chunks c
        JOIN app_documents d ON d.id = c.document_id
        WHERE d.user_id = match_user_id
          AND d.status = 'ready'
          AND d.pool_id IS NULL
          AND d.chat_id IS NULL
          AND 1 - (c.embedding <=> query_embedding) > match_threshold
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;


-- Same scope-isolation for image assets

CREATE OR REPLACE FUNCTION match_document_assets(
    query_embedding vector(1536),
    match_user_id UUID,
    match_chat_id UUID DEFAULT NULL,
    match_pool_id UUID DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    asset_id UUID,
    document_id UUID,
    filename TEXT,
    page_number INT,
    storage_path TEXT,
    caption TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF match_pool_id IS NOT NULL THEN
        RETURN QUERY
        SELECT
            a.id AS asset_id,
            a.document_id,
            d.filename,
            a.page_number,
            a.storage_path,
            a.caption,
            1 - (a.embedding <=> query_embedding) AS similarity
        FROM app_document_assets a
        JOIN app_documents d ON d.id = a.document_id
        WHERE d.pool_id = match_pool_id
          AND d.status = 'ready'
          AND a.embedding IS NOT NULL
          AND 1 - (a.embedding <=> query_embedding) > match_threshold
        ORDER BY a.embedding <=> query_embedding
        LIMIT match_count;

    ELSIF match_chat_id IS NOT NULL THEN
        -- Conversation-specific ONLY
        RETURN QUERY
        SELECT
            a.id AS asset_id,
            a.document_id,
            d.filename,
            a.page_number,
            a.storage_path,
            a.caption,
            1 - (a.embedding <=> query_embedding) AS similarity
        FROM app_document_assets a
        JOIN app_documents d ON d.id = a.document_id
        WHERE d.user_id = match_user_id
          AND d.pool_id IS NULL
          AND d.status = 'ready'
          AND d.chat_id = match_chat_id
          AND a.embedding IS NOT NULL
          AND 1 - (a.embedding <=> query_embedding) > match_threshold
        ORDER BY a.embedding <=> query_embedding
        LIMIT match_count;

    ELSE
        -- Global-only
        RETURN QUERY
        SELECT
            a.id AS asset_id,
            a.document_id,
            d.filename,
            a.page_number,
            a.storage_path,
            a.caption,
            1 - (a.embedding <=> query_embedding) AS similarity
        FROM app_document_assets a
        JOIN app_documents d ON d.id = a.document_id
        WHERE d.user_id = match_user_id
          AND d.pool_id IS NULL
          AND d.status = 'ready'
          AND d.chat_id IS NULL
          AND a.embedding IS NOT NULL
          AND 1 - (a.embedding <=> query_embedding) > match_threshold
        ORDER BY a.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;
