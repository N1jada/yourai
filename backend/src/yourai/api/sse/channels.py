"""SSE channel naming and management.

Channels are Redis pub/sub topics scoped by tenant to enforce isolation.
The tenant_id is always embedded in the channel name so that even if a
subscriber mistakenly connects to the wrong channel, it contains no
cross-tenant data.

Channel patterns:
    sse:{tenant_id}:user:{user_id}
    sse:{tenant_id}:conversation:{conversation_id}
    sse:{tenant_id}:policy-review:{review_id}
    sse:{tenant_id}:knowledge-base:{knowledge_base_id}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class SSEChannel:
    """Typed, tenant-scoped SSE channel identifier."""

    tenant_id: UUID
    scope: str  # "user", "conversation", "policy-review", "knowledge-base"
    resource_id: UUID

    @property
    def pubsub_key(self) -> str:
        """Redis pub/sub channel name."""
        return f"sse:{self.tenant_id}:{self.scope}:{self.resource_id}"

    @property
    def replay_key(self) -> str:
        """Redis sorted-set key for the replay buffer."""
        return f"sse:replay:{self.tenant_id}:{self.scope}:{self.resource_id}"

    @classmethod
    def for_user(cls, tenant_id: UUID, user_id: UUID) -> SSEChannel:
        return cls(tenant_id=tenant_id, scope="user", resource_id=user_id)

    @classmethod
    def for_conversation(cls, tenant_id: UUID, conversation_id: UUID) -> SSEChannel:
        return cls(tenant_id=tenant_id, scope="conversation", resource_id=conversation_id)

    @classmethod
    def for_policy_review(cls, tenant_id: UUID, review_id: UUID) -> SSEChannel:
        return cls(tenant_id=tenant_id, scope="policy-review", resource_id=review_id)

    @classmethod
    def for_knowledge_base(cls, tenant_id: UUID, knowledge_base_id: UUID) -> SSEChannel:
        return cls(tenant_id=tenant_id, scope="knowledge-base", resource_id=knowledge_base_id)
