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
1. Echte LLM-Anbindung über direkte Provider-APIs (OpenAI, Anthropic, Google, Mistral, X.AI)
2. Eigene Chat-Tabellen (`chats`, `chat_messages`) — getrennt von llm-council
3. SSE-Streaming mit Coolify-kompatiblen Headers
4. Modellauswahl (Dropdown) und Temperatur-Steuerung (Slider)
5. Auto-Benennung von Konversationen nach erster Nachricht
6. Markdown-Rendering für Assistant-Nachrichten
7. Frontend-Refactor in Component-Architektur (7 Komponenten)

## Phase B: User & Kosten-Management (geplant)
1. Auth-Modul: Register, Login, JWT Refresh
2. Auth-Middleware für geschützte Endpoints
3. User/Gruppen-Verwaltung mit Zugriffsrechten auf Modelle
4. Token-Usage Tracking (Kosten pro Nachricht)
5. Kosten-Dashboard + Budget-Limits

## Phase C: Wissen & Assistenten (geplant)
1. Datei-Upload (PDF, DOCX, TXT)
2. RAG-Pipeline: Chunking, Embeddings, Vektor-Suche
3. Konfigurierbare KI-Assistenten (System-Prompts, Modell-Präferenzen)
4. Prompt-Templates

## Phase D: Enterprise (geplant)
1. Workflow-Engine für automatisierte Abläufe
2. Admin-Dashboard (Policies, Kosten-Metriken, Admin-User)
3. Audit-Logs für Compliance
4. SSO (OIDC/SAML)
