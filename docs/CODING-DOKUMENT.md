# Coding-Dokument

## Ziel
Dieses Dokument hält Coding-Entscheidungen und Fehlerjournal fest, damit Fehler nicht wiederholt werden.

## Coding-Regeln (für dieses Projekt)
1. Frontend und Backend bleiben strikt getrennt deploybar.
2. Alle neuen APIs werden zuerst mit Request-/Response-Modellen typisiert.
3. Jede DB-Änderung erfolgt über versionierte Migrationen in `supabase/migrations/`.
4. Secrets werden nie in Code oder Commit gespeichert, nur via Env.
5. CORS und Security-Header werden für produktive Domains explizit gesetzt.
6. Keine Funktions- oder Codeübernahme aus `llm-council`; ausschließlich API-basierte Anbindung.
7. In Code und Dokumentation wird nicht auf externe Wettbewerbs-Produktnamen verwiesen.

## Fehlerjournal

### 2026-02-14
- Fehler: `python -m compileall` initial ohne `PYTHONPYCACHEPREFIX` ausgeführt.
  Ursache: In der Sandbox wurde in einen nicht erlaubten Standard-Cachepfad geschrieben.
  Korrektur: Compile-Checks künftig mit `PYTHONPYCACHEPREFIX=/tmp/pythoncache` ausführen.

### 2026-02-15 (Phase A)
- **Fehler: llm-council-Tabellen für Chat wiederverwendet.**
  Ursache: Die bestehenden `conversations`/`messages` Tabellen (mit stage1/stage2/stage3 Pipeline-Feldern) wurden fälschlicherweise für den direkten Chat mitbenutzt, statt eigene Tabellen anzulegen.
  Korrektur: Eigene Tabellen `chats` und `chat_messages` erstellt. **Regel: llm-council-Tabellen (conversations, messages, token_usage) nie für eigene Features nutzen. Immer eigene Tabellen anlegen.**

- **Fehler: Python 3.11 inkompatible Type-Annotation `StreamingResponse | dict`.**
  Ursache: Union-Syntax mit `|` in Return-Type ist in Python 3.11 kein valider Pydantic-Typ für FastAPI Response-Models. Docker-Image nutzt Python 3.11-slim.
  Korrektur: `response_model=None` im Decorator verwenden, Return-Type-Annotation weglassen. **Regel: Bei Endpoints die sowohl JSON als auch StreamingResponse zurückgeben, immer `response_model=None` setzen und keine Union-Type-Annotation verwenden.**

- **Fehler: stage3-Referenzen in neuem Code übernommen.**
  Ursache: Beim Bauen von storage.py und Frontend wurde aus dem bestehenden Code die `stage3.answer`-Logik kopiert, obwohl die neuen `chat_messages` keine stage-Felder haben.
  Korrektur: Alle stage1/stage2/stage3/metadata-Referenzen aus storage.py, main.py und ChatArea.jsx entfernt. **Regel: Neuen Code nicht blind aus bestehendem Code kopieren — immer prüfen ob die Felder in der Ziel-Tabelle existieren.**

### 2026-02-15 (Phase B)
- **Fehler: Shared `users` Tabelle mit llm-council verwendet.**
  Ursache: Die `users` Tabelle aus der initialen Migration wurde als "Shared" behandelt, obwohl beide Anwendungen komplett getrennt sein sollen. Register schlug fehl ("Email already exists") weil llm-council bereits Einträge hatte.
  Korrektur: Eigene `app_users` Tabelle erstellt, FKs von `chats` und `chat_token_usage` umgehängt. **Regel: KEINE shared Tabellen. Jede Anwendung nutzt ausschließlich eigene Tabellen.**

### 2026-02-16 (Phase D — Azure OpenAI + Provider-Keys)
- **Fehler: Azure GPT-5.x akzeptiert keine Temperature != 1.**
  Ursache: Azure's GPT-5.x Modelle unterstützen nur den Default-Wert `temperature=1`. Jeder andere Wert führt zu einem API-Fehler.
  Korrektur: Temperature-Parameter wird bei GPT-5.x Modellen nicht mitgesendet. **Regel: Bei neuen Azure-Modellen immer prüfen, welche Parameter unterstützt werden.**

