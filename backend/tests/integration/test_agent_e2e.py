"""Integration tests for agent conversation flow.

Tests conversation and message CRUD operations as part of the agent pipeline.

Note: Full E2E test with actual Anthropic API calls would require:
- Valid ANTHROPIC_API_KEY
- Real Redis instance for SSE
- WebSocket client for SSE stream listening

For Session 1, we focus on testing the data layer and service integration.
Session 2+ will add full mocked agent invocation tests.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.conversations import ConversationService
from yourai.agents.enums import MessageRole, MessageState
from yourai.agents.messages import MessageService
from yourai.agents.personas import PersonaService
from yourai.agents.schemas import CreateConversation, CreatePersona, SendMessage, UpdatePersona


@pytest.mark.asyncio
async def test_conversation_and_message_flow(test_session: AsyncSession) -> None:
    """Test creating a conversation, adding messages, and using a persona."""
    tenant_id = uuid4()
    user_id = uuid4()

    # 1. Create a persona
    persona_service = PersonaService(test_session)
    persona = await persona_service.create_persona(
        tenant_id,
        CreatePersona(
            name="Compliance Expert",
            description="Expert in UK compliance and GDPR",
            system_instructions="You are a helpful compliance assistant.",
        ),
    )
    assert persona.name == "Compliance Expert"

    # 2. Create a conversation
    conv_service = ConversationService(test_session)
    conversation = await conv_service.create_conversation(
        tenant_id, user_id, CreateConversation(title="GDPR Discussion")
    )
    assert conversation.title == "GDPR Discussion"

    # 3. Add user message
    msg_service = MessageService(test_session)
    user_msg = await msg_service.create_message(
        conversation.id,
        tenant_id,
        SendMessage(content="What are the key provisions of GDPR?", persona_id=persona.id),
    )

    assert user_msg.role == MessageRole.USER
    assert user_msg.content == "What are the key provisions of GDPR?"
    assert user_msg.state == MessageState.PENDING

    # 4. List messages
    messages = await msg_service.list_messages(conversation.id, tenant_id, page=1, page_size=10)
    assert messages.total == 1
    assert messages.items[0].id == user_msg.id

    # 5. Add more messages to verify conversation history
    await msg_service.create_message(
        conversation.id, tenant_id, SendMessage(content="Follow-up question")
    )
    await msg_service.create_message(
        conversation.id, tenant_id, SendMessage(content="Another question")
    )

    final_messages = await msg_service.list_messages(
        conversation.id, tenant_id, page=1, page_size=10
    )
    assert final_messages.total == 3

    # 6. Verify persona can be updated
    updated_persona = await persona_service.update_persona(
        persona.id,
        tenant_id,
        UpdatePersona(description="Updated description"),
    )
    assert updated_persona.description == "Updated description"


@pytest.mark.asyncio
async def test_multi_turn_conversation(test_session: AsyncSession) -> None:
    """Test multi-turn conversation with message ordering."""
    tenant_id = uuid4()
    user_id = uuid4()

    conv_service = ConversationService(test_session)
    msg_service = MessageService(test_session)

    # Create conversation
    conversation = await conv_service.create_conversation(
        tenant_id, user_id, CreateConversation(title="Multi-turn")
    )

    # Simulate multi-turn conversation
    messages_to_add = [
        "First question",
        "Second question",
        "Third question",
        "Fourth question",
    ]

    for content in messages_to_add:
        await msg_service.create_message(conversation.id, tenant_id, SendMessage(content=content))

    # Verify ordering (oldest first)
    messages = await msg_service.list_messages(conversation.id, tenant_id, page=1, page_size=10)
    assert messages.total == 4
    assert [m.content for m in messages.items] == messages_to_add
