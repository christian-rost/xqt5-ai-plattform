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
| `app_documents` | XQT5 AI Plattform | Hochgeladene Dokumente (PDF/TXT/Bild) mit Status + pool_id |
| `app_document_chunks` | XQT5 AI Plattform | Dokument-Chunks mit Embeddings (vector(1536)) |
| `pool_pools` | XQT5 AI Plattform | Pool-Metadaten (name, description, icon, color, owner_id) |
| `pool_members` | XQT5 AI Plattform | Pool-Mitgliedschaften mit Rolle (viewer/editor/admin) |
| `pool_invite_links` | XQT5 AI Plattform | Share-Links mit Token, Rolle, max_uses, expires_at |
| `pool_chats` | XQT5 AI Plattform | Pool-Chats (shared + private via is_shared Flag) |
| `pool_chat_messages` | XQT5 AI Plattform | Pool-Chat-Nachrichten mit user_id für Attribution |
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
   - Rate Limiting: `RATE_LIMIT_STORAGE_URL` (Default: `memory://`, Prod: `redis://redis:6379`)
   - Proxy: `FORWARDED_ALLOW_IPS` (Default: `*`)
3. Frontend-Service erstellen:
   - Build Context: `frontend`, Dockerfile: `frontend/Dockerfile`
   - Domain: `ai-hub.xqtfive.com`
   - Build-Arg: `VITE_API_BASE=https://api.xqtfive.com`
4. `CORS_ORIGINS` im Backend auf Frontend-Domain setzen
5. Supabase-Migrationen in numerischer Reihenfolge ausführen (alle Dateien unter `supabase/migrations/`)
   - **Wichtig**: pgvector Extension muss vor der RAG-Migration aktiviert sein (Dashboard → Database → Extensions → vector)

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

### Phase C Schritt 2: File Upload + RAG-Pipeline (2026-02-16)
1. **Datenbank-Migration** (`supabase/migrations/20260216_phase_c_rag.sql`):
   - `CREATE EXTENSION IF NOT EXISTS vector` (pgvector)
   - `app_documents` Tabelle (user_id, chat_id nullable, filename, file_type, file_size_bytes, extracted_text, chunk_count, status, error_message)
   - `app_document_chunks` Tabelle (document_id, chunk_index, content, token_count, embedding vector(1536))
   - HNSW-Index auf embedding (vector_cosine_ops)
   - RPC `match_document_chunks()`: Scope-basierte Similarity-Suche (Conversation, Pool oder global)
2. **Documents-Modul** (`backend/app/documents.py`):
   - `extract_text()` / `extract_text_and_assets()` (async): PDF/Bild via Mistral OCR API, TXT via UTF-8
   - `_ocr_pdf_mistral_with_assets()`: Sendet PDF als base64 data-URI an Mistral OCR API (`mistral-ocr-latest`), gibt Text + OCR-Assets zurück
   - `_ocr_image_mistral()`: Verarbeitet Bild-Uploads (`PNG/JPG/JPEG/WEBP`) über Mistral OCR API
   - Mistral API-Key via `providers.get_api_key("mistral")` (DB mit Env-Fallback)
   - Keine zusätzlichen System-Pakete nötig (kein Tesseract/Poppler)
   - CRUD: `create_document()`, `update_document_status()`, `list_documents()`, `get_document()`, `delete_document()`
   - `has_ready_documents()`: Quick-Check für RAG-Injection
3. **RAG-Modul** (`backend/app/rag.py`):
   - `chunk_text()`: Paragraph-aware Splitting mit konfigurierbarer chunk_size/overlap
   - `generate_embeddings()`: OpenAI API via httpx, nutzt `providers.get_api_key("openai")`
   - `process_document()`: Chunk + Embed + Store, Token-Usage-Tracking
   - `search_similar_chunks()`: Embedding-Generierung + Supabase RPC
   - `build_rag_context()`: Formatierter Context-String mit Source-Labels
4. **Config** (`backend/app/config.py`): 7 neue Variablen (EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, CHUNK_SIZE, CHUNK_OVERLAP, RAG_TOP_K, RAG_SIMILARITY_THRESHOLD, MAX_UPLOAD_SIZE_MB)
5. **Token-Tracking** (`backend/app/token_tracking.py`): Embedding-Kosten (text-embedding-3-small/large)
6. **API-Endpoints** (`backend/app/main.py`):
   - `POST /api/documents/upload` — UploadFile + Form(chat_id), unterstützt PDF/TXT/Bild, extrahiert Text, erzeugt Chunks+Embeddings
   - `GET /api/documents?chat_id=&scope=` — Dokument-Liste
   - `DELETE /api/documents/{id}` — Löschen (CASCADE auf Chunks)
   - `POST /api/rag/search` — Debug/Test-Endpoint für Similarity-Suche
