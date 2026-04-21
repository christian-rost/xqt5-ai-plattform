-- ==================== 20260214_initial_schema.sql ====================
-- Initial schema for XQT5 AI Plattform
-- Apply in Supabase SQL editor or via supabase migration tooling

create extension if not exists pgcrypto;

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    username varchar(32) unique not null,
    email varchar(255) unique not null,
    password_hash text not null,
    is_active boolean default true,
    is_admin boolean default false,
    created_at timestamptz default now()
);

create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references users(id) on delete cascade,
    title varchar(255) default 'New Conversation',
    created_at timestamptz default now()
);

create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    role varchar(10) not null check (role in ('user', 'assistant')),
    content text,
    stage1 jsonb,
    stage2 jsonb,
    stage3 jsonb,
    metadata jsonb,
    created_at timestamptz default now()
);

create index if not exists idx_messages_conversation on messages(conversation_id, created_at);
create index if not exists idx_conversations_user on conversations(user_id, created_at desc);

create table if not exists app_settings (
    key varchar(100) primary key,
    value jsonb not null,
    updated_at timestamptz default now()
);

insert into app_settings (key, value)
values
  ('default_model', '"google/gemini-3-pro-preview"'),
  ('model_set', '["openai/gpt-5.1","google/gemini-3-pro-preview","anthropic/claude-sonnet-4.5","x-ai/grok-4"]')
on conflict (key) do nothing;

create table if not exists api_keys (
    id uuid primary key default gen_random_uuid(),
    name varchar(100) not null,
    key_hash text not null,
    key_prefix varchar(16) not null,
    is_active boolean default true,
    rate_limit integer default 5,
    usage_count integer default 0,
    created_at timestamptz default now(),
    last_used_at timestamptz
);

create index if not exists idx_api_keys_prefix on api_keys(key_prefix);

create table if not exists provider_api_keys (
    provider varchar(50) primary key,
    api_key_encrypted text not null,
    is_active boolean default true,
    updated_at timestamptz default now()
);

create table if not exists token_usage (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    message_id uuid references messages(id) on delete cascade,
    user_id uuid references users(id) on delete set null,
    api_key_id uuid,
    source varchar(10) default 'chat' check (source in ('chat', 'api')),
    model varchar(100) not null,
    provider varchar(50) not null,
    stage varchar(10) not null check (stage in ('stage1', 'stage2', 'stage3', 'title')),
    prompt_tokens integer default 0,
    completion_tokens integer default 0,
    total_tokens integer default 0,
    estimated_cost_usd decimal(10, 6),
    cached_tokens integer default 0,
    created_at timestamptz default now()
);

create index if not exists idx_token_usage_conversation on token_usage(conversation_id);
create index if not exists idx_token_usage_created on token_usage(created_at);
create index if not exists idx_token_usage_provider on token_usage(provider, created_at);

-- ==================== 20260215_phase_a_model_temperature.sql ====================
-- Phase A: Own tables for direct LLM chat (separate from llm-council pipeline)

create table if not exists chats (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references users(id) on delete cascade,
    title varchar(255) default 'New Conversation',
    model varchar(100) default 'google/gemini-3-pro-preview',
    temperature decimal(3,2) default 0.70,
    created_at timestamptz default now()
);

create index if not exists idx_chats_user on chats(user_id, created_at desc);

create table if not exists chat_messages (
    id uuid primary key default gen_random_uuid(),
    chat_id uuid references chats(id) on delete cascade not null,
    role varchar(10) not null check (role in ('user', 'assistant')),
    content text not null,
    model varchar(100),
    created_at timestamptz default now()
);

create index if not exists idx_chat_messages_chat on chat_messages(chat_id, created_at);

