-- Phase C Step 2: RAG Pipeline — Documents + Chunks with pgvector

CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS app_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,  -- NULL = global knowledge base
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    extracted_text TEXT,
    chunk_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'processing',  -- processing | ready | error
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Document chunks with embeddings
CREATE TABLE IF NOT EXISTS app_document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES app_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON app_document_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_app_documents_user_id ON app_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_app_documents_chat_id ON app_documents(chat_id);
CREATE INDEX IF NOT EXISTS idx_app_document_chunks_document_id ON app_document_chunks(document_id);

-- RPC: Search similar chunks for a user (chat-specific + global docs)
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(1536),
    match_user_id UUID,
    match_chat_id UUID DEFAULT NULL,
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
      AND (
          d.chat_id = match_chat_id  -- chat-specific docs
          OR d.chat_id IS NULL       -- global knowledge base
      )
      AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
