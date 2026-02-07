"""Policy-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Policy Definition Groups
# ============================================================================

class CreatePolicyDefinitionGroup(BaseModel):
    """Request schema for creating a policy definition group."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class UpdatePolicyDefinitionGroup(BaseModel):
    """Request schema for updating a policy definition group."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class PolicyDefinitionGroupResponse(BaseModel):
    """Response schema for policy definition group."""

    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ============================================================================
# Policy Definition Topics
# ============================================================================

class CreatePolicyDefinitionTopic(BaseModel):
    """Request schema for creating a policy definition topic."""

    name: str = Field(..., min_length=1, max_length=255)


class UpdatePolicyDefinitionTopic(BaseModel):
    """Request schema for updating a policy definition topic."""

    name: str | None = Field(None, min_length=1, max_length=255)


class PolicyDefinitionTopicResponse(BaseModel):
    """Response schema for policy definition topic."""

    id: UUID
    tenant_id: UUID
    name: str
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ============================================================================
# Policy Definitions
# ============================================================================

class ComplianceCriterion(BaseModel):
    """Individual compliance criterion within a policy definition."""

    name: str
    priority: str = Field(..., pattern="^(high|medium|low|none)$")
    description: str
    criteria_type: str  # e.g., "mandatory", "recommended", "best_practice"


class ScoringCriterion(BaseModel):
    """Scoring criterion for RAG assessment."""

    criterion: str
    green_threshold: str
    amber_threshold: str
    red_threshold: str


class LegislationReference(BaseModel):
    """Reference to legislation that the policy must address."""

    act_name: str
    section: str | None = None
    uri: str | None = None
    notes: str | None = None


class CreatePolicyDefinition(BaseModel):
    """Request schema for creating a policy definition."""

    name: str = Field(..., min_length=1, max_length=255)
    uri: str = Field(
        ..., min_length=1, max_length=255, description="Unique identifier (kebab-case)"
    )
    group_id: UUID | None = None
    topic_ids: list[UUID] = Field(default_factory=list)
    description: str | None = None
    status: str = Field(default="active", pattern="^(active|inactive)$")
    is_required: bool = False
    review_cycle: str | None = Field(None, pattern="^(annual|quarterly|monthly)$")
    name_variants: list[str] = Field(default_factory=list)
    scoring_criteria: list[ScoringCriterion] = Field(default_factory=list)
    compliance_criteria: list[ComplianceCriterion] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    legislation_references: list[LegislationReference] = Field(default_factory=list)
    last_regulatory_update_date: datetime | None = None
    regulatory_change_flags: list[str] = Field(default_factory=list)


class UpdatePolicyDefinition(BaseModel):
    """Request schema for updating a policy definition."""

    name: str | None = Field(None, min_length=1, max_length=255)
    group_id: UUID | None = None
    topic_ids: list[UUID] | None = None
    description: str | None = None
    status: str | None = Field(None, pattern="^(active|inactive)$")
    is_required: bool | None = None
    review_cycle: str | None = Field(None, pattern="^(annual|quarterly|monthly)$")
    name_variants: list[str] | None = None
    scoring_criteria: list[ScoringCriterion] | None = None
    compliance_criteria: list[ComplianceCriterion] | None = None
    required_sections: list[str] | None = None
    legislation_references: list[LegislationReference] | None = None
    last_regulatory_update_date: datetime | None = None
    regulatory_change_flags: list[str] | None = None


class PolicyDefinitionResponse(BaseModel):
    """Response schema for policy definition."""

    id: UUID
    tenant_id: UUID
    name: str
    uri: str
    status: str
    group_id: UUID | None
    description: str | None
    is_required: bool
    review_cycle: str | None
    name_variants: list[str]
    scoring_criteria: list[ScoringCriterion]
    compliance_criteria: list[ComplianceCriterion]
    required_sections: list[str]
    legislation_references: list[LegislationReference]
    last_regulatory_update_date: datetime | None
    regulatory_change_flags: list[str]
    created_at: datetime | None
    updated_at: datetime | None
    
    # Nested relationships (optional - populated on demand)
    group: PolicyDefinitionGroupResponse | None = None
    topics: list[PolicyDefinitionTopicResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ============================================================================
# Policy Reviews
# ============================================================================


class Citation(BaseModel):
    """Citation reference for legislation or guidance."""

    source_type: str  # "legislation", "guidance", "case_law"
    act_name: str | None = None
    document_name: str | None = None
    section: str | None = None
    uri: str | None = None
    excerpt: str | None = None
    verified: bool = False


class CriterionResult(BaseModel):
    """Result of evaluating a single compliance criterion."""

    criterion_name: str
    criterion_priority: str  # "high", "medium", "low", "none"
    rating: str  # "red", "amber", "green"
    justification: str
    citations: list[Citation] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class GapItem(BaseModel):
    """Identified gap in policy coverage."""

    area: str
    severity: str  # "critical", "important", "advisory"
    description: str
    relevant_legislation: list[Citation] = Field(default_factory=list)


class Action(BaseModel):
    """Recommended action for policy improvement."""

    priority: str  # "critical", "important", "advisory"
    description: str
    related_criteria: list[str] = Field(default_factory=list)
    related_legislation: list[Citation] = Field(default_factory=list)


class PolicyReviewResult(BaseModel):
    """Complete policy review result structure."""

    policy_definition_id: UUID
    policy_definition_name: str
    overall_rating: str  # "red", "amber", "green"
    confidence: str  # "high", "medium", "low"
    legal_evaluation: list[CriterionResult] = Field(default_factory=list)
    gap_analysis: list[GapItem] = Field(default_factory=list)
    recommended_actions: list[Action] = Field(default_factory=list)
    summary: str
    created_at: datetime


class StartReviewRequest(BaseModel):
    """Request to start a new policy review."""

    document_text: str = Field(..., min_length=100)
    document_name: str = Field(..., min_length=1, max_length=255)
    policy_definition_id: UUID | None = None  # None = auto-identify


class PolicyReviewResponse(BaseModel):
    """Response schema for policy review."""

    id: UUID
    tenant_id: UUID
    request_id: UUID | None
    user_id: UUID
    policy_definition_id: UUID | None
    state: str
    result: PolicyReviewResult | None = None
    source: str | None
    citation_verification_result: dict | None  # type: ignore[type-arg]
    version: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ============================================================================
# Policy Type Identification
# ============================================================================

class AlternativeMatch(BaseModel):
    """Alternative policy definition match with confidence score."""

    uri: str
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class PolicyTypeIdentificationRequest(BaseModel):
    """Request schema for identifying policy type."""

    document_text: str = Field(..., min_length=10)


class PolicyTypeIdentificationResult(BaseModel):
    """Result of policy type identification."""

    matched_definition_id: UUID | None
    matched_definition_uri: str | None
    matched_definition_name: str | None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    alternative_matches: list[AlternativeMatch] = Field(default_factory=list)


# ============================================================================
# Bulk Operations
# ============================================================================

class BulkSeedRequest(BaseModel):
    """Request schema for bulk seeding policy definitions."""

    definitions: list[CreatePolicyDefinition]


# ============================================================================
# Review History & Trends
# ============================================================================


class CriterionComparison(BaseModel):
    """Comparison of a single criterion between two reviews."""

    criterion_name: str
    previous_rating: str  # "green", "amber", "red", "unknown"
    current_rating: str
    changed: bool


class ComparisonResult(BaseModel):
    """Result of comparing two reviews."""

    review1_id: UUID
    review1_date: datetime | None
    review1_overall_rating: str
    review2_id: UUID
    review2_date: datetime | None
    review2_overall_rating: str
    criteria_comparisons: list[CriterionComparison] = Field(default_factory=list)


class ReviewTrends(BaseModel):
    """Aggregate compliance trends for admin dashboard."""

    total_reviews: int
    green_count: int
    amber_count: int
    red_count: int
    green_percentage: float
    amber_percentage: float
    red_percentage: float
    required_policies_reviewed_count: int
    required_policies_total: int
    required_policies_coverage_percentage: float
