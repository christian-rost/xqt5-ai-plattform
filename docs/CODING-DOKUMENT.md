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

### Offene Risiken
1. Supabase RLS-Policies sind noch nicht aktiviert.
2. Kein Rate-Limiting auf LLM-Endpoints — authentifizierte User können unbegrenzt Kosten verursachen.

## Präventionsmaßnahmen
1. Vor jedem Merge: API-Smoketest, Frontend-Build, Datenbankschema-Check.
2. Jede Produktionsänderung erhält eine kurze Post-Deploy-Checkliste.
3. Bei neu gefundenen Fehlern wird hier ein Eintrag mit Ursache und Fix ergänzt.
4. **KEINE shared Tabellen** — jede Anwendung nutzt nur eigene Tabellen. llm-council-Tabellen (users, conversations, messages, token_usage, app_settings, api_keys, provider_api_keys) nie anfassen.
5. **Python-Version im Docker-Image prüfen** bevor neue Syntax-Features verwendet werden (aktuell: 3.11).
6. **Bei neuen Tabellen: kein Copy-Paste aus altem Storage-Code** ohne Feldprüfung.
