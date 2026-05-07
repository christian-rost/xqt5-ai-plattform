# Implementierte Features

Dieses Dokument hält abgeschlossene Implementierungen aus dem Feature-Backlog fest. Wenn ein Punkt aus `TODO.md` umgesetzt wird, wird er dort entfernt und hierher verschoben — vollständig mit allen technischen Details, sodass keine Information verloren geht.

---

## RAG-Backend — Cherry-picks aus dri-Branch (2026-04-07)

Die folgenden RAG-Verbesserungen wurden aus `xqt5-ai-plattform-dri` in `xqt5-ai-plattform` portiert. Die Portierung erfolgte als gezielte Einzeländerungen, nicht als Bulk-Überschreibung — der dri-Branch hatte UI- und Strukturänderungen (Sidebar-Redesign, NavRail-Entfernung, Provider-Entfernungen, Welcome.jsx-Vereinfachung), die Regressionen darstellen oder keinen Mehrwert für das aktive Repo haben und daher bewusst ausgeschlossen wurden.

> **Kritischer Bugfix enthalten:** Der dri-Branch hat `_reciprocal_rank_fusion()` korrigiert, das den Kosinus-`similarity`-Score mit dem winzigen RRF-Score (0.008–0.016) überschrieben hatte. Dies führte dazu, dass das Relevanzfilter immer `False` auswertete und RAG im Hybrid-Modus still deaktiviert war.

---

### Phase 1.1 — Relevanzfilter (`apply_relevance_gate()`)

- `apply_relevance_gate()` verwirft alle Chunks, wenn `max(similarity) < RAG_RELEVANCE_GATE` (Standard: 0.35)
- Enthält den RRF-Score-Bugfix: separates `rrf_score`-Feld; `similarity` enthält immer den rohen Kosinus-Score
- Dateien: `rag.py`, `config.py` (neues `RAG_RELEVANCE_GATE` Env-Var)

---

### Phase 1.2 — Vollständige Quellenangaben

- `build_rag_context()` gibt Seitenzahl + Abschnitts-Breadcrumb-Pfad im Quell-Header aus
- Format: `datei.pdf | Seite 12 | §3.1 Titel (Relevanz: 87%)`
- `rag_sources`-Array ans Frontend enthält `page_number`, `section_path`, `chunk_index`
- Dateien: `rag.py`, `main.py`

---

### Phase 4.2 — Kontextuelles Retrieval (Anthropic-Technik, opt-in)

- `_generate_chunk_context()` stellt jedem Chunk vor dem Embedding einen per LLM generierten 1-Satz-Kontext voran
- Parallele Batch-Verarbeitung via `asyncio.gather` pro Dokument
- Opt-in: Admin-Toggle `contextual_retrieval_enabled` + konfigurierbares Modell (`contextual_retrieval_model`)
- Gilt nur für neu hochgeladene Dokumente; bestehende Docs benötigen Re-Chunking
- Dateien: `rag.py`, `admin.py`, `models.py`

> **Ausstehend:** `AdminDashboard.jsx` Frontend-Toggles noch nicht hinzugefügt — siehe Backlog.

---

### Phase 4.3 — Dokument-Zusammenfassung beim Upload

- `_summarize_document()` in `main.py` vorhanden, in beiden Upload-Endpunkten eingebunden, befüllt `app_documents.summary`
- Dateien: `main.py`, `documents.py`

---

### Phase 5.1 — Tabellen-bewusstes Chunking

- `_table_to_atoms()` behandelt Markdown-Tabellenblöcke als atomare Einheiten
- Zu große Tabellen werden nur an Zeilengrenzen aufgeteilt; jeder Fortsetzungs-Chunk beginnt mit `[Tabellenfortsetzung — Spalten: …]`
- `_units_with_table_awareness()` ersetzt `_split_into_units()` in der Abschnitts-Splitting-Schleife
- Dateien: `rag.py`

---

### Phase 5.3 — Nachbar-Chunk-Abruf

- `enrich_with_neighbors()` ruft `chunk_index ± 1` für die Top-3-Ergebnisse nach dem Relevanzfilter ab
- Nachbar-Chunks erhalten `similarity = parent_similarity × 0.85` und `is_neighbor = true`
- Ergebnisse sortiert nach `document_id + chunk_index` für sequenzielles Lesen
- Opt-in: Admin-Toggle `neighbor_chunks_enabled` (Standard: true)
- Dateien: `rag.py`, `main.py`, `admin.py`, `models.py`

