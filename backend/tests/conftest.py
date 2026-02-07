"""Shared test fixtures for WP1 core and WP3 knowledge tests.

Uses in-memory SQLite for unit tests (fast, no DB required).
Integration tests should use the real PostgreSQL database.
"""

from __future__ import annotations

import pytest
import uuid_utils
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from yourai.agents.models import (  # noqa: F401 — Import to register with SQLAlchemy
    AgentInvocation,
    AgentInvocationEvent,
    Conversation,
    Message,
    Persona,
)
from yourai.core.auth import AuthService
from yourai.core.database import Base, get_db_session
from yourai.core.enums import (
    DocumentProcessingState,
    KnowledgeBaseCategory,
    KnowledgeBaseSourceType,
    UserStatus,
)
from yourai.core.models import Permission, Role, RolePermission, Tenant, User, UserRole
from yourai.knowledge.models import Document, KnowledgeBase
from yourai.policy.models import (  # noqa: F401 — Import to register with SQLAlchemy
    PolicyDefinition,
    PolicyDefinitionGroup,
    PolicyDefinitionTopic,
)

# In-memory async SQLite for unit tests
_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine with all tables."""
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create a test database session."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def sample_tenant(test_session: AsyncSession) -> Tenant:
    """Create a sample tenant."""
    tenant = Tenant(
        id=uuid_utils.uuid7(),
        name="Test Tenant",
        slug="test-tenant",
        industry_vertical="financial_services",
        branding_config={},
        ai_config={},
        is_active=True,
    )
    test_session.add(tenant)
    await test_session.flush()
    return tenant


@pytest.fixture
async def sample_permission(test_session: AsyncSession) -> Permission:
    """Create a sample permission."""
    permission = Permission(
        id=uuid_utils.uuid7(),
        name="list_users",
        description="List users within the tenant",
    )
    test_session.add(permission)
    await test_session.flush()
    return permission


@pytest.fixture
async def sample_role(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_permission: Permission,
) -> Role:
    """Create a sample role with the sample permission."""
    role = Role(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        name="Admin",
        description="Full access",
    )
    test_session.add(role)
    await test_session.flush()

    # Assign permission to role
    test_session.add(RolePermission(role_id=role.id, permission_id=sample_permission.id))
    await test_session.flush()
    return role


@pytest.fixture
async def sample_user(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_role: Role,
) -> User:
    """Create a sample active user with a role."""
    user = User(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        email="test@example.com",
        given_name="Test",
        family_name="User",
        status=UserStatus.ACTIVE,
        notification_preferences={},
    )
    test_session.add(user)
    await test_session.flush()

    # Assign role to user
    test_session.add(UserRole(user_id=user.id, role_id=sample_role.id))
    await test_session.flush()
    await test_session.refresh(user)
    return user


@pytest.fixture
def auth_token(sample_user: User, sample_tenant: Tenant) -> str:
    """Create a dev JWT for the sample user."""
    auth_service = AuthService()
    return auth_service.create_access_token(
        user_id=sample_user.id,
        tenant_id=sample_tenant.id,
        email=sample_user.email,
    )


@pytest.fixture
async def async_client(
    test_session: AsyncSession,
    auth_token: str,
) -> AsyncClient:
    """Create an httpx AsyncClient against the FastAPI app with auth."""
    from yourai.api.main import create_app

    app = create_app()

    # Override the DB session dependency
    async def _override_session():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# WP3 Knowledge fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sample_knowledge_base(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> KnowledgeBase:
    """Create a sample knowledge base."""
    kb = KnowledgeBase(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        name="Test Legislation KB",
        category=KnowledgeBaseCategory.LEGISLATION,
        source_type=KnowledgeBaseSourceType.UPLOADED,
    )
    test_session.add(kb)
    await test_session.flush()
    return kb


@pytest.fixture
async def sample_document(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_knowledge_base: KnowledgeBase,
) -> Document:
    """Create a sample document in the uploaded state."""
    doc = Document(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        knowledge_base_id=sample_knowledge_base.id,
        name="test_document.pdf",
        document_uri="/tmp/test_uploads/test_document.pdf",
        mime_type="application/pdf",
        byte_size=1024,
        hash="abc123",
        processing_state=DocumentProcessingState.UPLOADED,
    )
    test_session.add(doc)
    await test_session.flush()
    return doc
