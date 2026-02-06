"""Tests for SSE event model serialisation."""

from yourai.api.sse.events import (
    AgentCompleteEvent,
    AgentStartEvent,
    ContentDeltaEvent,
    ConversationTitleUpdatedEvent,
    CreditUsageWarningEvent,
    ErrorEvent,
    LegalSourceEvent,
    MessageCompleteEvent,
    PolicyReviewCompleteEvent,
    PolicyReviewStatusEvent,
)


def test_agent_start_event_serialisation() -> None:
    event = AgentStartEvent(
        agent_name="router",
        task_description="Classifying query...",
    )
    data = event.model_dump()
    assert data["event_type"] == "agent_start"
    assert data["agent_name"] == "router"

    json_str = event.model_dump_json()
    assert '"event_type":"agent_start"' in json_str or '"event_type": "agent_start"' in json_str


def test_content_delta_event() -> None:
    event = ContentDeltaEvent(text="The Housing Act 1985")
    assert event.event_type == "content_delta"
    assert event.text == "The Housing Act 1985"


def test_legal_source_event() -> None:
    event = LegalSourceEvent(
        act_name="Housing Act 1985",
        section="s.1",
        uri="https://lex.example.com/housing-act-1985/s1",
        verification_status="verified",
    )
    assert event.event_type == "legal_source"
    data = event.model_dump()
    assert data["verification_status"] == "verified"


def test_error_event() -> None:
    event = ErrorEvent(
        code="upstream_error",
        message="Anthropic API unavailable.",
        recoverable=True,
    )
    assert event.event_type == "error"
    assert event.recoverable is True


def test_message_complete_event() -> None:
    event = MessageCompleteEvent(message_id="abc-123")
    assert event.event_type == "message_complete"


def test_agent_complete_event() -> None:
    event = AgentCompleteEvent(agent_name="orchestrator", duration_ms=1500)
    assert event.event_type == "agent_complete"
    assert event.duration_ms == 1500


def test_policy_review_status_event() -> None:
    event = PolicyReviewStatusEvent(
        state="processing",
        status_text="Analysing policy structure...",
    )
    assert event.event_type == "policy_review_status"


def test_policy_review_complete_event() -> None:
    event = PolicyReviewCompleteEvent(review_id="review-uuid")
    assert event.event_type == "policy_review_complete"


def test_conversation_title_updated_event() -> None:
    event = ConversationTitleUpdatedEvent(
        conversation_id="conv-uuid",
        title="Housing legislation query",
    )
    assert event.event_type == "conversation_title_updated"


def test_credit_usage_warning_event() -> None:
    event = CreditUsageWarningEvent(
        percentage_used=85.0,
        credits_remaining=150.0,
    )
    assert event.event_type == "credit_usage_warning"
    assert event.percentage_used == 85.0
