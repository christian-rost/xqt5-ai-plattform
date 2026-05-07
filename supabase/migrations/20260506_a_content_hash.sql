-- Content-hash dedup on document upload.
-- Stores SHA-256 hex of the original file bytes so a re-upload of the same
-- file (within the same scope) can short-circuit OCR + embedding.

ALTER TABLE app_documents ADD COLUMN IF NOT EXISTS content_hash TEXT;

-- Partial composite indexes — speed the dedup-check queries done in app code.
-- Scope is per-pool when uploading into a pool, per-user (with pool_id IS NULL)
-- otherwise. Keeping these as separate non-unique indexes avoids a UNIQUE
-- constraint that would have to encode that scope rule across nullable columns.
CREATE INDEX IF NOT EXISTS idx_app_documents_pool_hash
    ON app_documents(pool_id, content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_app_documents_user_hash
    ON app_documents(user_id, content_hash) WHERE content_hash IS NOT NULL;
