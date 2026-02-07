"""Full end-to-end integration test for the agent system.

Tests the complete flow:
1. User asks housing legislation question
2. Router classifies → requires uk_legislation
3. LegislationWorker retrieves sources via Lex MCP
4. Orchestrator synthesizes response with citations
5. CitationVerificationAgent validates citations
6. Confidence scoring assigns level
7. Mandatory disclaimer appended
8. Title generation (for first message)
9. All SSE events emitted correctly
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.enums import ConfidenceLevel
from yourai.agents.invocation import AgentEngine
from yourai.agents.models import Conversation
from yourai.api.sse.enums import MessageState, VerificationStatus
from yourai.core.enums import UserStatus
from yourai.core.models import Tenant, User


@pytest.mark.asyncio
async def test_full_agent_flow_housing_question(
    test_session: AsyncSession,
) -> None:
    """Test complete agent flow with housing legislation question.

    This test mocks external dependencies (Anthropic API, Lex MCP) but tests
    the full orchestration logic end-to-end.
    """
    # Setup: Create tenant, user, conversation
    tenant = Tenant(name="Test Housing Authority", slug="test-housing")
    test_session.add(tenant)
    await test_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="tester@housing.gov.uk",
        given_name="Test",
        family_name="User",
        status=UserStatus.ACTIVE,
    )
    test_session.add(user)
    await test_session.flush()

    conversation = Conversation(
        tenant_id=tenant.id,
        user_id=user.id,
        state="ready",
    )
    test_session.add(conversation)
    await test_session.commit()

    # Mock Redis for SSE with proper pipeline support
    mock_redis = AsyncMock()
    mock_pipeline = MagicMock()
    mock_pipeline.zadd = MagicMock(return_value=mock_pipeline)
    mock_pipeline.zremrangebyscore = MagicMock(return_value=mock_pipeline)
    mock_pipeline.expire = MagicMock(return_value=mock_pipeline)
    mock_pipeline.publish = MagicMock(return_value=mock_pipeline)
    mock_pipeline.execute = AsyncMock(return_value=[1, 1, 1, 1])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    # Mock Anthropic API responses
    mock_anthropic_client = AsyncMock()

    # Mock router response (classifies as legislation_lookup)
    mock_router_response = MagicMock()
    mock_router_response.content = [
        MagicMock(
            text=(
                '{"intent": "legislation_lookup", '
                '"sources": ["uk_legislation"], '
                '"complexity": "moderate", '
                '"reasoning": "User asks about specific housing legislation"}'
            )
        )
    ]

    # Mock orchestrator response (generates text with citation)
    mock_orchestrator_stream = AsyncMock()
    mock_orchestrator_stream.__aenter__ = AsyncMock(return_value=mock_orchestrator_stream)
    mock_orchestrator_stream.__aexit__ = AsyncMock(return_value=None)

    # Simulate streaming response
    async def mock_text_stream():
        chunks = [
            "The Housing Act 1985, s.8(1) defines ",
            "the landlord condition as the requirement ",
            "that the interest of the landlord belongs ",
            "to a local housing authority or similar body.",
        ]
        for chunk in chunks:
            yield chunk

    mock_orchestrator_stream.text_stream = mock_text_stream()

    # Mock title generation response
    mock_title_response = MagicMock()
    mock_title_response.content = [
        MagicMock(text="Housing Act 1985 Landlord Conditions")
    ]

    # Configure mock to return different responses
    def mock_create_side_effect(*args, **kwargs):
        if kwargs.get("max_tokens") == 500:
            # Router call
            return mock_router_response
        elif kwargs.get("max_tokens") == 50:
            # Title generation call
            return mock_title_response
        return MagicMock()

    mock_anthropic_client.messages.create.side_effect = mock_create_side_effect
    # Stream returns the async context manager
    mock_anthropic_client.messages.stream = MagicMock(return_value=mock_orchestrator_stream)

    # Mock Lex MCP for legislation verification
    with patch("yourai.agents.verification.LexMcpClient") as MockLexClient:
        mock_lex_instance = AsyncMock()
        MockLexClient.return_value = mock_lex_instance

        # Mock legislation verification - section 8 exists (VERIFIED)
        mock_verify_result = MagicMock()
        mock_verify_result.content = [
            MagicMock(text='{"verified": true, "found": true}')
        ]
        mock_lex_instance.call_tool.return_value = mock_verify_result

        # Create AgentEngine and invoke
        engine = AgentEngine(
            session=test_session,
            redis=mock_redis,
            anthropic_client=mock_anthropic_client,
        )

        # Invoke the agent
        user_query = "What does the Housing Act 1985 say about landlord conditions?"
        await engine.invoke(
            message=user_query,
            conversation_id=conversation.id,
            tenant_id=tenant.id,
            user_id=user.id,
            persona_id=None,
        )

    # Verify database state
    await test_session.refresh(conversation)

    # 1. Conversation title should be generated (first message)
    assert conversation.title is not None
    assert len(conversation.title) <= 70
    assert "Housing Act" in conversation.title or "Landlord" in conversation.title

    # 2. Messages should be created
    from sqlalchemy import select

    from yourai.agents.models import Message

    messages_result = await test_session.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    messages = list(messages_result.scalars().all())

    assert len(messages) == 2  # User message + assistant message

    user_msg = messages[0]
    assert user_msg.role == "user"
    assert user_msg.content == user_query

    assistant_msg = messages[1]
    assert assistant_msg.role == "assistant"
    assert "Housing Act 1985" in assistant_msg.content
    assert "s.8(1)" in assistant_msg.content
    assert assistant_msg.state == MessageState.SUCCESS

    # 3. Disclaimer should be appended
    assert "does not constitute legal advice" in assistant_msg.content.lower()
    assert "qualified legal counsel" in assistant_msg.content.lower()

    # 4. Verification result should be stored
    assert assistant_msg.verification_result is not None
    verification = assistant_msg.verification_result
    assert verification["citations_checked"] >= 1
    assert verification["citations_verified"] >= 1
    assert len(verification["verified_citations"]) >= 1

    # Check verified citation status
    verified_citation = verification["verified_citations"][0]
    assert "Housing Act 1985" in verified_citation["citation_text"]
    assert verified_citation["verification_status"] == VerificationStatus.VERIFIED.value

    # 5. Confidence level should be assigned
    assert assistant_msg.confidence_level is not None
    # With verified citations, should be HIGH or MEDIUM
    assert assistant_msg.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    # 6. Verify SSE events were emitted (via mock_redis.publish calls)
    assert mock_redis.publish.call_count > 0

    # Check that key events were published
    published_events = [str(call.args) for call in mock_redis.publish.call_list]
    event_types = set()
    for event_str in published_events:
        if "agent_start" in event_str:
            event_types.add("agent_start")
        if "agent_complete" in event_str:
            event_types.add("agent_complete")
        if "content_delta" in event_str:
            event_types.add("content_delta")
        if "verification_result" in event_str:
            event_types.add("verification_result")
        if "confidence_update" in event_str:
            event_types.add("confidence_update")
        if "message_complete" in event_str:
            event_types.add("message_complete")
        if "conversation_title" in event_str:
            event_types.add("title_event")

    # Verify key event types were emitted
    assert "agent_start" in event_types, "AgentStartEvent should be emitted"
    assert "agent_complete" in event_types, "AgentCompleteEvent should be emitted"
    assert "content_delta" in event_types, "ContentDeltaEvent should be emitted"
    assert "verification_result" in event_types, "VerificationResultEvent should be emitted"
    assert "confidence_update" in event_types, "ConfidenceUpdateEvent should be emitted"
    assert "message_complete" in event_types, "MessageCompleteEvent should be emitted"
    assert "title_event" in event_types, "Title generation events should be emitted"

    # 7. Agent invocation should be recorded
    from yourai.agents.models import AgentInvocation

    invocations_result = await test_session.execute(
        select(AgentInvocation).where(AgentInvocation.conversation_id == conversation.id)
    )
    invocations = list(invocations_result.scalars().all())

    assert len(invocations) == 1
    invocation = invocations[0]
    assert invocation.state == "complete"
    assert invocation.query == user_query
    assert invocation.model_used is not None


@pytest.mark.asyncio
async def test_full_agent_flow_with_fake_citation(
    test_session: AsyncSession,
) -> None:
    """Test agent flow where verification catches a fake citation.

    Ensures the verification system correctly marks fabricated citations
    as REMOVED and assigns appropriate confidence level.
    """
    # Setup: Create tenant, user, conversation
    tenant = Tenant(name="Test Authority", slug="test-auth")
    test_session.add(tenant)
    await test_session.flush()

    user = User(
        tenant_id=tenant.id,
        email="tester@test.gov.uk",
        given_name="Test",
        family_name="User",
        status=UserStatus.ACTIVE,
    )
    test_session.add(user)
    await test_session.flush()

    conversation = Conversation(
        tenant_id=tenant.id,
        user_id=user.id,
        state="ready",
    )
    test_session.add(conversation)
    await test_session.commit()

    # Mock dependencies
    mock_redis = AsyncMock()
    mock_pipeline = MagicMock()
    mock_pipeline.zadd = MagicMock(return_value=mock_pipeline)
    mock_pipeline.zremrangebyscore = MagicMock(return_value=mock_pipeline)
    mock_pipeline.expire = MagicMock(return_value=mock_pipeline)
    mock_pipeline.publish = MagicMock(return_value=mock_pipeline)
    mock_pipeline.execute = AsyncMock(return_value=[1, 1, 1, 1])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    mock_anthropic_client = AsyncMock()

    # Mock router
    mock_router_response = MagicMock()
    mock_router_response.content = [
        MagicMock(
            text='{"intent": "legislation_lookup", "sources": ["uk_legislation"], '
            '"complexity": "simple", "reasoning": "Legislation question"}'
        )
    ]

    # Mock orchestrator with FAKE citation (section 999 doesn't exist)
    mock_orchestrator_stream = AsyncMock()
    mock_orchestrator_stream.__aenter__ = AsyncMock(return_value=mock_orchestrator_stream)
    mock_orchestrator_stream.__aexit__ = AsyncMock(return_value=None)

    async def mock_text_stream_fake():
        chunks = [
            "According to the Housing Act 1985, s.999, ",
            "landlords must provide proof of residence.",
        ]
        for chunk in chunks:
            yield chunk

    mock_orchestrator_stream.text_stream = mock_text_stream_fake()

    def mock_create_side_effect(*args, **kwargs):
        if kwargs.get("max_tokens") == 500:
            return mock_router_response
        return MagicMock()

    mock_anthropic_client.messages.create.side_effect = mock_create_side_effect
    # Stream returns the async context manager
    mock_anthropic_client.messages.stream = MagicMock(return_value=mock_orchestrator_stream)

    # Mock Lex MCP - section 999 does NOT exist
    with patch("yourai.agents.verification.LexMcpClient") as MockLexClient:
        mock_lex_instance = AsyncMock()
        MockLexClient.return_value = mock_lex_instance

        mock_verify_result = MagicMock()
        mock_verify_result.content = [
            MagicMock(text='{"verified": false, "error": "Section not found"}')
        ]
        mock_lex_instance.call_tool.return_value = mock_verify_result

        engine = AgentEngine(
            session=test_session,
            redis=mock_redis,
            anthropic_client=mock_anthropic_client,
        )

        await engine.invoke(
            message="What does section 999 say?",
            conversation_id=conversation.id,
            tenant_id=tenant.id,
            user_id=user.id,
        )

    # Verify verification caught the fake citation
    from sqlalchemy import select

    from yourai.agents.models import Message

    messages_result = await test_session.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id, Message.role == "assistant")
    )
    assistant_msg = messages_result.scalar_one()

    verification = assistant_msg.verification_result
    assert verification["citations_checked"] == 1
    assert verification["citations_removed"] == 1
    assert verification["citations_verified"] == 0

    # Confidence should be LOW due to removed citation
    assert assistant_msg.confidence_level == ConfidenceLevel.LOW
