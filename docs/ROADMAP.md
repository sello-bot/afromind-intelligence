# LUNA AI roadmap

## MVP foundation (this repository)
- Minimal branded chat UI
- FastAPI backend
- SSE token streaming
- Conversation persistence
- One OpenAI-compatible provider adapter
- Local SQLite development database

## Next
- Real authentication: email verification, secure HttpOnly sessions, password reset
- PostgreSQL + Alembic migrations
- Provider adapters (Anthropic, Google, other supported APIs)
- Model catalogue and capability-aware routing
- Rate limiting, quotas, moderation and usage accounting
- File uploads and document analysis
- Agent tools with explicit permission boundaries
- Production observability, backups and security review