7. **RAG-Injection** in `send_message()`:
   - Prüft ob User ready Docs hat, sucht ähnliche Chunks, injiziert als System-Message-Kontext
   - `rag_sources` Liste wird in Stream-Done-Event und Non-Streaming-Response mitgegeben
8. **Dependencies**: OCR läuft über Mistral API; `pypdf` ist aktuell noch als Legacy-Dependency in `pyproject.toml` enthalten
9. **Frontend-Komponenten**:
   - `FileUpload.jsx`: Clip-Icon Button mit Hidden File-Input (PDF/TXT/PNG/JPG/JPEG/WEBP)
   - `DocumentList.jsx`: Dokument-Tags (Icon + Name + Chunks + Status + Delete)
   - `SourceDisplay.jsx`: "Sources:" Label mit Filename-Tags unter Assistant-Nachrichten
10. **Frontend-Änderungen**:
    - `api.js`: `uploadDocument()`, `listDocuments()`, `deleteDocument()`, sources in `onDone`
    - `MessageInput.jsx`: FileUpload-Button + DocumentList
    - `MessageBubble.jsx`: SourceDisplay unter Assistant-Nachrichten
    - `ChatArea.jsx`: Neue Props (documents, onUpload, onDeleteDocument)
    - `App.jsx`: chatDocuments State, loadDocuments Effect, Upload/Delete Handlers, Sources an Messages
    - `styles.css`: file-upload, document-list, rag-sources Styles

### Phase D Erweiterung 2: Security Hardening (2026-02-17)
1. **is_active Enforcement** auf Access- UND Refresh-Token:
   - `get_current_user()` prüft `is_active` bei jedem Request
   - Refresh-Endpoint prüft `is_active` vor Token-Erneuerung
   - Fehlermeldung: "Account is inactive"
2. **Token Version Revocation** (`token_version` Spalte in `app_users`):
   - Migration: `supabase/migrations/20260217_phase_d_token_version_revocation.sql`
   - `bump_token_version()` in `auth.py` erhöht die Version → alle bestehenden Tokens ungültig
   - Access- und Refresh-Token enthalten `token_version` Claim, wird bei Validierung geprüft
   - Wird automatisch bei User-Deaktivierung (`PATCH /api/admin/users/{id}` mit `is_active=false`) aufgerufen
3. **slowapi Rate Limiting** (7 Endpoints):
   - `POST /api/auth/register` — 5/minute
   - `POST /api/auth/login` — 10/minute
   - `POST /api/auth/refresh` — 30/minute
   - `POST /api/conversations/{id}/message` — 60/minute
   - `POST /api/documents/upload` — 20/minute
   - `POST /api/rag/search` — 60/minute
   - `POST /api/admin/providers/{provider}/test` — 20/minute
   - Key-Funktion: per-User (`user:<uuid>`) bei gültigem Bearer-Token, Fallback `ip:<address>`
4. **Redis-Backend** via `RATE_LIMIT_STORAGE_URL` Env-Variable:
   - Default: `memory://` (In-Process, kein Redis nötig)
   - Produktion: `redis://redis:6379` für persistente Limits über Restarts
5. **Proxy-Headers** für korrekte Client-IP hinter Reverse-Proxy:
   - Uvicorn CMD: `--proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"`
   - Env-Variable `FORWARDED_ALLOW_IPS` (Default: `*`)
6. **Dependencies**: `slowapi>=0.1.9`, `redis>=5.0.0` in pyproject.toml + Dockerfile

### Phase D Erweiterung 3: Admin User Löschen + Default-Modell Fix (2026-02-17)
1. **Admin User Soft-Delete** (`DELETE /api/admin/users/{user_id}`):
   - Setzt `is_active=false` + `bump_token_version()` zur Session-Invalidierung
   - Selbstschutz: Admin kann sich nicht selbst löschen (HTTP 400)
   - Audit-Log: `ADMIN_USER_DEACTIVATE`
2. **Frontend UsersTab Erweiterungen** (`AdminDashboard.jsx`):
   - `showInactive` State (default `false`) mit Checkbox "Deaktivierte anzeigen"
   - Inaktive User standardmäßig ausgeblendet, mit Toggle einblendbar
   - "Löschen"-Button pro Zeile (rot, disabled für eigenen User, `confirm()` Dialog)
   - Deaktivierte Zeilen: CSS-Klasse `.user-inactive` für graue Darstellung
   - `currentUser` Prop von `App.jsx` durchgereicht für Selbstschutz
