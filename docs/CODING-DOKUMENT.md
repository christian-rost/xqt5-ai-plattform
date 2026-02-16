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

### Offene Risiken
1. Supabase RLS-Policies sind noch nicht aktiviert.
2. Kein Rate-Limiting auf LLM-Endpoints — authentifizierte User können unbegrenzt Kosten verursachen.
3. Provider-API-Keys in DB sind Fernet-verschlüsselt mit von JWT_SECRET abgeleitetem Key — bei JWT_SECRET-Rotation werden alle gespeicherten Keys unlesbar.

## Präventionsmaßnahmen
1. Vor jedem Merge: API-Smoketest, Frontend-Build, Datenbankschema-Check.
2. Jede Produktionsänderung erhält eine kurze Post-Deploy-Checkliste.
3. Bei neu gefundenen Fehlern wird hier ein Eintrag mit Ursache und Fix ergänzt.
4. **KEINE shared Tabellen** — jede Anwendung nutzt nur eigene Tabellen. llm-council-Tabellen (users, conversations, messages, token_usage, app_settings, api_keys, provider_api_keys) nie anfassen.
5. **Python-Version im Docker-Image prüfen** bevor neue Syntax-Features verwendet werden (aktuell: 3.11).
6. **Bei neuen Tabellen: kein Copy-Paste aus altem Storage-Code** ohne Feldprüfung.
7. **Azure-Modelle immer mit `deployment_name` in `app_model_config` anlegen.**