- **Fehler: Azure Endpoint-URL enthielt Pfad-Komponenten.**
  Ursache: User gaben die volle Azure-URL inkl. `/openai/deployments/...` ein, aber der Code baut den Pfad selbst auf, was zu doppelten Pfaden führte.
  Korrektur: Auto-Strip von Pfad-Komponenten — nur Schema + Host werden aus der konfigurierten URL übernommen. **Regel: Endpoint-URLs immer normalisieren.**

- **Fehler: Azure verwendet `api-key` Header statt `Authorization: Bearer`.**
  Ursache: Azure OpenAI nutzt ein anderes Auth-Schema als Standard-OpenAI. Der generische Bearer-Token-Ansatz wurde fälschlicherweise verwendet.
  Korrektur: Eigene `_azure_headers()` Funktion mit `api-key` Header. **Regel: Provider-spezifische Auth immer in eigener Funktion kapseln.**

- **Fehler: `max_tokens` statt `max_completion_tokens` bei GPT-5.x.**
  Ursache: GPT-5.x Modelle akzeptieren nur `max_completion_tokens`, nicht das ältere `max_tokens` Feld.
  Korrektur: Für GPT-5.x wird `max_completion_tokens` verwendet. **Regel: Azure-Request-Body-Aufbau in eigener Funktion mit Modell-spezifischer Logik.**

- **Fehler: Azure Deployment-Name != Model-Name.**
  Ursache: Azure nutzt Deployment-Names (z.B. `gpt-4o-deployment`) statt Model-Names (z.B. `gpt-4o`) in der API-URL. Ohne Mapping schlug der Call fehl.
  Korrektur: Eigene `deployment_name` Spalte in `app_model_config` mit Lookup in `_azure_url()`. **Regel: Azure-Modelle immer mit deployment_name in app_model_config anlegen.**

### 2026-02-16 (Phase C Schritt 2 — RAG)
- **Hinweis: pgvector Extension muss vor Migration aktiviert werden.**
  Die `vector`-Extension wird per `CREATE EXTENSION IF NOT EXISTS vector` in der Migration aufgerufen, muss aber in Supabase unter Dashboard → Database → Extensions vorab aktiviert sein.
- **Hinweis: OpenAI API-Key für Embeddings zwingend erforderlich.**
  Embeddings laufen über OpenAI (text-embedding-3-small). Ohne konfigurierten OpenAI-Key schlägt der Upload fehl. Key kann via Env oder Admin-Provider-UI gesetzt werden.
- **Hinweis: Supabase RPC `match_document_chunks` benötigt pgvector-Operatoren.**
  Die Funktion nutzt `<=>` (Cosine Distance). Ohne pgvector Extension schlägt die Suche fehl.

### 2026-02-17 (Security Hardening)
- **Rate Limiting mit slowapi + Redis**: 7 kritische Endpoints mit per-User/per-IP Limits versehen (Register 5/min, Login 10/min, Refresh 30/min, Message 60/min, Upload 20/min, RAG-Search 60/min, Provider-Test 20/min). Fallback auf In-Memory wenn kein Redis konfiguriert.
- **Token Version Revocation**: Neue `token_version` Spalte in `app_users`. Bei User-Deaktivierung wird `bump_token_version()` aufgerufen, alle bestehenden Tokens werden sofort ungültig. Access- und Refresh-Token prüfen `token_version` bei jeder Validierung.
- **is_active Enforcement auf Refresh**: Deaktivierte User können nicht nur keine neuen Access-Tokens nutzen, sondern auch kein Refresh durchführen. Fehlermeldung: "Account is inactive".
- **Proxy-Headers**: Uvicorn mit `--proxy-headers` und `FORWARDED_ALLOW_IPS` für korrekte IP-Erkennung hinter Coolify-Proxy.

### 2026-02-17 (OCR für gescannte PDFs)
- **OCR-Fallback via Mistral OCR API**: `extract_text()` ist jetzt `async`. Wenn pypdf weniger als 50 Zeichen aus einem PDF extrahiert (typisch für gescannte PDFs ohne Text-Layer), wird `_ocr_pdf_mistral()` aufgerufen.
- **Mistral OCR API**: `POST https://api.mistral.ai/v1/ocr` mit `mistral-ocr-latest` Modell. PDF wird als base64 data-URI gesendet, Antwort enthält Markdown pro Seite.
- **API-Key**: Via `providers.get_api_key("mistral")` (DB mit Env-Fallback). Ohne Key gibt es eine klare Fehlermeldung.
- **Keine System-Pakete**: Kein Tesseract/Poppler im Docker nötig — rein API-basiert.
- **Timeout**: 120s für große PDFs (httpx AsyncClient).

