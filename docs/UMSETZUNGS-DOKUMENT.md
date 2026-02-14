# Umsetzungs-Dokument

## Zielarchitektur
1. Frontend-Service (React/Vite, statisch via Nginx)
2. Backend-Service (FastAPI/Uvicorn)
3. Supabase (Postgres) als zentrale Datenbank
4. Coolify als Orchestrierungs- und Deployment-Ebene

## Technische Entscheidungen
1. Trennung in zwei Container für unabhängige Deployments und Skalierung
2. Supabase als Managed Postgres für schnelle Time-to-Market
3. FastAPI wegen guter API-Performance und klarer Pydantic-Validierung
4. React/Vite wegen schneller Build- und Dev-Zyklen
5. Externe Kopplung zu `llm-council` nur per HTTP-API, keine Funktions- oder Codeübernahme

## Implementierte Artefakte
1. Backend-Grundstruktur unter `backend/app`
2. Frontend-Grundstruktur unter `frontend/src`
3. Container-Builds:
   - `backend/Dockerfile`
   - `frontend/Dockerfile`
4. Supabase-Migration:
   - `supabase/migrations/20260214_initial_schema.sql`
5. Env-Vorlage:
   - `.env.example`

## Coolify Setup-Schritte
1. Repo in Coolify verbinden
2. Service A erstellen:
   - Build Context: `backend`
   - Dockerfile: `backend/Dockerfile`
   - Domain: `api.<deine-domain>`
   - Umgebungsvariablen setzen
3. Service B erstellen:
   - Build Context: `frontend`
   - Dockerfile: `frontend/Dockerfile`
   - Domain: `app.<deine-domain>`
   - `VITE_API_BASE=https://api.<deine-domain>` setzen
4. `CORS_ORIGINS` im Backend auf Frontend-Domain setzen
5. Supabase-Migration einmalig ausführen

## Nächste Umsetzungsschritte
1. Echte Auth-Flows (Register/Login/JWT Refresh) fertigstellen
2. Adapter-Endpunkte für externe `llm-council`-API bauen (Timeouts, Retries, Fehlerabbildung)
3. Streaming-Endpunkte (SSE) hinzufügen
4. RLS und Mandantenmodell in Supabase aktivieren
5. Integrationstests für API und End-to-End-Chat bauen
