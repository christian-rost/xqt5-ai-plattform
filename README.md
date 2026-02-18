# XQT5 AI Plattform

Grundgerüst für eine AI-Hub-Anwendung mit:
- Frontend: React + Vite
- Backend: FastAPI
- DB: Supabase Postgres
- Deployment: Coolify mit 2 getrennten Services/Containern

## Architekturvorgabe
- Es werden keine Funktionen aus `llm-council` in dieses Repository übernommen.
- Falls Funktionen aus `llm-council` benötigt werden, erfolgt die Nutzung ausschließlich über externe API-Aufrufe.

## Projektstruktur
- `frontend/` React/Vite App (Component-Architektur unter `src/components/`)
- `backend/` FastAPI API (LLM-Provider unter `app/llm.py`)
- `supabase/migrations/` SQL-Migrationen
- `docs/` Produkt-, Umsetzungs- und Coding-Dokumentation
  - Anwender-Doku: `docs/ANWENDER-DOKUMENT.md`
  - Anwender-Quickstart: `docs/ANWENDER-QUICKSTART.md`

## Features (Phase A)
- Multi-Provider LLM Chat (OpenAI, Anthropic, Google, Mistral, X.AI)
- SSE-Streaming mit Echtzeit-Anzeige
- Modellauswahl und Temperatur-Steuerung
- Auto-Benennung von Konversationen
- Markdown-Rendering für Assistant-Nachrichten

## Lokaler Start

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Coolify Deployment

### Backend-Service
- Build Context: `/backend`, Dockerfile: `Dockerfile`, Port: `8001`
- Required env: `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET`, `CORS_ORIGINS`
- Provider Keys (min. 1): `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`
- Optional: `DEFAULT_MODEL`, `DEFAULT_TEMPERATURE`

### Frontend-Service
- Build Context: `/frontend`, Dockerfile: `Dockerfile`, Port: `80`
- Build-Arg: `VITE_API_BASE=https://api.xqtfive.com`

## Datenbank
Migrationen in Reihenfolge im Supabase SQL Editor ausführen:
1. `supabase/migrations/20260214_initial_schema.sql` — Basis-Schema (users, llm-council-Tabellen, settings)
2. `supabase/migrations/20260215_phase_a_model_temperature.sql` — Eigene Chat-Tabellen (chats, chat_messages)
