# Backend — YourAI

## Quick Reference

```bash
uv run pytest                           # Run all tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest -k "test_name" -x         # Single test, stop on failure
uv run alembic upgrade head             # Apply migrations
uv run alembic revision --autogenerate -m "description"  # New migration
uv run ruff check src/                  # Lint
uv run ruff format src/                 # Format
uv run mypy src/                        # Type check
uv run uvicorn yourai.api.main:app --reload  # Dev server (port 8000)
```

## Architecture

```
src/yourai/
├── core/          # WP1: Tenant, auth, RBAC, config, database
├── knowledge/     # WP3: Document processing, search, embeddings
├── agents/        # WP5: AI engine, multi-agent orchestration
├── policy/        # WP6: Policy review, ontology, compliance
├── billing/       # Billing: Credits, usage tracking
├── monitoring/    # Monitoring: Regulatory change detection
└── api/           # FastAPI routes, middleware, SSE
    └── routes/    # Route handlers by domain
```

## Rules

1. **Tenant isolation**: Every query MUST filter by `tenant_id`. Every new table MUST have RLS.
2. **Async everything**: All endpoints and DB operations use `async def`.
3. **SQLAlchemy 2.0**: Use `mapped_column`, not `Column`.
4. **Pydantic v2**: All request/response schemas.
5. **Structured logging**: Every log line includes `tenant_id`, `request_id`.
6. **British English**: All user-facing strings.
7. **Tests mirror source**: `src/yourai/core/auth.py` → `tests/unit/core/test_auth.py`.
