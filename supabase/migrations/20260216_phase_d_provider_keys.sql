-- Phase D: Provider API Keys (DB-managed)
CREATE TABLE IF NOT EXISTS app_provider_keys (
  provider VARCHAR(50) PRIMARY KEY,
  api_key_encrypted TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