3. **Default-Modell Bugfix** (`llm.py` + `App.jsx` + `admin.py` + `main.py`):
   - `/api/models` gibt jetzt `is_default` Flag aus `app_model_config` zurück (auch im Fallback-Pfad)
   - Frontend wählt beim Laden das `is_default && available` Modell statt hardcoded Fallback
   - Hardcoded `DEFAULT_MODEL` in `FALLBACK_MODEL` umbenannt (nur noch als letzter Fallback)
   - Neuer State `defaultModelId` im Frontend: wird bei Conversation-Wechsel als Fallback genutzt (`activeConversation.model || defaultModelId`)
   - Backend: Neue Funktion `admin.get_default_model_id()` liest `is_default && is_enabled` aus DB
   - Backend: `send_message()` Fallback-Kette erweitert: `payload.model → conversation.model → assistant.model → admin.get_default_model_id() → DEFAULT_MODEL`
4. **API** (`api.js`): Neue Methode `adminDeleteUser(userId)` → `DELETE /api/admin/users/${userId}`

### Phase E: Pools — Geteilte Dokumentensammlungen (umgesetzt 2026-02-18)

#### Datenbank
1. **Migration** (`supabase/migrations/20260218_pools.sql`):
   - `pool_pools` Tabelle (id, name, description, icon, color, owner_id → app_users)
   - `pool_members` Tabelle (pool_id, user_id, role CHECK viewer/editor/admin, UNIQUE pool_id+user_id)
   - `pool_invite_links` Tabelle (pool_id, token VARCHAR(64) UNIQUE, role, max_uses, use_count, expires_at, is_active)
   - `pool_chats` Tabelle (pool_id, title, is_shared, created_by, model, temperature)
   - `pool_chat_messages` Tabelle (chat_id, user_id, role, content, model)
   - `app_documents` erweitert: `pool_id UUID REFERENCES pool_pools(id) ON DELETE CASCADE`
   - `match_document_chunks()` RPC erweitert: neuer Parameter `match_pool_id UUID DEFAULT NULL` — wenn gesetzt, werden nur Pool-Dokumente durchsucht

#### Backend
2. **Pools-Modul** (`backend/app/pools.py`):
   - Pool CRUD: `create_pool()`, `list_pools_for_user()`, `get_pool()`, `update_pool()`, `delete_pool()`
   - Auth: `get_user_pool_role()` → owner/admin/editor/viewer/None, `require_pool_role()` → HTTP 403
   - Members: `add_member()`, `list_members()`, `update_member_role()`, `remove_member()`, `find_user_by_username()`
   - Invites: `create_invite_link()`, `get_invite_by_token()`, `use_invite_link()`, `list_invite_links()`, `revoke_invite_link()`
   - Pool Docs: `list_pool_documents()`, `get_pool_document_preview()`, `has_ready_pool_documents()`
   - Pool Chats: `create_pool_chat()`, `list_pool_chats()`, `get_pool_chat()`, `add_pool_chat_message()`, `delete_pool_chat()`
3. **Bestehende Module erweitert**:
   - `documents.py`: `create_document()` bekommt `pool_id` Parameter
   - `rag.py`: `search_similar_chunks()` bekommt `pool_id` Parameter, wird an RPC weitergegeben
   - `models.py`: 8 neue Pydantic-Modelle (CreatePoolRequest, AddPoolMemberRequest, CreateInviteLinkRequest, JoinPoolRequest, CreatePoolChatRequest, SendPoolMessageRequest, etc.)
4. **API-Endpunkte** (`main.py`):
   - Pool CRUD: POST/GET/PATCH/DELETE `/api/pools`
   - Members: GET/POST/PATCH/DELETE `/api/pools/{pool_id}/members`
   - Invites: GET/POST/DELETE `/api/pools/{pool_id}/invites`, POST `/api/pools/join`
   - Documents: GET/POST/DELETE `/api/pools/{pool_id}/documents` + GET `/api/pools/{pool_id}/documents/{document_id}/preview`
   - Chats: GET/POST/DELETE `/api/pools/{pool_id}/chats`, POST `/api/pools/{pool_id}/chats/{chat_id}/message`

#### Frontend
5. **API-Client** (`api.js`): Pool-Endpunkte inkl. Dokumentvorschau (`getPoolDocumentPreview`)
6. **Neue Komponenten** (8 Dateien):
   - `PoolList.jsx` — Sidebar-Sektion mit Pool-Liste
   - `CreatePoolDialog.jsx` — Modal: Pool erstellen
   - `PoolDetail.jsx` — Hauptansicht mit Tabs (Dokumente/Chats/Mitglieder)
   - `PoolDocuments.jsx` — Dokumentenliste + Upload + Vorschau-Modal
   - `PoolChatList.jsx` — Shared + private Chats
   - `PoolChatArea.jsx` — Chat-Ansicht (nutzt bestehende MessageBubble/MessageInput/SourceDisplay)
   - `PoolMembers.jsx` — Mitgliederliste mit Rollen-Management
   - `PoolShareDialog.jsx` — Invite-Link-Dialog
