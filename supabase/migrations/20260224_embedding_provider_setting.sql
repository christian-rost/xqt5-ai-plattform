-- Add embedding_provider and embedding_deployment fields to rag_settings.
-- No schema change needed — app_runtime_config.value is already JSONB.
-- This migration patches the existing row (if any) to include the new keys.

UPDATE app_runtime_config
SET value = value || '{"embedding_provider": "openai", "embedding_deployment": ""}'::jsonb
WHERE key = 'rag_settings';
