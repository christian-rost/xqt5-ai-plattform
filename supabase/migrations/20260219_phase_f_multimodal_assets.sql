-- Phase F: Multimodal assets for image-grounded RAG

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS app_document_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES app_documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    pool_id UUID REFERENCES pool_pools(id) ON DELETE CASCADE,
    page_number INTEGER,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('page_image', 'embedded_image', 'upload_image')),
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT 'image/png',
    width INTEGER,
    height INTEGER,
    caption TEXT,
    ocr_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_app_document_assets_document_id ON app_document_assets(document_id);
CREATE INDEX IF NOT EXISTS idx_app_document_assets_user_id ON app_document_assets(user_id);
CREATE INDEX IF NOT EXISTS idx_app_document_assets_pool_id ON app_document_assets(pool_id);
CREATE INDEX IF NOT EXISTS idx_app_document_assets_embedding
    ON app_document_assets USING hnsw (embedding vector_cosine_ops);

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
          AND (
              d.chat_id = match_chat_id
              OR d.chat_id IS NULL
          )
          AND a.embedding IS NOT NULL
          AND 1 - (a.embedding <=> query_embedding) > match_threshold
        ORDER BY a.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;