### 2026-02-17 (Admin User Löschen + Default-Modell Fix)
- **Admin User Soft-Delete**: Neuer `DELETE /api/admin/users/{user_id}` Endpoint. Setzt `is_active=false` und ruft `bump_token_version()` auf. Selbstschutz: Admin kann sich nicht selbst löschen (400). Frontend: Löschen-Button pro Zeile, deaktiviert für eigenen User, `confirm()` Dialog.
- **Deaktivierte User ausblenden**: UsersTab zeigt standardmäßig nur aktive User. Checkbox "Deaktivierte anzeigen" blendet inaktive User grau ein (`.user-inactive td { opacity: 0.5 }`).
- **Fehler: Default-Modell aus Admin-Dashboard wurde ignoriert.**
  Ursache: Frontend hatte `const DEFAULT_MODEL = 'google/gemini-3-pro-preview'` hardcoded. Die `is_default`-Einstellung aus `app_model_config` wurde weder von der `/api/models`-API zurückgegeben noch vom Frontend abgefragt.
  Korrektur: `get_available_models()` gibt jetzt `is_default` mit. Frontend sucht zuerst ein `is_default && available` Modell, Fallback auf erstes verfügbares. **Regel: Admin-konfigurierbare Defaults immer aus der DB lesen, nie im Frontend hardcoden.**

- **Fehler: Default-Modell griff trotz Fix nicht bei neuen Chats (Frontend + Backend).**
  Ursache (Backend): `send_message()` nutzte `DEFAULT_MODEL` env-var als Fallback, ohne die DB nach `is_default` zu fragen.
  Ursache (Frontend): Bei "New Conversation" wurde `selectedModel` nicht auf den DB-Default zurückgesetzt. Neue Conversations haben `model=null`, das useEffect ignorierte diesen Fall und behielt den vorherigen Wert bei.
  Korrektur (Backend): Neue Funktion `admin.get_default_model_id()` liest `is_default=true && is_enabled=true` aus `app_model_config`. In `send_message()` wird diese vor `DEFAULT_MODEL` abgefragt.
  Korrektur (Frontend): Neuer State `defaultModelId` speichert das API-Default-Modell. Bei Conversation-Wechsel wird `selectedModel` immer gesetzt: `activeConversation.model || defaultModelId`.
  **Regel: Fallback-Ketten immer End-to-End durchdenken — sowohl Frontend-UI als auch Backend-Verarbeitung müssen den DB-Default kennen.**

### Offene Risiken
1. Supabase RLS-Policies sind noch nicht aktiviert.
2. ~~Kein Rate-Limiting auf LLM-Endpoints~~ — **Gelöst (2026-02-17)**: slowapi Rate Limiting mit Redis-Backend auf allen kritischen Endpoints (siehe Fehlerjournal 2026-02-17).
3. Provider-API-Keys in DB sind Fernet-verschlüsselt mit von JWT_SECRET abgeleitetem Key — bei JWT_SECRET-Rotation werden alle gespeicherten Keys unlesbar.

## Präventionsmaßnahmen
1. Vor jedem Merge: API-Smoketest, Frontend-Build, Datenbankschema-Check.
2. Jede Produktionsänderung erhält eine kurze Post-Deploy-Checkliste.
3. Bei neu gefundenen Fehlern wird hier ein Eintrag mit Ursache und Fix ergänzt.
4. **KEINE shared Tabellen** — jede Anwendung nutzt nur eigene Tabellen. llm-council-Tabellen (users, conversations, messages, token_usage, app_settings, api_keys, provider_api_keys) nie anfassen.
5. **Python-Version im Docker-Image prüfen** bevor neue Syntax-Features verwendet werden (aktuell: 3.11).
6. **Bei neuen Tabellen: kein Copy-Paste aus altem Storage-Code** ohne Feldprüfung.
7. **Azure-Modelle immer mit `deployment_name` in `app_model_config` anlegen.**
8. **Token-Invalidierung**: Bei sicherheitskritischen User-Änderungen (Deaktivierung, Passwort-Reset) immer `bump_token_version()` aufrufen, damit alle bestehenden Tokens sofort ungültig werden.
