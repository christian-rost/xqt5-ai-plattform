# Feature-Dokument

## Produktziel
Eine Enterprise-fähige AI-Hub-Plattform mit Multi-LLM-Orchestrierung, zentralem Wissenszugriff, Workflows und Governance.

## Verbindliche Scope-Regel
1. Es wird keine Funktion aus `llm-council` in den Hub-Code übernommen.
2. Benötigte Fähigkeiten von `llm-council` werden nur über eine externe API-Integration genutzt.

## Phase 0: MVP (umgesetzt 2026-02-14)
1. Chat mit Konversationsverwaltung (Erstellen, Laden, Löschen)
2. Persistenz in Supabase (llm-council-Tabellen: `conversations`, `messages`)
3. Basale Rollen-/Auth-Vorbereitung (`users`, JWT-Basis im Backend)
4. Grundlegendes Kosten-/Nutzungstracking-Schema (`token_usage`)
5. Bereitstellung auf Coolify mit getrenntem Frontend-/Backend-Service

## Phase A: Core Chat Enhancement (umgesetzt 2026-02-15)
1. Echte LLM-Anbindung über direkte Provider-APIs (OpenAI, Anthropic, Google, Mistral, X.AI, Azure OpenAI)
2. Eigene Chat-Tabellen (`chats`, `chat_messages`) — getrennt von llm-council
3. SSE-Streaming mit Coolify-kompatiblen Headers
4. Modellauswahl (Dropdown) und Temperatur-Steuerung (Slider)
5. Auto-Benennung von Konversationen nach erster Nachricht
6. Markdown-Rendering für Assistant-Nachrichten
7. Frontend-Refactor in Component-Architektur (7 Komponenten)

## Phase B: User & Kosten-Management (umgesetzt 2026-02-15)
1. Eigene `app_users` Tabelle (komplett getrennt von llm-council `users`)
2. Auth-Modul: Register, Login, JWT Access (30min) + Refresh (7d)
3. Alle Conversation-Endpoints geschützt mit Ownership-Check
4. Token-Usage Tracking in eigener `chat_token_usage` Tabelle (Kosten pro Anfrage)
5. Usage-Widget in Sidebar (Tokens, Kosten, Anfragen)
6. Login-/Register-Screen im Frontend
7. Einfaches Admin vs. Normaluser (Gruppen auf Phase D verschoben)

## Phase C: Wissen & Assistenten (umgesetzt 2026-02-16)
### Schritt 1: KI-Assistenten + Prompt-Templates (umgesetzt)
1. Konfigurierbare KI-Assistenten (System-Prompts, Modell/Temperature-Override, Icons)
2. Globale Assistenten (nur Admins) + persönliche Assistenten
3. System-Prompt Injection bei Chat mit Assistent
4. Prompt-Templates mit Platzhalter-Syntax ({{variable}})
5. Template-Picker in Message-Input
6. Assistenten-Selector in Sidebar + Manager-Modal
7. Template-Manager-Modal
### Schritt 2: File Upload + RAG-Pipeline (umgesetzt 2026-02-16)
1. Datei-Upload (PDF, TXT, PNG, JPG, JPEG, WEBP) pro Chat (API-seitig optional auch ohne Chat-ID)
2. Text-Extraktion via Mistral OCR API (PDF/Bild) bzw. UTF-8 (TXT)
3. Paragraph-aware Chunking mit konfigurierbarer Größe und Overlap
4. OpenAI Embeddings (text-embedding-3-small, 1536 Dimensionen)
5. pgvector HNSW-Index für schnelle Cosine-Similarity-Suche
6. Automatische RAG-Kontext-Injection in Chat-Nachrichten
7. Source-Attribution unter Assistant-Antworten
8. Upload-Button, Document-Tags, Source-Tags im Frontend

