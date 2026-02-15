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
