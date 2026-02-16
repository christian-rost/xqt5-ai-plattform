-- Phase C: Assistants & Prompt Templates
-- XQT5 AI Plattform eigene Tabellen (KEINE shared Tabellen!)

-- Assistants table
CREATE TABLE assistants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT DEFAULT '',
  system_prompt TEXT NOT NULL,
  model VARCHAR(100),
  temperature FLOAT,
  is_global BOOLEAN DEFAULT FALSE,
  icon VARCHAR(10) DEFAULT '🤖',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_assistants_user ON assistants(user_id);

-- Prompt templates table
CREATE TABLE prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT DEFAULT '',
  content TEXT NOT NULL,
  category VARCHAR(50) DEFAULT 'general',
  is_global BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_templates_user ON prompt_templates(user_id);

-- Link chats to assistants
ALTER TABLE chats ADD COLUMN assistant_id UUID REFERENCES assistants(id) ON DELETE SET NULL;