## Phase D: Enterprise (teilweise umgesetzt 2026-02-16)
### Admin-Dashboard + Audit-Logs (umgesetzt)
1. Admin-Dashboard mit Tab-Navigation (Benutzer, Kosten, Statistiken, Modelle, Audit-Logs, Provider)
2. Benutzer-Verwaltung: Active/Admin-Toggle mit Selbstschutz
3. Kosten-Dashboard: Globale Totals + Per-User Aufschlüsselung
4. System-Statistiken: Users, Chats, Messages, Assistenten, Templates
5. Modell-Konfiguration via DB (app_model_config) statt hardcoded — Enable/Disable, Default
6. Audit-Logs: Auth-, Admin-, Chat-Events mit fire-and-forget Logging
7. Paginierte Audit-Log-Anzeige mit Aktions-Filter
### Provider-Key-Verwaltung + Azure OpenAI (umgesetzt)
1. DB-verwaltete Provider API-Keys (Fernet-verschlüsselt) mit Env-Fallback
2. Admin-UI: Provider-Keys Tab mit Save/Delete/Test pro Provider
3. Azure OpenAI als LLM-Provider (Deployment-Name Lookup, GPT-5.x Handling)
4. Azure-spezifische Konfiguration (Endpoint-URL, API-Version) in DB und UI
5. Deployment-Name Spalte in Modell-Konfiguration für Azure-Modelle
### Security Hardening (umgesetzt 2026-02-17)
1. Rate Limiting pro Endpoint (per-User bei gültigem Token, per-IP als Fallback)
2. Redis-backed Rate Limit Storage (Fallback: In-Memory)
3. Token Version Revocation für sofortige Session-Invalidierung bei User-Deaktivierung
4. is_active Prüfung auf allen Auth-Flows (Access-Token UND Refresh-Token)
5. Proxy-Header-Konfiguration für korrekte IP-Erkennung hinter Reverse-Proxy
### Admin User Löschen + Default-Modell Fix (umgesetzt 2026-02-17)
1. Admin User Soft-Delete (is_active=false + Session-Invalidierung) via DELETE Endpoint
2. Selbstschutz: Admin kann sich nicht selbst löschen
3. Deaktivierte User standardmäßig ausgeblendet, mit Toggle einblendbar (grau dargestellt)
4. Default-Modell aus DB (`is_default` in `app_model_config`) wird jetzt vom Frontend respektiert
## Phase E: Pools — Geteilte Dokumentensammlungen (umgesetzt 2026-02-18)
Pools sind geteilte Dokumentensammlungen, in denen mehrere Nutzer Dokumente ablegen und per Chat RAG-gestützte Fragen dazu stellen können.

### Kernfeatures
1. Pool erstellen mit Name, Beschreibung, Icon und Farbe
2. Dokumente in Pool hochladen (PDF, TXT, PNG, JPG, JPEG, WEBP) — Chunking + Embedding wie bei bestehender RAG-Pipeline
3. 4-stufiges Berechtigungsmodell: Viewer (lesen + fragen), Editor (+ Dokumente verwalten), Admin (+ Mitglieder verwalten), Owner (implizit, immer Admin)
4. Mitglieder einladen per Username (Admin+)
5. Share-Link generieren mit Rolle und optionalem Limit (max Uses, Ablaufdatum)
6. Shared Pool-Chat: Alle Mitglieder sehen denselben Chatverlauf mit RAG-Kontext
7. Private Pool-Chats: Jeder Nutzer kann eigene private Chats gegen Pool-Dokumente führen
8. RAG-Suche auf Pool-Scope (nur Dokumente des Pools, nicht des Users)
9. Source-Attribution in Pool-Chats
10. Dokumentvorschau im Pool-Dokumenttab (Textvorschau für PDF/TXT, Bildvorschau für Bild-Uploads)

### Neue Tabellen
- `pool_pools` — Pool-Metadaten + owner_id
- `pool_members` — Mitgliedschaften mit Rolle (UNIQUE pool_id + user_id)
- `pool_invite_links` — Share-Links mit Token, Rolle, max_uses, expires_at
- `pool_chats` — Chats (shared + private via is_shared Flag)
- `pool_chat_messages` — Nachrichten mit user_id
- `app_documents` erweitert um `pool_id` Spalte

