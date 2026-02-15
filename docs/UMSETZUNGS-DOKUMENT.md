# Umsetzungs-Dokument

## Zielarchitektur
1. Frontend-Service (React/Vite, statisch via Nginx)
2. Backend-Service (FastAPI/Uvicorn)
3. Supabase (Postgres) als zentrale Datenbank
4. Coolify als Orchestrierungs- und Deployment-Ebene

## Technische Entscheidungen
1. Trennung in zwei Container für unabhängige Deployments und Skalierung
2. Supabase als Managed Postgres für schnelle Time-to-Market
3. FastAPI wegen guter API-Performance und klarer Pydantic-Validierung
4. React/Vite wegen schneller Build- und Dev-Zyklen
5. Externe Kopplung zu `llm-council` nur per HTTP-API, keine Funktions- oder Codeübernahme

## Implementierte Artefakte

### MVP (Phase 0 — 2026-02-14)
1. Backend-Grundstruktur unter `backend/app`
2. Frontend-Grundstruktur unter `frontend/src`
3. Container-Builds: `backend/Dockerfile`, `frontend/Dockerfile`
4. Supabase-Migration: `supabase/migrations/20260214_initial_schema.sql`
5. Env-Vorlage: `.env.example`

### Phase A: Core Chat Enhancement (2026-02-15)
1. **LLM Provider Modul** (`backend/app/llm.py`):
   - Multi-Provider Support: OpenAI, Anthropic, Google Gemini, Mistral, X.AI
   - Streaming (SSE) und Non-Streaming Calls via `httpx.AsyncClient`
   - Anthropic-Sonderbehandlung (anderes Request-Format)
   - `LLMError` Exception-Klasse für einheitliche Fehlerbehandlung
2. **Eigene Chat-Tabellen** (getrennt von llm-council):
   - `chats` (id, user_id, title, model, temperature, created_at)
   - `chat_messages` (id, chat_id, role, content, model, created_at)
   - Migration: `supabase/migrations/20260215_phase_a_model_temperature.sql`
3. **Backend Endpoints**:
   - `GET /api/models` — Verfügbare Modelle mit Availability-Status
   - `PATCH /api/conversations/{id}` — Conversation Settings updaten
   - `POST /api/conversations/{id}/message` — Erweitert: stream, model, temperature
   - SSE-Streaming mit Coolify-kompatiblen Headers (`X-Accel-Buffering: no`)
   - Auto-Benennung nach erster Nachricht (Background-Task, silent fail)
4. **Frontend Component-Architektur** (`frontend/src/components/`):
   - Sidebar, ChatArea, MessageBubble, MessageInput, ModelSelector, TemperatureSlider, Welcome
   - SSE-Stream-Parsing mit optimistischem Rendering
   - Markdown-Rendering für Assistant-Nachrichten (`react-markdown`)
   - Model-Dropdown und Temperature-Slider
5. **Config**: `DEFAULT_MODEL`, `DEFAULT_TEMPERATURE` in docker-compose.coolify.yml

## Datenbank-Schema-Übersicht

| Tabelle | Zugehörigkeit | Beschreibung |
|---------|---------------|--------------|
| `users` | Shared | Benutzer mit is_admin Flag |
| `conversations` | llm-council | Pipeline-Konversationen (stage1/2/3) |
| `messages` | llm-council | Pipeline-Nachrichten (stage1/2/3, metadata) |
| `token_usage` | llm-council | Token-Verbrauch pro Pipeline-Stage |
| `app_settings` | Shared | Globale Einstellungen |
| `api_keys` | Shared | API-Key-Verwaltung |
| `provider_api_keys` | Shared | Verschlüsselte Provider-Keys |
| `chats` | Direct Chat | Direkte Chat-Konversationen mit model/temperature |
| `chat_messages` | Direct Chat | Chat-Nachrichten (clean, ohne Pipeline-Felder) |

## Coolify Setup-Schritte
1. Repo in Coolify verbinden
2. Backend-Service erstellen:
   - Build Context: `backend`, Dockerfile: `backend/Dockerfile`
   - Domain: `api.xqtfive.com`
   - Env: `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET`, `CORS_ORIGINS`
   - Provider Keys: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
   - Defaults: `DEFAULT_MODEL`, `DEFAULT_TEMPERATURE`
3. Frontend-Service erstellen:
   - Build Context: `frontend`, Dockerfile: `frontend/Dockerfile`
   - Domain: `ai-hub.xqtfive.com`
   - Build-Arg: `VITE_API_BASE=https://api.xqtfive.com`
4. `CORS_ORIGINS` im Backend auf Frontend-Domain setzen
5. Supabase-Migrationen ausführen (initial + phase_a)

## Nächste Umsetzungsschritte
1. **Phase B**: Auth (Register/Login/JWT), User/Gruppen-Verwaltung, Token-Tracking, Kosten-Dashboard
2. **Phase C**: Datei-Upload, RAG-Pipeline, KI-Assistenten, Prompt-Templates
3. **Phase D**: Admin-Dashboard, Workflow-Engine, Audit-Logs, SSO
4. RLS und Mandantenmodell in Supabase aktivieren
5. Integrationstests für API und End-to-End-Chat
