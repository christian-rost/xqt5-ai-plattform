-- Runtime configuration for admin-managed feature flags and retrieval tuning

CREATE TABLE IF NOT EXISTS app_runtime_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO app_runtime_config (key, value)
VALUES (
    'rag_settings',
    '{
      "rerank_enabled": false,
      "rerank_candidates": 20,
      "rerank_top_n": 6,
      "rerank_model": "rerank-v3.5"
    }'::jsonb
)
ON CONFLICT (key) DO NOTHING;