### Neue Backend-Module
- `pools.py` — Pool CRUD, Members, Invites, Chats, Dokumentvorschau
- API-Endpunkte unter `/api/pools/...` inkl. Dokumentvorschau

### Neue Frontend-Komponenten
- PoolList, CreatePoolDialog, PoolDetail (Tabs: Dokumente/Chats/Mitglieder)
- PoolDocuments, PoolChatList, PoolChatArea, PoolMembers, PoolShareDialog

### Phase E Update: Pool-Dokumentvorschau (umgesetzt 2026-02-19)
1. Neuer API-Endpunkt: `GET /api/pools/{pool_id}/documents/{document_id}/preview`
2. Rollenmodell: Zugriff ab Pool-Rolle `viewer`
3. Rückgabe enthält gekürzte Textvorschau (`text_preview`) inkl. Längen-/Truncation-Info
4. Für Bild-Dokumente wird optional `image_data_url` aus `app_document_assets` geliefert
5. Frontend: `PoolDocuments` ergänzt um Vorschau-Button und Modal

## Phase RAGplus: RAG-Qualitätsverbesserungen + UX (umgesetzt 2026-02-22)

### Verbessertes Chunking (Ansatz A+B)
1. **Markdown-Section-aware Chunking**: Überschriften erkennen, Sektionsgrenzen respektieren, Breadcrumb-Header in jeden Chunk einbetten
2. **Token-basierte Chunk-Größe**: 512 Tokens (statt 1500 Zeichen), 50 Tokens Overlap — präzise Größenkontrolle via tiktoken
3. **Sentence Boundary Respect**: Chunks werden an Satzgrenzen aufgeteilt, keine abgeschnittenen Sätze
4. **Admin Re-Chunk Feature**: Bestehende Dokumente per Knopfdruck mit der neuen Strategie neu chunken — mit Live-Fortschrittsanzeige im Admin-Dashboard

### BM25 via PostgreSQL Full-Text Search
5. **BM25-Suche**: Ersetzt ILIKE-Keyword-Supplement durch native PostgreSQL FTS (`tsvector` GENERATED STORED, GIN-Index, `websearch_to_tsquery('german', ...)`, `ts_rank_cd`)
6. **Reciprocal Rank Fusion (RRF)**: Vector-Suche und BM25-Suche werden per RRF (k=60) zu einem gemeinsamen Ranking kombiniert — robuster als reine Score-Addition
7. **Keine Extension nötig**: `tsvector` / GIN / `ts_rank_cd` sind built-in PostgreSQL — Supabase-kompatibel ohne zusätzliche Extensions

### UX-Verbesserungen
8. **Sidebar 50:50 Split**: Pools und Conversations teilen sich den Sidebar-Platz 50:50 — beide Sektionen sind gleichzeitig sichtbar und scrollen unabhängig
9. **Drag-to-Resize Sidebar**: Ziehbarer Divider zwischen Pools und Conversations für individuelle Aufteilung (15-80%)
10. **Upload-Fortschrittsanzeige**: Echtzeit-Fortschrittsbalken beim Hochladen (File-Transfer % + Server-Processing-Shimmer) — Chat und Pool

## Noch geplant

### Tabellen-Extraktion & strukturierte Abfragen (SDE — Structured Data Extraction)

**Motivation**: Hochgeladene Dokumente (Rechnungen, Berichte, Listen) enthalten häufig Tabellen mit numerischen Werten. Heute landen diese als Fließtext im RAG-Chunk — Berechnungen wie "Summe aller Rechnungen im Januar" sind so nicht zuverlässig möglich.

**Konzept**:
1. **Erkennung & Extraktion**: Beim Upload werden Markdown-Tabellen aus dem OCR-Output geparst (Mistral OCR liefert Tabellen bereits als `| Spalte | Wert |`). Ein LLM-Schritt kann zusätzlich unstrukturierte Tabellen normalisieren.
2. **Strukturierte Speicherung**: Neue Tabelle `app_document_tables` speichert Tabellen pro Dokument:
   - `headers` (JSONB): Spaltenbezeichnungen, z. B. `["Datum", "Betrag", "Beschreibung"]`
   - `rows` (JSONB): Zeilendaten, z. B. `[["01.01.2026", "150.00", "Beratung"], ...]`
   - `page_number`, `table_index`, `caption`, `raw_markdown`
