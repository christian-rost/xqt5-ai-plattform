-- Phase D Security: Token versioning for immediate session invalidation

ALTER TABLE app_users
  ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;
