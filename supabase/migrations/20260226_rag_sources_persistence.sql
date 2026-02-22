-- RAG sources persistence
-- Stores rag_sources (filename, excerpt, page_number, ...) as JSONB
-- so citations survive page navigation / session reload.

ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS rag_sources JSONB;

ALTER TABLE pool_chat_messages
    ADD COLUMN IF NOT EXISTS rag_sources JSONB;