3. **Abfragen — zwei Ansätze**:
   - **Direkt via SQL/JSONB**: Aggregationen wie `SUM`, `AVG`, `COUNT` direkt in PostgreSQL auf den JSONB-Daten
   - **Text-to-SQL**: Nutzer stellt Frage in natürlicher Sprache → LLM generiert SQL-Query auf den Tabellendaten → Ergebnis wird zurückgegeben
4. **Integration in Chat-RAG**: Bei Zahlen-/Berechnungsfragen werden automatisch Tabellendaten statt (oder zusätzlich zu) Text-Chunks einbezogen; Ergebnis erscheint als Antwort mit Quellenangabe (Dokument + Tabellenposition)

**Beispiel-Flow**:
> Upload: 12 Rechnungs-PDFs → Tabellen extrahiert und gespeichert
> User: *"Wie hoch ist die Gesamtsumme der Rechnungen im Januar 2026?"*
> System: Tabellendaten abfragen → `SELECT SUM(betrag::numeric) WHERE datum LIKE '01/2026%'` → *"Gesamtsumme Januar 2026: 4.320,00 €"* (Quellen: Rechnung-001.pdf, Rechnung-003.pdf, ...)

**Scope-Unterstützung**: Funktioniert für eigene Dokumente (Conversation-Scope), Pool-Dokumente und globale Dokumente — analog zur bestehenden RAG-Scope-Logik.

**Technische Abhängigkeiten**: Neue Migration `app_document_tables`, erweiterter Upload-Flow, optionaler LLM-Schritt für Tabellennormalisierung, Text-to-SQL-Modul im Backend.

### Dokumente & Wissensmanagement

**Automatische Zusammenfassung beim Upload**
Beim Indexieren wird direkt eine LLM-generierte Kurzzusammenfassung gespeichert. Sichtbar im Dokument-Tab und optional als zusätzlicher RAG-Kontext ("Was ist der Inhalt dieses Dokuments?"). Geringer Mehraufwand: ein LLM-Call beim Upload.

**Dokument-Tagging**
Manuell vergebene oder LLM-automatisch generierte Tags pro Dokument (z. B. "Rechnung", "Vertrag", "Protokoll"). Ermöglicht gefilterte RAG-Suche: "Suche nur in Rechnungen" oder "Suche nur in Dokumenten aus 2025".

**Dokumentversionen**
Bei erneutem Upload eines Dokuments mit identischem Dateinamen wird die alte Version archiviert statt überschrieben. Versionsverlauf im UI einsehbar; ältere Versionen können aus dem RAG-Index ausgeschlossen werden.

**Ablaufdatum für Dokumente**
Dokumente können mit einem Ablaufdatum versehen werden (z. B. Preislisten, temporäre Richtlinien). Nach Ablauf werden sie automatisch aus dem RAG-Index deaktiviert und im UI als "abgelaufen" markiert.

---

### Chat & RAG

**Zitatmodus (erweiterte Source-Attribution)**
RAG-Antworten enthalten nicht nur den Dateinamen als Quelle, sondern exakte Textzitate mit Seitenangabe. Erweiterung der bestehenden `SourceDisplay`-Komponente; geringer Mehraufwand.

**Lücken-Erkennung (Knowledge Gap Detection)**
Das System erkennt, wenn Fragen wiederholt keine guten RAG-Treffer liefern, und meldet im Admin-Dashboard: "Zu folgenden Themen fehlen Dokumente." Basis: niedrige Similarity-Scores als Signal.

**Einzeldokument-Fokus**
Nutzer kann einen Chat explizit auf ein bestimmtes Dokument beschränken ("Nur dieses Dokument befragen"). Filtert die RAG-Suche hart auf `document_id`, ignoriert alle anderen Dokumente.

