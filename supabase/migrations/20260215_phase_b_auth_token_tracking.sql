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
