-- Add LLM-generated summary column to app_documents.
-- Populated automatically on upload; NULL for documents uploaded before this feature.

ALTER TABLE app_documents ADD COLUMN IF NOT EXISTS summary TEXT;
