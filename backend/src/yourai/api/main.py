"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from yourai.api.sse.dependencies import close_redis
from yourai.core.config import settings
from yourai.core.exceptions import YourAIError
from yourai.core.schemas import HealthResponse

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    yield
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Exception handlers --
    @app.exception_handler(YourAIError)
    async def yourai_error_handler(_request: Request, exc: YourAIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    # -- Routes --
    from yourai.api.routes.activity_logs import router as activity_logs_router
    from yourai.api.routes.auth import router as auth_router
    from yourai.api.routes.conversations import router as conversations_router
    from yourai.api.routes.documents import router as documents_router
    from yourai.api.routes.feedback import router as feedback_router
    from yourai.api.routes.guardrails import router as guardrails_router
    from yourai.api.routes.knowledge_bases import router as knowledge_bases_router
    from yourai.api.routes.personas import router as personas_router
    from yourai.api.routes.policy_ontology import router as policy_ontology_router
    from yourai.api.routes.policy_reviews import router as policy_reviews_router
    from yourai.api.routes.roles import router as roles_router
    from yourai.api.routes.search import router as search_router
    from yourai.api.routes.sse import router as sse_router
    from yourai.api.routes.templates import router as templates_router
    from yourai.api.routes.tenants import router as tenants_router
    from yourai.api.routes.users import router as users_router

    app.include_router(auth_router)
    app.include_router(tenants_router)
    app.include_router(users_router)
    app.include_router(roles_router)
    app.include_router(conversations_router)
    app.include_router(sse_router)
    app.include_router(knowledge_bases_router)
    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(personas_router)
    app.include_router(policy_ontology_router)
    app.include_router(policy_reviews_router)
    app.include_router(feedback_router)
    app.include_router(templates_router)
    app.include_router(guardrails_router)
    app.include_router(activity_logs_router)

    @app.get("/api/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check probing database, Redis, Qdrant, and Lex connectivity."""
        db_status = "ok"
        redis_status = "ok"
        qdrant_status = "unknown"
        lex_status = "unknown"

        # Probe database
        try:
            from yourai.core.database import async_session_factory

            async with async_session_factory() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
        except Exception:
            db_status = "error"

        # Probe Redis
        try:
            from yourai.api.sse.dependencies import get_redis

            redis = await anext(get_redis())
            await redis.ping()
        except Exception:
            redis_status = "error"

        # Probe Qdrant (best-effort)
        try:
            from qdrant_client import AsyncQdrantClient

            client = AsyncQdrantClient(url=settings.qdrant_url)
            await client.get_collections()
            await client.close()
            qdrant_status = "ok"
        except Exception:
            qdrant_status = "error"

        # Probe Lex (best-effort)
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.lex_base_url}/health")
                lex_status = "ok" if resp.status_code == 200 else "error"
        except Exception:
            lex_status = "error"

        overall = "healthy" if db_status == "ok" and redis_status == "ok" else "degraded"

        return HealthResponse(
            status=overall,
            database=db_status,
            qdrant=qdrant_status,
            redis=redis_status,
            lex=lex_status,
            version="0.1.0",
        )

    return app


app = create_app()