> **Ausstehend:** `AdminDashboard.jsx` Frontend-Toggle noch nicht hinzugefügt — siehe Backlog.

---

### Phase 7.1 — Token-Budget-Kontextzusammenstellung

- `build_rag_context(max_tokens=6000)` befüllt Chunks nach Relevanz bis das Budget erschöpft ist
- Übersprungene Chunks werden geloggt; verhindert, dass 50-Chunk-Kontext das LLM-Fenster dominiert
- `max_context_tokens` bis 32.000 in den Admin-Einstellungen konfigurierbar
- Dateien: `rag.py`, `main.py`, `admin.py`, `models.py`

> **Ausstehend:** `AdminDashboard.jsx` Frontend-Slider noch nicht hinzugefügt — siehe Backlog.

---

### Phase 7.2 — XML-Kontext-Format

- `build_rag_context()` gibt nun XML-getaggte Blöcke statt `--- Source N ---` aus
- Format gemäß Anthropic-Prompting-Best-Practices:
  ```xml
  <documents>
    <document index="1">
      <source>datei.pdf | Seite 12 | §3.1 Titel (Relevanz: 87%)</source>
      <content>…</content>
    </document>
  </documents>
  ```
- Dateien: `rag.py`

---

### `_apply_document_access_policy()` — Aktualisierte Dokumentzugriffs-Richtlinie

- Vorher (2-teilig): kein Zugriff behaupten + Antwort auf Kontext basieren
- Neu (3-teilig):
  1. Dokumentkontext NUR verwenden, wenn direkt relevant für die Frage des Nutzers
  2. Falls der Nutzer etwas fragt, das nichts mit den Dokumenten zu tun hat, aus eigenem Wissen antworten — Dokumente nicht referenzieren
  3. Antworten auf bereitgestellten Kontext basieren, klar kommunizieren wenn Information fehlt
- Datei: `main.py` → `_apply_document_access_policy()`

---

## Admin-UI Frontend-Toggles (2026-05-06)

Drei Backend-RAG-Settings (Phase 4.2 Contextual Retrieval, Phase 5.3 Nachbar-Chunks, Phase 7.1 Token-Budget) waren am Backend bereits aktiv, aber ohne UI nur über manuelle Bearbeitung der `app_runtime_config.rag_settings`-JSONB-Zeile zu ändern. Die Toggles wurden im `RetrievalTab` von `AdminDashboard.jsx` ergänzt: Neue `<hr>`-getrennte Sektionen "Kontextzusammenstellung" und "Kontextuelles Retrieval", form-state + GET/PUT-Mappings + footer-Zusammenfassung, alle vier neuen Felder (`contextual_retrieval_enabled`, `contextual_retrieval_model`, `neighbor_chunks_enabled`, `max_context_tokens`) verwenden snake_case wie das Backend-Pydantic-Modell.

**i18n-Vorbereitung:** Erstmaliger Einsatz eines minimalen i18n-Helpers `frontend/src/i18n/strings.js` mit `t(key)`-Funktion und Deutsch-Default-Dict. Alle neuen UI-Strings laufen darüber statt hartcodiert in JSX zu landen — bestehende hartcodierte deutsche Strings bleiben unverändert (Refactor wäre eigene Aufgabe).

Dateien: `frontend/src/components/AdminDashboard.jsx`, `frontend/src/i18n/strings.js` (neu)

---

## Content-Hash Upload-Deduplikation (A1, 2026-05-06)

Verhindert OCR + Embedding-Recompute, wenn ein Nutzer dieselbe Datei zweimal hochlädt.

