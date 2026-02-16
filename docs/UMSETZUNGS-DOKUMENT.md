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
   - Multi-Provider Support: OpenAI, Anthropic, Google Gemini, Mistral, X.AI, Azure OpenAI
   - Streaming (SSE) und Non-Streaming Calls via `httpx.AsyncClient`
   - Anthropic-Sonderbehandlung (anderes Request-Format)
   - Azure OpenAI Sonderbehandlung: eigene URL/Request/Call/Stream-Funktionen
   - GPT-5.x: kein Temperature-Parameter, `max_completion_tokens` statt `max_tokens`
   - Azure Auth via `api-key` Header, Deployment-Name Lookup aus `app_model_config`
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
| `app_model_config` | XQT5 AI Plattform | Admin-verwaltete Modell-Liste (+ deployment_name für Azure) |
| `app_provider_keys` | XQT5 AI Plattform | Verschlüsselte Provider-API-Keys + Azure-Config |
| `app_audit_logs` | XQT5 AI Plattform | Audit-Log-Einträge |
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
   - Azure: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_API_VERSION` (default: 2025-04-01-preview)
   - Defaults: `DEFAULT_MODEL`, `DEFAULT_TEMPERATURE`
3. Frontend-Service erstellen:
   - Build Context: `frontend`, Dockerfile: `frontend/Dockerfile`
   - Domain: `ai-hub.xqtfive.com`
   - Build-Arg: `VITE_API_BASE=https://api.xqtfive.com`
4. `CORS_ORIGINS` im Backend auf Frontend-Domain setzen
5. Supabase-Migrationen ausführen (initial + phase_a + phase_b + phase_c + phase_d)

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

### Phase D: Admin-Dashboard + Audit-Logs (2026-02-16)
1. **Datenbank-Migration** (`supabase/migrations/20260216_phase_d_admin_audit.sql`):
   - `app_model_config` Tabelle (model_id, provider, display_name, is_enabled, is_default, sort_order)
   - Seed mit 9 aktuellen Modellen aus `llm.py`
   - `app_audit_logs` Tabelle (user_id, action, target_type, target_id, metadata, ip_address)
   - Indizes auf user_id, action, created_at, (target_type, target_id)
2. **Admin-Modul** (`backend/app/admin.py`):
   - `list_users()`, `update_user()` (Active/Admin-Toggle)
   - `get_global_usage_summary()`, `get_usage_per_user()` (Token-Kosten Aggregation)
   - `get_system_stats()` (Zähler: Users, Chats, Messages, Assistenten, Templates)
   - `list_model_configs()`, `create_model_config()`, `update_model_config()`, `delete_model_config()`
   - Default-Modell-Logik: Setzen eines neuen Defaults setzt alle anderen zurück
3. **Audit-Modul** (`backend/app/audit.py`):
   - Action-Konstanten für Auth, Admin, Chat
   - `log_event()` — fire-and-forget Audit-Logging
   - `list_audit_logs()` — paginierte Abfrage mit Filtern, JOIN auf app_users für Username
4. **Admin API-Endpoints** (alle `Depends(get_current_admin)`):
   - `GET/PATCH /api/admin/users/{id}` — User-Verwaltung (Selbstschutz: kein Self-Deactivate)
   - `GET /api/admin/usage` — Globale + Per-User Kosten
   - `GET /api/admin/stats` — System-Statistiken
   - `GET/POST/PATCH/DELETE /api/admin/models` — Modell-Konfigurationen
   - `GET /api/admin/audit-logs` — Paginierte Audit-Logs mit Filtern
5. **LLM-Modul** (`backend/app/llm.py`):
   - `get_available_models()` liest aus DB (`app_model_config`), Fallback auf hardcoded Liste
6. **Audit-Events** in bestehende Endpoints injiziert:
   - Auth: login (success + failed), register
   - Admin: user toggles, model config CRUD
   - Chat: conversation create/delete, message send (nur Metadaten, kein Inhalt)
