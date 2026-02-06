"""Database engine, session factory, and base model."""

from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import ForeignKey, Uuid, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from yourai.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_min,
    max_overflow=settings.database_pool_max - settings.database_pool_min,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with async_session_factory() as session:
        yield session


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Set the RLS tenant context for the current transaction.

    MUST be called at the start of every request that touches tenant-scoped data.
    On non-PostgreSQL backends (e.g. SQLite in tests), this is a no-op.
    """
    dialect = session.bind.dialect.name if session.bind else ""
    if dialect == "postgresql":
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)},
        )


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TenantScopedMixin:
    """Mixin for all tenant-scoped models. Adds tenant_id column with FK to tenants."""

    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
