-- Image pHash dedup for OCR-extracted figures.
--
-- Same logo or header repeats on every page of a multi-page PDF — the
-- previous behavior stored each occurrence as a separate asset row, which
-- pollutes RAG retrieval with N copies of the same logo. This migration
-- adds a perceptual-hash column and a "recurring" flag so the ingest
-- pipeline can mark same-document duplicates and the asset-search RPC
-- can filter them out.
--
-- Per-document scope only for now. Cross-document dedup is future work
-- (would need either a tenant-scoped phash index or a canonical-asset table).
--
-- Row-level access control is unchanged: anon and authenticated were
-- already revoked from the entire `public` schema in 20260506_b_* and
-- 20260507_*. Service-role keeps full access for the backend.

ALTER TABLE app_document_assets ADD COLUMN IF NOT EXISTS phash TEXT;
ALTER TABLE app_document_assets ADD COLUMN IF NOT EXISTS recurring BOOLEAN NOT NULL DEFAULT FALSE;

-- Speeds within-document phash lookups (e.g. future "any prior asset with
-- this hash already canonical?" queries). Partial index — rows without a
-- phash (e.g. upload_image rows from create_document_asset) skip indexing.
CREATE INDEX IF NOT EXISTS idx_app_document_assets_doc_phash
    ON app_document_assets(document_id, phash) WHERE phash IS NOT NULL;

-- Recreate match_document_assets with `AND a.recurring = FALSE` injected
-- into all three branches. Signature is unchanged from
-- 20260221_rag_scoped_search.sql so CREATE OR REPLACE is safe and any
-- caller using the old signature continues to work.
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
          AND a.recurring = FALSE
          AND 1 - (a.embedding <=> query_embedding) > match_threshold
        ORDER BY a.embedding <=> query_embedding
        LIMIT match_count;

    ELSIF match_chat_id IS NOT NULL THEN
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
          AND a.recurring = FALSE
          AND 1 - (a.embedding <=> query_embedding) > match_threshold
        ORDER BY a.embedding <=> query_embedding
        LIMIT match_count;

    ELSE
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
          AND a.recurring = FALSE
          AND 1 - (a.embedding <=> query_embedding) > match_threshold
        ORDER BY a.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;
