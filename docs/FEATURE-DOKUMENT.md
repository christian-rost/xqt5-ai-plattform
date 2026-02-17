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
1. Datei-Upload (PDF, TXT) pro Chat oder als globale Wissensbasis
2. Text-Extraktion via pypdf (PDF) / UTF-8 (TXT)
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
### Noch geplant
1. Workflow-Engine für automatisierte Abläufe
2. SSO (OIDC/SAML)
