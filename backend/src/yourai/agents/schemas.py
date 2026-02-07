"""Pydantic v2 request/response schemas for agent-related endpoints.

All schemas match API_CONTRACTS.md §4 (Conversation Management).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yourai.agents.enums import (
    ConfidenceLevel,
    ConversationState,
    MessageRole,
    MessageState,
)

# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------


class PersonaResponse(BaseModel):
    """Persona response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    system_instructions: str | None
    activated_skills: list[str]
    usage_count: int
    created_at: datetime | None
    updated_at: datetime | None


class CreatePersona(BaseModel):
    """Create a new persona."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    system_instructions: str | None = None
    activated_skills: list[str] = Field(default_factory=list)


class UpdatePersona(BaseModel):
    """Update an existing persona."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    system_instructions: str | None = None
    activated_skills: list[str] | None = None


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


class ConversationResponse(BaseModel):
    """Conversation response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: str | None
    state: ConversationState
    template_id: UUID | None
    deleted_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None


class CreateConversation(BaseModel):
    """Create a new conversation."""

    title: str | None = Field(None, max_length=255)
    template_id: UUID | None = None


class UpdateConversation(BaseModel):
    """Update an existing conversation (rename, change state)."""

    title: str | None = Field(None, max_length=255)
    state: ConversationState | None = None


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    """Message response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    conversation_id: UUID
    request_id: UUID | None
    role: MessageRole
    content: str
    state: MessageState
    metadata_: dict[str, object]
    file_attachments: list[str]
    confidence_level: ConfidenceLevel | None
    verification_result: dict[str, object] | None
    created_at: datetime | None
    updated_at: datetime | None


class SendMessage(BaseModel):
    """Send a message in a conversation."""

    content: str = Field(..., min_length=1)
    persona_id: UUID | None = None
    file_attachments: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent Invocation
# ---------------------------------------------------------------------------


class AgentInvocationResponse(BaseModel):
    """Agent invocation response schema (for debugging/monitoring)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    conversation_id: UUID | None
    request_id: UUID | None
    user_id: UUID
    mode: str
    query: str | None
    persona_id: UUID | None
    context_id: UUID | None
    state: str
    attachments: list[str]
    model_used: str | None
    model_tier: str | None
    cache_hit: bool
    created_at: datetime | None
    updated_at: datetime | None


# ---------------------------------------------------------------------------
# Internal schemas (not exposed via API)
# ---------------------------------------------------------------------------


class RouterDecision(BaseModel):
    """Internal: Router agent's classification decision."""

    intent: str
    sources: list[str]
    complexity: str
    reasoning: str


class VerifiedCitationSchema(BaseModel):
    """A single citation with its verification result."""

    citation_text: str
    citation_type: str  # "legislation", "case_law", "policy"
    verification_status: str  # "verified", "unverified", "removed"
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    error_message: str | None = None


class CitationVerificationResultSchema(BaseModel):
    """Complete verification result for a response."""

    citations_checked: int
    citations_verified: int
    citations_unverified: int
    citations_removed: int
    verified_citations: list[VerifiedCitationSchema]
    issues: list[str]
