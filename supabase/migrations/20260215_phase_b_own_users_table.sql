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