- SHA-256-Hex der hochgeladenen Bytes wird beim Upload berechnet (`compute_file_hash()` in `documents.py`)
- Vor OCR wird in `app_documents` gegen den Hash geprüft (`find_existing_document_by_hash()`); Match → bestehender Datensatz wird zurückgegeben, Audit-Log-Event `document.upload.dedup_skipped` geschrieben
- Scope-Regeln: pool-weit wenn `pool_id` gegeben, sonst per-User mit `chat_id` als zusätzlichem Filter wenn vorhanden
- Migration `supabase/migrations/20260506_a_content_hash.sql`: `content_hash TEXT` Spalte plus zwei partielle composite indexes (`(pool_id, content_hash)` und `(user_id, content_hash)`, jeweils `WHERE content_hash IS NOT NULL`)
- `create_document()` Signatur um `content_hash: Optional[str] = None` erweitert; bestehende Aufrufer unverändert
- Audit-Konstante `DOCUMENT_UPLOAD_DEDUP_SKIPPED` in `audit.py`
- Wiring in beiden Upload-Routen (`upload_document` und `upload_pool_document` in `main.py`)
- **Status:** Code deployed und Migration auf dev angewendet 2026-05-06; prod-Migration noch ausstehend bis bewusste Freigabe

Dateien: `supabase/migrations/20260506_a_content_hash.sql`, `backend/app/documents.py`, `backend/app/audit.py`, `backend/app/main.py`

---

## DB-Sicherheits-Härtung — Anon + Authenticated Rolle revoked (2026-05-06)

Supabase Studio Security Advisor meldete ~30 Warnungen, die meisten "RLS not enabled" auf `public`-Tabellen. Verifikation per curl mit dem Anon-JWT auf prod ergab: Anon hatte tatsächlich Lesezugriff auf alle `app_*` und `pool_*` Tabellen inklusive `app_users.password_hash` und `pool_invite_links.token`. Da der Anon-Key bei Supabase als „öffentlich teilbar" konzipiert ist, war das eine reale Datenexposition.

- Migration `20260506_b_revoke_anon_public.sql`: `REVOKE ALL` auf TABLES/SEQUENCES/FUNCTIONS in `public` für `anon`, plus `ALTER DEFAULT PRIVILEGES FOR ROLE postgres, supabase_admin` analog für künftige Objekte
- Migration `20260507_revoke_authenticated_public.sql`: identische Behandlung für die `authenticated`-Rolle, da dieselbe Bug-Klasse via JWT mit `role: authenticated` ausnutzbar wäre
- `service_role` blieb unangetastet — der Backend hängt davon ab
- Verifikation: nach Anwendung liefert dieselbe curl auf alle 6 getesteten Tabellen `HTTP 401 42501 permission denied`. App funktioniert unverändert (Backend nutzt service-role)
- **Status:** beide Migrationen auf prod angewendet 2026-05-06; dev hat aktuell keine Anon/Authenticated-Rollen exponiert, dort idempotent ausstehend

Vollständiges Bedrohungsmodell, offene Lücken und Verifikationsbefehle: `docs/SECURITY.md` (neu, kanonischer Sicherheits-Track-Record).

Dateien: `supabase/migrations/20260506_b_revoke_anon_public.sql`, `supabase/migrations/20260507_revoke_authenticated_public.sql`, `docs/SECURITY.md`

---

## Bild-pHash Deduplikation (A2, 2026-05-06)

Verhindert, dass dasselbe Logo, der Briefkopf oder ein wiederkehrendes Header-Bild eines mehrseitigen PDFs als N separate Asset-Zeilen abgelegt und N-mal aus RAG zurückgegeben wird.

