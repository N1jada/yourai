"""Unit tests for ConversationService.

Tests CRUD operations and tenant/user isolation.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.conversations import ConversationService
from yourai.agents.schemas import CreateConversation, UpdateConversation
from yourai.core.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_create_conversation(test_session: AsyncSession) -> None:
    """Test creating a new conversation."""
    service = ConversationService(test_session)
    tenant_id = uuid4()
    user_id = uuid4()

    data = CreateConversation(title="Test Conversation")
    result = await service.create_conversation(tenant_id, user_id, data)

    assert result.title == "Test Conversation"
    assert result.tenant_id == tenant_id
    assert result.user_id == user_id
    assert result.deleted_at is None


@pytest.mark.asyncio
async def test_list_conversations(test_session: AsyncSession) -> None:
    """Test listing conversations for a user."""
    service = ConversationService(test_session)
    tenant_id = uuid4()
    user_id = uuid4()

    # Create a few conversations
    await service.create_conversation(tenant_id, user_id, CreateConversation(title="Conv 1"))
    await service.create_conversation(tenant_id, user_id, CreateConversation(title="Conv 2"))
    await service.create_conversation(tenant_id, user_id, CreateConversation(title="Conv 3"))

    page = await service.list_conversations(tenant_id, user_id, page=1, page_size=10)

    assert page.total == 3
    assert len(page.items) == 3
    assert page.has_next is False


@pytest.mark.asyncio
async def test_get_conversation(test_session: AsyncSession) -> None:
    """Test getting a single conversation."""
    service = ConversationService(test_session)
    tenant_id = uuid4()
    user_id = uuid4()

    created = await service.create_conversation(
        tenant_id, user_id, CreateConversation(title="Test")
    )

    fetched = await service.get_conversation(created.id, tenant_id, user_id)

    assert fetched.id == created.id
    assert fetched.title == "Test"


@pytest.mark.asyncio
async def test_update_conversation(test_session: AsyncSession) -> None:
    """Test updating a conversation."""
    service = ConversationService(test_session)
    tenant_id = uuid4()
    user_id = uuid4()

    created = await service.create_conversation(
        tenant_id, user_id, CreateConversation(title="Original")
    )

    updated = await service.update_conversation(
        created.id, tenant_id, user_id, UpdateConversation(title="Updated")
    )

    assert updated.title == "Updated"


@pytest.mark.asyncio
async def test_soft_delete_conversation(test_session: AsyncSession) -> None:
    """Test soft deleting a conversation."""
    service = ConversationService(test_session)
    tenant_id = uuid4()
    user_id = uuid4()

    created = await service.create_conversation(
        tenant_id, user_id, CreateConversation(title="To Delete")
    )

    await service.delete_conversation(created.id, tenant_id, user_id)

    # Should not be found after soft delete
    with pytest.raises(NotFoundError):
        await service.get_conversation(created.id, tenant_id, user_id)


@pytest.mark.asyncio
async def test_user_isolation(test_session: AsyncSession) -> None:
    """Test that users can only access their own conversations."""
    service = ConversationService(test_session)
    tenant_id = uuid4()
    user1_id = uuid4()
    user2_id = uuid4()

    # User 1 creates a conversation
    conv = await service.create_conversation(
        tenant_id, user1_id, CreateConversation(title="User 1 Conv")
    )

    # User 2 should not be able to access it
    with pytest.raises(NotFoundError):
        await service.get_conversation(conv.id, tenant_id, user2_id)


@pytest.mark.asyncio
async def test_tenant_isolation(test_session: AsyncSession) -> None:
    """Test that tenants cannot access other tenants' conversations."""
    service = ConversationService(test_session)
    tenant1_id = uuid4()
    tenant2_id = uuid4()
    user_id = uuid4()

    # Tenant 1 creates a conversation
    conv = await service.create_conversation(
        tenant1_id, user_id, CreateConversation(title="Tenant 1 Conv")
    )

    # Tenant 2 should not be able to access it
    with pytest.raises(NotFoundError):
        await service.get_conversation(conv.id, tenant2_id, user_id)
