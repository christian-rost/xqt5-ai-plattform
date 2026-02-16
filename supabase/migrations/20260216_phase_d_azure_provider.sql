-- Azure OpenAI provider support: additional columns for endpoint_url, api_version, deployment_name

ALTER TABLE app_provider_keys
  ADD COLUMN IF NOT EXISTS endpoint_url TEXT,
  ADD COLUMN IF NOT EXISTS api_version VARCHAR(50);

ALTER TABLE app_model_config
  ADD COLUMN IF NOT EXISTS deployment_name VARCHAR(100);
