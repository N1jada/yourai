"""Tests for SSE channel naming and management."""

from uuid import UUID, uuid4

from yourai.api.sse.channels import SSEChannel


def test_for_user_channel_key() -> None:
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    user_id = UUID("00000000-0000-0000-0000-000000000002")
    ch = SSEChannel.for_user(tenant_id, user_id)

    assert ch.scope == "user"
    assert ch.tenant_id == tenant_id
    assert ch.resource_id == user_id
    assert ch.pubsub_key == f"sse:{tenant_id}:user:{user_id}"
    assert ch.replay_key == f"sse:replay:{tenant_id}:user:{user_id}"


def test_for_conversation_channel_key() -> None:
    tenant_id = uuid4()
    conv_id = uuid4()
    ch = SSEChannel.for_conversation(tenant_id, conv_id)

    assert ch.scope == "conversation"
    assert ch.pubsub_key == f"sse:{tenant_id}:conversation:{conv_id}"


def test_for_policy_review_channel_key() -> None:
    tenant_id = uuid4()
    review_id = uuid4()
    ch = SSEChannel.for_policy_review(tenant_id, review_id)

    assert ch.scope == "policy-review"
    assert ch.pubsub_key == f"sse:{tenant_id}:policy-review:{review_id}"


def test_for_knowledge_base_channel_key() -> None:
    tenant_id = uuid4()
    kb_id = uuid4()
    ch = SSEChannel.for_knowledge_base(tenant_id, kb_id)

    assert ch.scope == "knowledge-base"
    assert ch.pubsub_key == f"sse:{tenant_id}:knowledge-base:{kb_id}"


def test_channels_are_frozen() -> None:
    ch = SSEChannel.for_user(uuid4(), uuid4())
    try:
        ch.tenant_id = uuid4()  # type: ignore[misc]
        msg = "Should not allow mutation"
        raise AssertionError(msg)
    except AttributeError:
        pass


def test_different_tenants_get_different_channels() -> None:
    resource_id = uuid4()
    ch_a = SSEChannel.for_conversation(uuid4(), resource_id)
    ch_b = SSEChannel.for_conversation(uuid4(), resource_id)

    assert ch_a.pubsub_key != ch_b.pubsub_key
    assert ch_a.replay_key != ch_b.replay_key
