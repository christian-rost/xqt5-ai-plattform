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

## Phase C: Wissen & Assistenten (Schritt 1 umgesetzt 2026-02-16)
### Schritt 1: KI-Assistenten + Prompt-Templates (umgesetzt)
1. Konfigurierbare KI-Assistenten (System-Prompts, Modell/Temperature-Override, Icons)
2. Globale Assistenten (nur Admins) + persönliche Assistenten
3. System-Prompt Injection bei Chat mit Assistent
4. Prompt-Templates mit Platzhalter-Syntax ({{variable}})
5. Template-Picker in Message-Input
6. Assistenten-Selector in Sidebar + Manager-Modal
7. Template-Manager-Modal
### Schritt 2: File Upload + RAG-Pipeline (geplant)
1. Datei-Upload (PDF, DOCX, TXT)
2. RAG-Pipeline: Chunking, Embeddings (pgvector), Vektor-Suche
3. Kontext-Injection bei Nachrichten

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
### Noch geplant
1. Workflow-Engine für automatisierte Abläufe
2. SSO (OIDC/SAML)
