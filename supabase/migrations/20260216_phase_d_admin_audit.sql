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
