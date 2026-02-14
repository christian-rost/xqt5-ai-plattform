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
- Offene Risiken (noch kein Fehler):
  1. Auth ist als Basis vorbereitet, aber noch nicht vollständig umgesetzt.
  2. Externer `llm-council`-API-Adapter ist noch nicht umgesetzt.
  3. Supabase RLS-Policies sind noch nicht aktiviert.

## Präventionsmaßnahmen
1. Vor jedem Merge: API-Smoketest, Frontend-Build, Datenbankschema-Check.
2. Jede Produktionsänderung erhält eine kurze Post-Deploy-Checkliste.
3. Bei neu gefundenen Fehlern wird hier ein Eintrag mit Ursache und Fix ergänzt.
