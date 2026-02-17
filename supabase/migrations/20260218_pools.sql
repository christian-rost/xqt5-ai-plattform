-- Pools: Shared Document Collections with RAG
-- New tables for pool management, membership, invite links, and pool chats.

-- Pool metadata
CREATE TABLE IF NOT EXISTS pool_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    icon TEXT DEFAULT '📚',
    color TEXT DEFAULT '#ee7f00',
    owner_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pool_pools_owner ON pool_pools(owner_id);

-- Pool members (owner is NOT stored here — implicit via pool_pools.owner_id)
CREATE TABLE IF NOT EXISTS pool_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID NOT NULL REFERENCES pool_pools(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(pool_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_pool_members_pool ON pool_members(pool_id);
CREATE INDEX IF NOT EXISTS idx_pool_members_user ON pool_members(user_id);

-- Invite links for sharing pools
CREATE TABLE IF NOT EXISTS pool_invite_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID NOT NULL REFERENCES pool_pools(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(24), 'hex'),
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'editor', 'admin')),
    max_uses INTEGER,  -- NULL = unlimited
    use_count INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ,  -- NULL = never expires
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pool_invite_links_pool ON pool_invite_links(pool_id);
CREATE INDEX IF NOT EXISTS idx_pool_invite_links_token ON pool_invite_links(token);

-- Pool chats
CREATE TABLE IF NOT EXISTS pool_chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID NOT NULL REFERENCES pool_pools(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Chat',
    is_shared BOOLEAN NOT NULL DEFAULT false,
    created_by UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    model TEXT,
    temperature FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pool_chats_pool ON pool_chats(pool_id);
CREATE INDEX IF NOT EXISTS idx_pool_chats_created_by ON pool_chats(created_by);

-- Pool chat messages
CREATE TABLE IF NOT EXISTS pool_chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL REFERENCES pool_chats(id) ON DELETE CASCADE,
    user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL DEFAULT '',
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pool_chat_messages_chat ON pool_chat_messages(chat_id);

-- Extend app_documents: add pool_id column
ALTER TABLE app_documents ADD COLUMN IF NOT EXISTS pool_id UUID REFERENCES pool_pools(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_app_documents_pool_id ON app_documents(pool_id);

-- Update the match_document_chunks RPC to support pool_id
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
    ELSE
        -- User-scoped search (original behavior)
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
          AND (
              d.chat_id = match_chat_id
              OR d.chat_id IS NULL
          )
          AND 1 - (c.embedding <=> query_embedding) > match_threshold
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count;
    END IF;
END;
$$;