- `compute_phash()` in `documents.py` berechnet 64-bit perzeptuellen Hash via `imagehash.phash()` über `PIL.Image`. Schutz gegen Decompression-Bombs: `Image.MAX_IMAGE_PIXELS = 50_000_000` auf Modulebene + 20-MB Byte-Cap im Helper + try/except auf `DecompressionBombError` und `UnidentifiedImageError`
- `_mark_recurring_by_phash()` läuft am Ende von `_extract_image_assets_from_pages()` über die gesammelten `embedded_image`-Assets, dekodiert die Data-URI, vergleicht jeden Hash gegen alle bisher als „Canonical" markierten via Hamming-Distanz. Threshold = 4 (innerhalb desselben Dokuments hashen Logo-Crops typisch bei 0–2; 4 ist eng genug um verschiedene Diagramme nicht fälschlich zu mergen)
- Erste Vorkommen pro Cluster bleiben mit `recurring=False` als kanonisch erhalten; nachfolgende werden `recurring=True` markiert
- `upload_image`-Assets werden übersprungen (Einzelnutzer-Upload, kein Dedup-Ziel); `page_image` wird vom Code derzeit nicht geschrieben
- `create_document_assets()` erweitert die Insert-Zeile um `phash` und `recurring`
- Migration `supabase/migrations/20260506_c_asset_phash_recurring.sql`: `phash TEXT` und `recurring BOOLEAN NOT NULL DEFAULT FALSE` auf `app_document_assets`, plus partieller Index `(document_id, phash) WHERE phash IS NOT NULL`. `match_document_assets`-RPC mit unverändertem Signaturen-Layout neu definiert (3-Branch IF/ELSIF/ELSE pool/chat/global), in jedem Branch Filter `AND a.recurring = FALSE`
- Neue Python-Dependencies `Pillow>=10.0.0` und `imagehash>=4.3.1` in `pyproject.toml` und `Dockerfile` pip-install-Zeile (manylinux-wheels verfügbar, kein apt-get nötig auf python:3.11-slim)
- **Cross-Document-Dedup ist ausdrücklich nicht implementiert** — würde tenant-scoped phash-Index oder kanonische Asset-Tabelle benötigen, ist als Future-Work in `docs/TODO.md` zu vermerken
- **Status:** Code zum Commit fertig; Migration noch nicht angewendet (gleicher Workflow wie A1: paste-in-Studio auf dev, dann prod nach Bedarf)

Dateien: `supabase/migrations/20260506_c_asset_phash_recurring.sql`, `backend/app/documents.py`, `backend/pyproject.toml`, `backend/Dockerfile`

---

## Pool-UI: Persistenter Header + Übersichts-Seite (2026-05-06)

Bisher musste man Tabs (Dokumente / Chats / Mitglieder) wechseln um zu sehen wer im Pool ist oder welche Chats existieren. Beim Öffnen eines Chats verlor man auch jeglichen Pool-Kontext. Zwei UI-Verbesserungen, frontend-only, kein Backend nötig (alle Endpunkte existieren bereits):

**Persistenter Pool-Header** — `frontend/src/components/PoolHeader.jsx` (neu): kompakter Streifen über jedem Pool-Inhalt (auch in offenen Chats), zeigt Pool-Icon, Name, Beschreibung, Avatar-Reihe der ersten 5 Mitglieder mit `+N`-Overflow, sowie klickbare Counts für Dokumente/Chats/Mitglieder. Klick auf Avatar oder Count → `onTabChange()`. Die Komponente hat null-safety für fehlendes Icon, fehlende Beschreibung und kürzere Mitgliederlisten.

**Übersichts-Tab als neuer Default** — `frontend/src/components/PoolOverview.jsx` (neu): Landing-Seite beim Öffnen eines Pools mit vier Karten-Sektionen: Pool-Zusammenfassung, Mitglieder-Vorschau (5 + „Alle anzeigen"), zuletzt erstellte Chats (5), zuletzt hochgeladene Dokumente (5). Jede Sektion hat Empty-State und „Alle anzeigen"-Button der zum entsprechenden Tab wechselt.

Wiring: `Sidebar.jsx` bekommt eine neue `IconOverview`-Komponente und einen vierten Tab-Button (vor Documents/Chats/Members) ohne Count-Badge. `App.jsx` setzt `setPoolTab('overview')` beim Pool-Öffnen statt vorher `'chats'`. `PoolDetail.jsx` rendert `PoolHeader` immer als ersten Flex-Child von `.pool-detail` und `PoolOverview` wenn `activeTab === 'overview'`. `.pool-detail` ist bereits `display: flex; flex-direction: column; overflow: hidden` — keine CSS-Anpassung am Layout nötig, der Chat-Bereich flext sich korrekt unter dem Header ein.

i18n: 19 neue Keys unter `pool.header.*`, `pool.overview.*`, `pool.tab.overview` in `frontend/src/i18n/strings.js`. Alle UI-Strings laufen durch den `t()`-Helper, kein hartcodierter Text in JSX.

Dateien: `frontend/src/components/PoolHeader.jsx` (neu), `frontend/src/components/PoolOverview.jsx` (neu), `frontend/src/components/PoolDetail.jsx`, `frontend/src/components/Sidebar.jsx`, `frontend/src/App.jsx`, `frontend/src/styles.css`, `frontend/src/i18n/strings.js`
