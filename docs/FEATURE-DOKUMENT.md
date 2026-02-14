# Feature-Dokument

## Produktziel
Eine Enterprise-fähige AI-Hub-Plattform mit Multi-LLM-Orchestrierung, zentralem Wissenszugriff, Workflows und Governance.

## MVP-Funktionen (Phase 1)
1. Chat mit Konversationsverwaltung (Erstellen, Laden, Löschen)
2. Persistenz in Supabase (`conversations`, `messages`)
3. Basale Rollen-/Auth-Vorbereitung (`users`, JWT-Basis im Backend)
4. API-Struktur für spätere Stage-Logik (Stage 1/2/3)
5. Grundlegendes Kosten-/Nutzungstracking-Schema (`token_usage`)
6. Bereitstellung auf Coolify mit getrenntem Frontend-/Backend-Service

## Ausbau-Funktionen (Phase 2)
1. Multi-LLM Council Pipeline (parallelisierte Modellantworten + Ranking + Synthesis)
2. Provider-Key-Management und API-Key-Management
3. Prompt-Templates und Assistentenprofile
4. Dokumenten-Upload und RAG (Chunking, Embeddings, Retrieval)
5. Team- und Tenant-Fähigkeit inkl. RLS

## Enterprise-Funktionen (Phase 3)
1. Workflow-Engine und Agent-Tools
2. Admin-Dashboard für Policies, Kosten, Qualitätsmetriken
3. Audit-Logs, DLP/PII-Filter, Retention-Policies
4. SSO (OIDC/SAML) und feinere RBAC-Rechte