-- ==================== 20260215_phase_b_auth_token_tracking.sql ====================
-- Phase B: Auth & Token Tracking
-- Own table for token usage (not llm-council's token_usage)

create table if not exists chat_token_usage (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    chat_id uuid references chats(id) on delete set null,
    model varchar(100) not null,
    provider varchar(50) not null,
    prompt_tokens int not null default 0,
    completion_tokens int not null default 0,
    total_tokens int not null default 0,
    estimated_cost decimal(12,6) not null default 0,
    created_at timestamptz default now()
);

create index idx_chat_token_usage_user on chat_token_usage(user_id);
create index idx_chat_token_usage_created on chat_token_usage(created_at);

-- ==================== 20260215_phase_b_own_users_table.sql ====================
-- Phase B: Own users table (separate from llm-council's users table)

create table if not exists app_users (
    id uuid primary key default gen_random_uuid(),
    username varchar(32) unique not null,
    email varchar(255) unique not null,
    password_hash text not null,
    is_active boolean default true,
    is_admin boolean default false,
    created_at timestamptz default now()
);

-- Remove FK from chats -> users, add FK to app_users
alter table chats drop constraint if exists chats_user_id_fkey;
alter table chats add constraint chats_user_id_fkey foreign key (user_id) references app_users(id) on delete cascade;

-- Remove FK from chat_token_usage -> users, add FK to app_users
alter table chat_token_usage drop constraint if exists chat_token_usage_user_id_fkey;
alter table chat_token_usage add constraint chat_token_usage_user_id_fkey foreign key (user_id) references app_users(id) on delete cascade;

-- ==================== 20260216_phase_c_assistants_templates.sql ====================
-- Phase C: Assistants & Prompt Templates
-- XQT5 AI Plattform eigene Tabellen (KEINE shared Tabellen!)

-- Assistants table
CREATE TABLE assistants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT DEFAULT '',
  system_prompt TEXT NOT NULL,
  model VARCHAR(100),
  temperature FLOAT,
  is_global BOOLEAN DEFAULT FALSE,
  icon VARCHAR(10) DEFAULT '🤖',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_assistants_user ON assistants(user_id);

-- Prompt templates table
CREATE TABLE prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT DEFAULT '',
  content TEXT NOT NULL,
  category VARCHAR(50) DEFAULT 'general',
  is_global BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_templates_user ON prompt_templates(user_id);

-- Link chats to assistants
ALTER TABLE chats ADD COLUMN assistant_id UUID REFERENCES assistants(id) ON DELETE SET NULL;

-- ==================== 20260216_phase_c_rag.sql ====================
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

-- ==================== 20260216_phase_d_admin_audit.sql ====================
-- Phase D: Admin-Dashboard + Audit-Logs
-- Schritt 1: app_model_config + app_audit_logs

-- ── Model Configuration Table ──
CREATE TABLE app_model_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_id VARCHAR(100) NOT NULL UNIQUE,
  provider VARCHAR(50) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  is_enabled BOOLEAN DEFAULT TRUE,
  is_default BOOLEAN DEFAULT FALSE,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with current 9 models from llm.py
INSERT INTO app_model_config (model_id, provider, display_name, is_enabled, is_default, sort_order) VALUES
  ('openai/gpt-5.1',              'openai',    'GPT-5.1',            TRUE, FALSE, 1),
  ('openai/gpt-4.1',              'openai',    'GPT-4.1',            TRUE, FALSE, 2),
  ('openai/gpt-4.1-mini',         'openai',    'GPT-4.1 Mini',      TRUE, FALSE, 3),
  ('anthropic/claude-sonnet-4-5',  'anthropic', 'Claude Sonnet 4.5', TRUE, FALSE, 4),
  ('anthropic/claude-haiku-3-5',   'anthropic', 'Claude Haiku 3.5',  TRUE, FALSE, 5),
  ('google/gemini-3-pro-preview',  'google',    'Gemini 3 Pro',      TRUE, TRUE,  6),
  ('google/gemini-2.5-flash',      'google',    'Gemini 2.5 Flash',  TRUE, FALSE, 7),
  ('mistral/mistral-large-latest', 'mistral',   'Mistral Large',     TRUE, FALSE, 8),
  ('x-ai/grok-4',                  'x-ai',      'Grok 4',           TRUE, FALSE, 9);

-- ── Audit Logs Table ──
CREATE TABLE app_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
  action VARCHAR(100) NOT NULL,
  target_type VARCHAR(50),
  target_id UUID,
  metadata JSONB DEFAULT '{}',
  ip_address VARCHAR(45),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON app_audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON app_audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON app_audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_target ON app_audit_logs(target_type, target_id);

-- ==================== 20260216_phase_d_provider_keys.sql ====================
-- Phase D: Provider API Keys (DB-managed)
CREATE TABLE IF NOT EXISTS app_provider_keys (
  provider VARCHAR(50) PRIMARY KEY,
  api_key_encrypted TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== 20260216_phase_d_azure_provider.sql ====================
-- Azure OpenAI provider support: additional columns for endpoint_url, api_version, deployment_name

ALTER TABLE app_provider_keys
  ADD COLUMN IF NOT EXISTS endpoint_url TEXT,
  ADD COLUMN IF NOT EXISTS api_version VARCHAR(50);

ALTER TABLE app_model_config
  ADD COLUMN IF NOT EXISTS deployment_name VARCHAR(100);

-- ==================== 20260217_phase_d_token_version_revocation.sql ====================
-- Phase D Security: Token versioning for immediate session invalidation

ALTER TABLE app_users
  ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;

-- ==================== 20260218_pools.sql ====================
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

-- ==================== 20260219_drop_old_function_overloads.sql ====================
-- Drop old overloaded function signatures that conflict with the new
-- scope-isolated versions added in 20260221_rag_scoped_search.sql.
--
-- PostgreSQL allows function overloading, but PostgREST (PGRST203) cannot
-- resolve the ambiguity when both signatures match the supplied parameters.
-- Dropping the old 5-parameter variants removes the ambiguity.

-- Old match_document_chunks: (vector, uuid, uuid, float, int) — no pool_id
DROP FUNCTION IF EXISTS match_document_chunks(
    vector(1536), UUID, UUID, FLOAT, INT
);

-- Old match_document_assets: (vector, uuid, uuid, float, int) — no pool_id
DROP FUNCTION IF EXISTS match_document_assets(
    vector(1536), UUID, UUID, FLOAT, INT
);

-- ==================== 20260219_phase_f_multimodal_assets.sql ====================
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

-- ==================== 20260220_runtime_rag_settings.sql ====================
-- Runtime configuration for admin-managed feature flags and retrieval tuning

CREATE TABLE IF NOT EXISTS app_runtime_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO app_runtime_config (key, value)
VALUES (
    'rag_settings',
    '{
      "rerank_enabled": false,
      "rerank_candidates": 20,
      "rerank_top_n": 6,
      "rerank_model": "rerank-v3.5"
    }'::jsonb
)
ON CONFLICT (key) DO NOTHING;

-- ==================== 20260221_rag_scoped_search.sql ====================
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

-- ==================== 20260222_bm25_fts.sql ====================
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

-- ==================== 20260223_chunk_page_number.sql ====================
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

-- ==================== 20260224_embedding_provider_setting.sql ====================
-- Add embedding_provider and embedding_deployment fields to rag_settings.
-- No schema change needed — app_runtime_config.value is already JSONB.
-- This migration patches the existing row (if any) to include the new keys.

UPDATE app_runtime_config
SET value = value || '{"embedding_provider": "openai", "embedding_deployment": ""}'::jsonb
WHERE key = 'rag_settings';

-- ==================== 20260225_document_summary.sql ====================
-- Add LLM-generated summary column to app_documents.
-- Populated automatically on upload; NULL for documents uploaded before this feature.

ALTER TABLE app_documents ADD COLUMN IF NOT EXISTS summary TEXT;

-- ==================== 20260226_rag_sources_persistence.sql ====================
-- RAG sources persistence
-- Stores rag_sources (filename, excerpt, page_number, ...) as JSONB
-- so citations survive page navigation / session reload.

ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS rag_sources JSONB;

ALTER TABLE pool_chat_messages
    ADD COLUMN IF NOT EXISTS rag_sources JSONB;

