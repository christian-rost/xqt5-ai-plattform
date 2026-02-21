-- BM25-style keyword search via PostgreSQL Full-Text Search (ts_rank_cd)
-- Replaces the ILIKE supplement in the hybrid RAG pipeline.
--
-- No extension required — tsvector / GIN / ts_rank_cd are built-in PostgreSQL.
-- The 'german' dictionary handles stemming (Projektleiter → Projektleitung etc.)

-- 1. Computed tsvector column (STORED = persisted on disk, updated on INSERT/UPDATE)
ALTER TABLE app_document_chunks
  ADD COLUMN IF NOT EXISTS content_fts tsvector
    GENERATED ALWAYS AS (
      to_tsvector('german', coalesce(content, ''))
    ) STORED;

-- 2. GIN index for fast FTS queries
CREATE INDEX IF NOT EXISTS idx_doc_chunks_content_fts
  ON app_document_chunks USING GIN (content_fts);

-- 3. Drop old signature if it exists (prevents PGRST203 overload ambiguity)
DROP FUNCTION IF EXISTS keyword_search_chunks(text, uuid, int, uuid, uuid);

-- 4. Scope-isolated keyword search RPC (mirrors match_document_chunks scoping)
--    Scopes:
--      match_pool_id IS NOT NULL  → pool documents only
--      match_chat_id IS NOT NULL  → conversation documents only
--      both NULL                  → user's global documents (no pool, no chat)
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
  bm25_score   FLOAT
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
    ts_rank_cd(c.content_fts, q.query, 32)::FLOAT AS bm25_score
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