**Konversations-Export**
Chat-Verlauf als PDF oder Markdown exportieren — inkl. Quellenhinweisen. Weitgehend Frontend-seitig umsetzbar (kein neues Backend-Modul nötig).

---

### Zusammenarbeit

**Konversation teilen**
Read-only Deeplink auf eine Konversation — ähnlich wie bei anderen Chat-Tools. Empfänger sieht den Verlauf ohne eigenen Account (oder mit, je nach Konfiguration).

**Pool-Benachrichtigungen**
Pool-Mitglieder erhalten eine Benachrichtigung (In-App oder E-Mail), wenn neue Dokumente hochgeladen oder Pool-Chats aktualisiert werden.

**Kommentare auf Nachrichten**
Nutzer können KI-Antworten annotieren oder mit Kommentaren versehen — für interne Qualitätssicherung oder Teamdiskussion zu einem bestimmten Ergebnis.

---

### Automatisierung

**E-Mail-Eingang als Dokument**
E-Mails an eine dedizierte Adresse werden automatisch als Dokument in einen konfigurierten Pool verarbeitet (Text + Anhänge). Ermöglicht passiven Wissensaufbau ohne manuellen Upload.

**Webhooks**
Externe Systeme bei Ereignissen benachrichtigen (z. B. "Dokument verarbeitet", "neue Pool-Nachricht"). Konfigurierbar pro Pool oder global im Admin-Dashboard.

**Workflow-Engine**
Automatisierte mehrstufige Abläufe: Dokument eingeht → Zusammenfassung erstellen → Ergebnis in Pool-Chat posten → Webhook auslösen. Visueller Editor für Workflows geplant.

**Geplante Neuverarbeitung**
Dokumente zu einem definierten Zeitpunkt automatisch neu chunken und reindexieren (z. B. täglich für Live-Feeds oder nach Modell-Updates).

---

### Analytics & Qualität

**Abfrage-Analytics**
Welche Themen werden am häufigsten gefragt, welche Dokumente am häufigsten abgerufen — sichtbar im Admin-Dashboard als Nutzungsstatistik.

**RAG-Qualitätsmetrik**
Durchschnittliche Similarity-Scores und Retrieval-Trefferquote über die Zeit. Gibt Hinweise ob neue Dokumente oder ein Re-Chunk nötig ist.

**Kostenaufschlüsselung nach Pool**
Im Admin-Dashboard: welcher Pool verursacht wie viele Embedding- und LLM-Kosten — für interne Verrechnung oder Budgetkontrolle.

---

### KI-Features

**Agent-Modus**
LLM plant selbst mehrstufige Aufgaben: recherchieren (RAG), berechnen (SDE/Tabellen), zusammenfassen, Ergebnis formatieren — ohne dass der Nutzer jeden Schritt vorgibt. Basis für komplexe Assistenten-Workflows.

**Auto-Tagging**
LLM vergibt beim Upload automatisch Kategorien und Tags basierend auf dem extrahierten Text. Kann manuell überschrieben werden.

**Übersetzung**
Dokumente oder Chat-Antworten on-the-fly übersetzen. Wahlweise beim Upload (Dokument wird auf Deutsch indexiert unabhängig der Originalsprache) oder im Chat ("Antworte auf Englisch").

---

### Enterprise & Compliance

**Abteilungs-/Team-Hierarchie**
Nutzer in Abteilungen organisieren; Pools können auf Abteilungsebene sichtbar oder eingeschränkt sein. Erleichtert Governance in größeren Organisationen.

**DSGVO-Tools**
Nutzer-Daten-Export (alle Konversationen, Dokumente, Nutzungsdaten) und vollständige Löschung auf Anfrage — als Admin-Funktion oder Self-Service.

**Compliance-Modus**
Konfigurierbar: bestimmte LLM-Provider sperren (z. B. nur EU-Hosting), Datenverarbeitung auf definierten Standort beschränken, Audit-Pflicht für alle KI-Antworten.

**SSO (OIDC/SAML)**
Anbindung an Unternehmens-Identity-Provider (Azure AD, Okta, Google Workspace) für Single Sign-On und automatische Rollenvergabe.
