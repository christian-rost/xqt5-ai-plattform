# XQT5 AI Plattform

Grundgerüst für eine AI-Hub-Anwendung (ähnlich neuland.ai Hub) mit:
- Frontend: React + Vite
- Backend: FastAPI
- DB: Supabase Postgres
- Deployment: Coolify mit 2 getrennten Services/Containern

## Projektstruktur
- `frontend/` React/Vite App
- `backend/` FastAPI API
- `supabase/migrations/` SQL-Migrationen
- `docs/` Produkt-, Umsetzungs- und Coding-Dokumentation

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
- Build Context: `/backend`
- Dockerfile: `Dockerfile`
- Port: `8001`
- Required env: `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET`, `CORS_ORIGINS`

### Frontend-Service
- Build Context: `/frontend`
- Dockerfile: `Dockerfile`
- Port: `80`
- Env: `VITE_API_BASE=https://<dein-backend-domain>`

## Datenbank
- Migration ausführen: `supabase/migrations/20260214_initial_schema.sql`
