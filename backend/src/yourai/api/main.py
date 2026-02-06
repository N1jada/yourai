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
    from yourai.api.routes.auth import router as auth_router
    from yourai.api.routes.documents import router as documents_router
    from yourai.api.routes.knowledge_bases import router as knowledge_bases_router
    from yourai.api.routes.roles import router as roles_router
    from yourai.api.routes.search import router as search_router
    from yourai.api.routes.sse import router as sse_router
    from yourai.api.routes.tenants import router as tenants_router
    from yourai.api.routes.users import router as users_router

    app.include_router(auth_router)
    app.include_router(tenants_router)
    app.include_router(users_router)
    app.include_router(roles_router)
    app.include_router(sse_router)
    app.include_router(knowledge_bases_router)
    app.include_router(documents_router)
    app.include_router(search_router)

    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    return app


app = create_app()
