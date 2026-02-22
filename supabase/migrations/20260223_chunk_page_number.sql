-- Add page_number to app_document_chunks
-- Populated during OCR re-chunking from <!-- page:N --> markers in extracted markdown.
ALTER TABLE app_document_chunks ADD COLUMN IF NOT EXISTS page_number integer;

-- Update match_document_chunks to return page_number.
-- PostgreSQL requires DROP when RETURNS TABLE columns change (even if parameters are unchanged).
DROP FUNCTION IF EXISTS match_document_chunks(vector,uuid,uuid,uuid,double precision,integer);
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
    similarity FLOAT,
    page_number INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF match_pool_id IS NOT NULL THEN
        RETURN QUERY
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.token_count,
            d.filename,
            1 - (c.embedding <=> query_embedding) AS similarity,
            c.page_number
        FROM app_document_chunks c
        JOIN app_documents d ON d.id = c.document_id
        WHERE d.pool_id = match_pool_id
          AND d.status = 'ready'
          AND 1 - (c.embedding <=> query_embedding) > match_threshold
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count;

    ELSIF match_chat_id IS NOT NULL THEN
        RETURN QUERY
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.token_count,
            d.filename,
            1 - (c.embedding <=> query_embedding) AS similarity,
            c.page_number
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
        RETURN QUERY
        SELECT
            c.id,
            c.document_id,
            c.chunk_index,
            c.content,
            c.token_count,
            d.filename,
            1 - (c.embedding <=> query_embedding) AS similarity,
            c.page_number
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


-- Update keyword_search_chunks to return page_number.
-- Same reason: DROP required when RETURNS TABLE columns change.
DROP FUNCTION IF EXISTS keyword_search_chunks(text,uuid,integer,uuid,uuid);
CREATE OR REPLACE FUNCTION keyword_search_chunks(
  query_text       TEXT,
  match_user_id    UUID,
  match_count      INT  DEFAULT 10,
  match_chat_id    UUID DEFAULT NULL,
  match_pool_id    UUID DEFAULT NULL
)
RETURNS TABLE (
  id           UUID,
  document_id  UUID,
  chunk_index  INT,
  content      TEXT,
  token_count  INT,
  filename     TEXT,
  bm25_score   FLOAT,
  page_number  INT
)
LANGUAGE sql STABLE AS $$
  WITH q AS (
    SELECT websearch_to_tsquery('german', query_text) AS query
  )
  SELECT
    c.id,
    c.document_id,
    c.chunk_index,
    c.content,
    c.token_count,
    d.filename,
    ts_rank_cd(c.content_fts, q.query, 32)::FLOAT AS bm25_score,
    c.page_number
  FROM app_document_chunks c
  JOIN app_documents d ON d.id = c.document_id
  CROSS JOIN q
  WHERE
    c.content_fts @@ q.query
    AND d.status = 'ready'
    AND (
      CASE
        WHEN match_pool_id IS NOT NULL
          THEN d.pool_id = match_pool_id
        WHEN match_chat_id IS NOT NULL
          THEN d.user_id = match_user_id
           AND d.pool_id IS NULL
           AND d.chat_id = match_chat_id
        ELSE
               d.user_id = match_user_id
           AND d.pool_id IS NULL
           AND d.chat_id IS NULL
      END
    )
  ORDER BY bm25_score DESC
  LIMIT match_count;
$$;
