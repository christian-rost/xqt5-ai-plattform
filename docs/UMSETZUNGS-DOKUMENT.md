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

**KEINE shared Tabellen — jede Anwendung nutzt nur eigene Tabellen.**

| Tabelle | Zugehörigkeit | Beschreibung |
|---------|---------------|--------------|
| `app_users` | XQT5 AI Plattform | Eigene Benutzer mit is_admin Flag |
| `chats` | XQT5 AI Plattform | Chat-Konversationen mit model/temperature/assistant_id |
| `chat_messages` | XQT5 AI Plattform | Chat-Nachrichten (clean, ohne Pipeline-Felder) |
| `chat_token_usage` | XQT5 AI Plattform | Token-Verbrauch + Kosten pro Anfrage |
| `assistants` | XQT5 AI Plattform | KI-Assistenten mit System-Prompts |
| `prompt_templates` | XQT5 AI Plattform | Prompt-Templates mit Platzhaltern |
| `users` | llm-council | Pipeline-Benutzer (nicht anfassen!) |
| `conversations` | llm-council | Pipeline-Konversationen (stage1/2/3) |
| `messages` | llm-council | Pipeline-Nachrichten (stage1/2/3, metadata) |
| `token_usage` | llm-council | Token-Verbrauch pro Pipeline-Stage |
| `app_settings` | llm-council | Globale Einstellungen |
| `api_keys` | llm-council | API-Key-Verwaltung |
| `provider_api_keys` | llm-council | Verschlüsselte Provider-Keys |

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
5. Supabase-Migrationen ausführen (initial + phase_a + phase_b)

### Phase B: User & Kosten-Management (2026-02-15)
1. **Eigene User-Tabelle** (`app_users`):
   - Komplett getrennt von llm-council's `users` Tabelle
   - Migration: `supabase/migrations/20260215_phase_b_own_users_table.sql`
2. **Auth-Modul** (`backend/app/auth.py`):
   - bcrypt Passwort-Hashing, JWT Access-Token (30min) + Refresh-Token (7d)
   - FastAPI Dependencies: `get_current_user`, `get_current_admin`
   - Register mit Username/Email Duplikat-Check
3. **Token-Tracking** (`backend/app/token_tracking.py`):
   - Eigene `chat_token_usage` Tabelle (nicht llm-council's `token_usage`)
   - Kosten-Schätzung pro Modell (COST_PER_1M_TOKENS)
   - Usage-Erfassung nach jedem LLM-Call (streaming + non-streaming)
   - Migration: `supabase/migrations/20260215_phase_b_auth_token_tracking.sql`
4. **Geschützte Endpoints**:
   - Alle `/api/conversations/*` mit `Depends(get_current_user)` + Ownership-Check
   - Auth-Endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me`
   - Usage-Endpoint: `/api/usage`
5. **LLM Usage-Erfassung** (`backend/app/llm.py`):
   - Stream-Generatoren liefern Usage-Dict als letztes Element
   - OpenAI: `stream_options: {"include_usage": true}`
   - Anthropic: `message_start` + `message_delta` Events
   - Google: `usageMetadata` aus letztem Chunk
6. **Frontend**:
   - Login/Register-Screen (`LoginScreen.jsx`)
   - Token-Management in `api.js` (localStorage, auto-refresh bei 401)
   - Usage-Widget in Sidebar (`UsageWidget.jsx`)
   - Auth-State in `App.jsx` (Loading → Login → App)

### Phase C Schritt 1: KI-Assistenten + Prompt-Templates (2026-02-16)
1. **Datenbank-Migration** (`supabase/migrations/20260216_phase_c_assistants_templates.sql`):
   - `assistants` Tabelle (user_id, name, description, system_prompt, model, temperature, is_global, icon)
   - `prompt_templates` Tabelle (user_id, name, description, content, category, is_global)
   - `chats.assistant_id` FK auf `assistants`
2. **Backend CRUD-Module**:
   - `backend/app/assistants.py`: Erstellen, Auflisten (eigene + globale), Lesen, Updaten, Löschen
   - `backend/app/templates.py`: Analog für Prompt-Templates
   - Ownership-/Admin-Checks für globale Einträge
3. **API-Endpoints**:
   - `GET/POST /api/assistants`, `GET/PATCH/DELETE /api/assistants/{id}`
   - `GET/POST /api/templates`, `GET/PATCH/DELETE /api/templates/{id}`
   - `is_global=true` nur für Admins
4. **System-Prompt Injection**:
   - Wenn Chat `assistant_id` hat → Assistant laden → `system_prompt` als erste Message in LLM-Kontext
   - Model/Temperature-Override vom Assistant (nachrangig zu Message- und Conversation-Level)
   - `CreateConversationRequest` erweitert um `assistant_id`
5. **Frontend-Komponenten**:
   - `AssistantSelector.jsx`: Icon-Grid in Sidebar, Klick erstellt neuen Chat mit Assistent
   - `AssistantManager.jsx`: Modal für CRUD (Name, Icon, Beschreibung, System-Prompt, Model/Temp)
   - `TemplateManager.jsx`: Modal für CRUD (Name, Beschreibung, Kategorie, Inhalt)
   - `TemplatePicker.jsx`: Dropdown in MessageInput, fügt Template-Text in Textarea ein
6. **Geänderte Dateien**:
   - `App.jsx`: Assistants/Templates State, CRUD-Handler, Manager-Modals
   - `Sidebar.jsx`: AssistantSelector, Buttons für Assistenten/Templates verwalten
   - `ChatArea.jsx`: Templates-Prop an MessageInput durchreichen
   - `MessageInput.jsx`: TemplatePicker neben Model-Selector
   - `api.js`: 8 neue API-Methoden (CRUD für Assistenten + Templates)
   - `storage.py`: `assistant_id` in create/get_conversation
   - `models.py`: 4 neue Request-Models

## Nächste Umsetzungsschritte
1. **Phase C Schritt 2**: Datei-Upload, RAG-Pipeline (pgvector, Embeddings, Vektor-Suche)
2. **Phase D**: Admin-Dashboard, Workflow-Engine, Audit-Logs, SSO
3. RLS und Mandantenmodell in Supabase aktivieren
4. Integrationstests für API und End-to-End-Chat
