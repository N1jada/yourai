"""Knowledge worker result schemas.

Structured formats for citations and sources returned by knowledge workers.
These are used to provide context to the orchestrator agent and format
inline citations in the final response.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    """Type of knowledge source."""

    POLICY = "company_policy"
    LEGISLATION = "uk_legislation"
    CASE_LAW = "case_law"
    EXTERNAL = "external"


class VerificationStatus(StrEnum):
    """Citation verification status."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    PENDING = "pending"


# ---------------------------------------------------------------------------
# Base Knowledge Source
# ---------------------------------------------------------------------------


class KnowledgeSource(BaseModel):
    """Base class for all knowledge sources returned by workers."""

    source_type: SourceType
    content: str = Field(..., description="The relevant text content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")


# ---------------------------------------------------------------------------
# Policy Sources (Internal)
# ---------------------------------------------------------------------------


class PolicySource(KnowledgeSource):
    """Internal company policy document source."""

    source_type: SourceType = SourceType.POLICY
    document_id: str
    document_name: str
    section: str | None = None
    page_number: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    def format_citation(self) -> str:
        """Format as inline citation for AI response."""
        if self.section:
            return f"{self.document_name}, {self.section}"
        return self.document_name


# ---------------------------------------------------------------------------
# Legislation Sources (UK)
# ---------------------------------------------------------------------------


class LegislationSource(KnowledgeSource):
    """UK legislation source from Lex."""

    source_type: SourceType = SourceType.LEGISLATION
    act_name: str
    section: str | None = None
    subsection: str | None = None
    uri: str
    year: int | None = None
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    is_historical: bool = Field(
        default=False, description="True if enacted before 1963 (digitised content)"
    )

    def format_citation(self) -> str:
        """Format as canonical UK legislation citation."""
        # Act name already includes year (e.g., "Housing Act 1985")
        # Only add year if not already in name
        base = self.act_name
        if self.year and str(self.year) not in self.act_name:
            base = f"{self.act_name} {self.year}"

        if self.section:
            citation = f"{base}, s.{self.section}"
            if self.subsection:
                citation += f"({self.subsection})"
            return citation
        return base


# ---------------------------------------------------------------------------
# Case Law Sources
# ---------------------------------------------------------------------------


class CaseLawSource(KnowledgeSource):
    """Case law source from Lex."""

    source_type: SourceType = SourceType.CASE_LAW
    case_name: str
    citation: str
    court: str
    judgment_date: date | None = None
    uri: str | None = None
    neutral_citation: str | None = None

    def format_citation(self) -> str:
        """Format as case law citation."""
        if self.neutral_citation:
            return f"{self.case_name} {self.neutral_citation}"
        return f"{self.case_name} {self.citation}"


# ---------------------------------------------------------------------------
# External Sources
# ---------------------------------------------------------------------------


class ExternalSource(KnowledgeSource):
    """External source (news, regulatory updates, etc.)."""

    source_type: SourceType = SourceType.EXTERNAL
    title: str
    url: str
    published_date: date | None = None
    publisher: str | None = None

    def format_citation(self) -> str:
        """Format as external citation."""
        if self.publisher:
            return f"{self.title} ({self.publisher})"
        return self.title


# ---------------------------------------------------------------------------
# Aggregated Context
# ---------------------------------------------------------------------------


class KnowledgeContext(BaseModel):
    """Aggregated knowledge sources from all workers."""

    policy_sources: list[PolicySource] = Field(default_factory=list)
    legislation_sources: list[LegislationSource] = Field(default_factory=list)
    case_law_sources: list[CaseLawSource] = Field(default_factory=list)
    external_sources: list[ExternalSource] = Field(default_factory=list)

    @property
    def all_sources(self) -> list[KnowledgeSource]:
        """Get all sources combined, sorted by score descending."""
        all_: list[KnowledgeSource] = []
        all_.extend(self.policy_sources)
        all_.extend(self.legislation_sources)
        all_.extend(self.case_law_sources)
        all_.extend(self.external_sources)
        return sorted(all_, key=lambda s: s.score, reverse=True)

    @property
    def has_sources(self) -> bool:
        """Check if any sources were found."""
        return bool(self.all_sources)

    def format_for_prompt(self) -> str:
        """Format knowledge sources for inclusion in system prompt.

        Returns a structured text representation of all retrieved sources
        for the AI to reference when generating its response.
        """
        if not self.has_sources:
            return "No relevant sources found."

        lines = ["# Retrieved Knowledge Sources\n"]

        if self.legislation_sources:
            lines.append("## UK Legislation\n")
            for i, src in enumerate(self.legislation_sources, 1):
                historical = " [HISTORICAL - digitised content]" if src.is_historical else ""
                lines.append(f"{i}. **{src.format_citation()}**{historical}")
                lines.append(f"   URI: {src.uri}")
                lines.append(f"   Content: {src.content[:500]}...\n")

        if self.case_law_sources:
            lines.append("## Case Law\n")
            for i, case_src in enumerate(self.case_law_sources, 1):
                lines.append(f"{i}. **{case_src.format_citation()}** ({case_src.court})")
                if case_src.judgment_date:
                    lines.append(f"   Date: {case_src.judgment_date.strftime('%d/%m/%Y')}")
                lines.append(f"   Content: {case_src.content[:500]}...\n")

        if self.policy_sources:
            lines.append("## Company Policies\n")
            for i, policy_src in enumerate(self.policy_sources, 1):
                lines.append(f"{i}. **{policy_src.format_citation()}**")
                lines.append(f"   Content: {policy_src.content[:500]}...\n")

        if self.external_sources:
            lines.append("## External Sources\n")
            for i, ext_src in enumerate(self.external_sources, 1):
                lines.append(f"{i}. **{ext_src.format_citation()}**")
                lines.append(f"   URL: {ext_src.url}")
                lines.append(f"   Content: {ext_src.content[:500]}...\n")

        return "\n".join(lines)
