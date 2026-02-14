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