7. **App.jsx Änderungen**: Neuer State (pools, activePool, activePoolView, activePoolChat), mutually exclusive mit activeConversation
8. **Sidebar.jsx**: PoolList-Integration

#### Phase E Update (2026-02-19): Dokumentvorschau im Pool
9. **Neuer Endpoint** (`main.py`):
   - `GET /api/pools/{pool_id}/documents/{document_id}/preview`
   - Zugriff für alle Pool-Mitglieder (ab Rolle `viewer`)
10. **Preview-Logik** (`pools.py`):
   - Liefert `text_preview`, `text_length`, `truncated` für Dokumente
   - Liefert bei Bild-Dokumenten optional `image_data_url` aus `app_document_assets`
11. **Frontend-UX** (`PoolDocuments.jsx` + `styles.css`):
   - Vorschau-Button pro Dokument
   - Modal mit Textvorschau (gekürzt) und optionaler Bildansicht

#### Design-Entscheidungen
- `app_documents` wird wiederverwendet (statt eigener pool_documents), weil `app_document_chunks` per FK darauf verweist — hält Embedding-Pipeline unverändert
- `pool_chats`/`pool_chat_messages` sind separate Tabellen (nicht `chats`/`chat_messages`), weil Pool-Chats Multi-User-Zugriff brauchen
- Owner ist NICHT in `pool_members` — Ownership implizit über `pool_pools.owner_id`

### Phase RAGPools: RAG-Qualität für Conversations + Pools (2026-02-19)

#### Migrations
- `supabase/migrations/20260219_phase_f_multimodal_assets.sql` — `app_document_assets` Tabelle für Bild-RAG
- `supabase/migrations/20260220_runtime_rag_settings.sql` — Admin-konfigurierbare RAG-Einstellungen (Cohere Reranking)
- `supabase/migrations/20260221_rag_scoped_search.sql` — Scope-isolierte `match_document_chunks`/`match_document_assets`: conversation-only, pool-only, global-only (kein `OR d.chat_id IS NULL` mehr)
- `supabase/migrations/20260219_drop_old_function_overloads.sql` — Droppt alte 5-Parameter-Versionen der RPCs (behebt PGRST203)

#### Backend `rag.py`
- **`_rpc_chunks()`** / **`_rpc_assets()`**: Wrapper die pre-computed Embeddings wiederverwenden; Parameter nur inkludiert wenn `is not None`
- **`_search_chunks_hybrid()`** (ehem. `_search_chunks_two_phase`): Phase 1 Vektor (Conversation), Phase 2 Keyword ILIKE-Supplement
- **`_extract_query_keywords()`**: Stopwort-Filterung (DE+EN), min. 4 Zeichen, max. 3 Keywords
- **`_keyword_supplement_chunks()`**: Scope-aware ILIKE-Suche in `app_document_chunks`, enriched mit filename
- **`retrieve_chunks_with_strategy()`**: Conversations nutzen `top_k=50, threshold=0.0` (alle Chunks, kein Filter), Pools nutzen threshold-gefilterte Pläne; ohne Cohere werden alle Chunks in Dokumentreihenfolge zurückgegeben
- **`_apply_optional_rerank()`**: Ohne Cohere → Dokumentreihenfolge (`document_id, chunk_index`), alle Chunks; mit Cohere → `rerank_candidates=50` (Default erhöht von 20)
- **Cohere Reranking** (`_cohere_rerank()`): Optional via Admin-konfigurierbares `rerank_enabled`, `rerank_model`, `rerank_candidates`, `rerank_top_n`

#### Backend `main.py`
- RAG-Injection für `send_message` und `send_pool_message` in separate `try/except`-Blöcke aufgeteilt: Vector-Suche, Context-Injection, Text-Fallback sind unabhängig voneinander
- `exc_info=True` bei allen RAG-Exception-Logs für vollständige Stack-Traces

#### Design-Entscheidungen
- **Globale Dokumente weiterhin API-seitig vorhanden**: Scope `chat_id IS NULL` wird weiterhin unterstützt (z. B. in Dokumentlisten/Fallback-Pfaden); Haupt-UI-Fluss bleibt chat- und pool-zentriert
- **Conversations: Wide-Net-Retrieval**: Statt threshold-Filterung alle verfügbaren Chunks abrufen und in Dokumentreihenfolge sortieren; relevanter für Einzeldokument-Conversations
- **Hybrid Search**: ILIKE-Supplement garantiert dass Kapitel mit spezifischen Begriffen auch bei niedrigem Vektor-Score im Kandidatenset landen

## Nächste Umsetzungsschritte
1. **Workflow-Engine** für automatisierte Abläufe
2. **SSO** (OIDC/SAML)
3. RLS und Mandantenmodell in Supabase aktivieren
4. Integrationstests für API und End-to-End-Chat
