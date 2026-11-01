# Afromind LUNA AI

**LUNA AI — The Intelligence.** A public, multi-model AI chat platform by Afromind Tech.

This repository contains a runnable MVP foundation:
- Next.js + TypeScript + Tailwind frontend
- FastAPI backend
- Provider-independent LLM adapter layer (OpenAI-compatible API adapter included)
- SQLite by default for quick local development; PostgreSQL-ready via `DATABASE_URL`
- Conversation/message persistence
- Streaming chat responses using Server-Sent Events (SSE)
- Basic health endpoint and CORS configuration

## 1. Requirements
- Node.js 20+
- Python 3.11+
- An API key from at least one supported OpenAI-compatible model provider

## 2. Configure the backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` and add your provider key. The default adapter uses the OpenAI-compatible Chat Completions API. Set `AI_BASE_URL`, `AI_API_KEY`, and `AI_MODEL` for your chosen provider.

Start the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## 3. Configure the frontend

In a second terminal:

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000.

For macOS/Linux use `cp .env.example .env.local` instead of `copy`.

## 4. Environment variables

### Backend (`backend/.env`)
- `DATABASE_URL` — defaults to local SQLite; use a PostgreSQL URL in deployment.
- `CORS_ORIGINS` — comma-separated allowed frontend origins.
- `AI_PROVIDER` — currently `openai_compatible`.
- `AI_BASE_URL` — provider API base URL, ending in `/v1` for OpenAI-compatible services.
- `AI_API_KEY` — provider secret. Never expose this in frontend variables.
- `AI_MODEL` — default model name.
- `AI_TEMPERATURE` — generation temperature.

### Frontend (`frontend/.env.local`)
- `NEXT_PUBLIC_API_URL` — backend URL, default `http://localhost:8000`.

## 5. Current MVP scope and important notes
- Chat streams tokens from the backend and saves completed assistant messages.
- Conversations are stored per anonymous browser-generated user ID in this starter. This is **not production authentication**.
- Before opening public registration, implement verified accounts, secure sessions, email verification, password reset, abuse controls, privacy policy, and usage/billing limits.
- The included model adapter is OpenAI-compatible. Multi-provider routing is structured behind an interface, but additional provider adapters and capability-aware routing are next milestones.
- Do not commit `.env`, API keys, database files, or user data.

## 6. Suggested next milestones
1. Add production authentication and account ownership.
2. Add provider adapters and model catalogue with capability metadata.
3. Add rate limiting, quotas, moderation, and audit/usage events.
4. Add document uploads, retrieval, vision, and agent execution.
5. Deploy backend and database, then frontend; test production end-to-end.

## Product identity
- Product: **LUNA AI**
- Brand: **AFROMIND LUNA AI**
- Parent: **Afromind Tech**
- Brand pillar: **LUNA AI — The Intelligence.**