7. **Frontend**:
   - `AdminDashboard.jsx`: Tab-basierte Navigation (Benutzer, Kosten, Statistiken, Modelle, Audit-Logs, Provider)
   - Benutzer-Tab: Tabelle mit Active/Admin Toggle-Switches
   - Kosten-Tab: Globale Totals (Cards) + Per-User-Tabelle sortiert nach Kosten
   - Statistiken-Tab: Card-Grid (6 Metriken)
   - Modelle-Tab: Enable/Disable Toggle, Default-Radio, Neues Modell hinzufügen
   - Audit-Logs-Tab: Paginierte Tabelle mit Aktions-Filter, "Mehr laden"-Button
   - `Sidebar.jsx`: Admin-Button (nur für Admins sichtbar)
   - `App.jsx`: showAdmin State, bedingtes Rendering (AdminDashboard statt ChatArea)
   - `api.js`: 9 neue Admin-API-Methoden
   - `styles.css`: Admin-Dashboard, Tabs, Cards, Table, Toggle-Switches
8. **Pydantic-Models** (`backend/app/models.py`):
   - `UpdateUserRequest`, `CreateModelConfigRequest`, `UpdateModelConfigRequest`

### Phase D Erweiterung: Provider-Key-Verwaltung + Azure OpenAI (2026-02-16)
1. **Datenbank-Migrationen**:
   - `supabase/migrations/20260216_phase_d_provider_keys.sql`: `app_provider_keys` Tabelle (provider, api_key_encrypted, extra_config, created_at, updated_at)
   - `supabase/migrations/20260216_phase_d_azure_provider.sql`: `deployment_name` Spalte in `app_model_config`
2. **Encryption-Modul** (`backend/app/encryption.py`):
   - Fernet-Verschlüsselung mit von `JWT_SECRET` abgeleitetem Key (PBKDF2)
   - `encrypt_value()` / `decrypt_value()` Funktionen
3. **Provider-Modul** (`backend/app/providers.py`):
   - `get_provider_key()`: DB-Lookup mit Fallback auf Env-Variable
   - `set_provider_key()`: Verschlüsseltes Speichern in DB
   - `delete_provider_key()`: Entfernen aus DB
   - `get_provider_config()`: Gesamte Provider-Konfiguration (Key + Extra-Config)
   - `test_provider_key()`: Live-Test gegen Provider-API
4. **Admin API-Endpoints** (alle `Depends(get_current_admin)`):
   - `GET /api/admin/providers` — Alle Provider mit Key-Status (masked)
   - `PUT /api/admin/providers/{provider}/key` — Key speichern/aktualisieren
   - `DELETE /api/admin/providers/{provider}/key` — Key löschen
   - `POST /api/admin/providers/{provider}/test` — Provider-Verbindung testen
5. **LLM-Modul Azure-Erweiterungen** (`backend/app/llm.py`):
   - `_azure_url()`: Endpoint-URL-Konstruktion mit Deployment-Name
   - `_azure_headers()`: `api-key` Header statt Bearer Token
   - `_azure_request_body()`: GPT-5.x Handling (kein Temperature, `max_completion_tokens`)
   - `_call_azure()` / `_stream_azure()`: Eigene Call/Stream-Funktionen
   - Auto-Strip von Pfad-Komponenten aus Azure Endpoint-URL
6. **Config** (`backend/app/config.py`):
   - Neue Env-Vars: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_API_VERSION`
7. **Frontend**:
   - Provider-Keys Tab in `AdminDashboard.jsx` mit Save/Delete/Test pro Provider
   - Azure-spezifische Felder (Endpoint-URL, API-Version) im Provider-Tab
   - Deployment-Name Feld in Modell-Konfiguration
   - `api.js`: 4 neue Admin-API-Methoden (GET/PUT/DELETE/POST Provider)

## Nächste Umsetzungsschritte
1. **Phase C Schritt 2**: Datei-Upload, RAG-Pipeline (pgvector, Embeddings, Vektor-Suche)
2. **Phase D Rest**: Workflow-Engine, SSO (OIDC/SAML)
3. RLS und Mandantenmodell in Supabase aktivieren
4. Integrationstests für API und End-to-End-Chat
