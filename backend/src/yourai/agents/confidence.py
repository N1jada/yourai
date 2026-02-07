"""Confidence scoring for AI responses.

Calculates confidence level (HIGH/MEDIUM/LOW) based on:
- Number and quality of verified citations
- Citation verification success rate
- Knowledge source availability
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yourai.agents.schemas import CitationVerificationResultSchema, RouterDecision

from yourai.agents.enums import ConfidenceLevel


def calculate_confidence(
    verification_result: CitationVerificationResultSchema,
    router_decision: RouterDecision | None,
    has_knowledge_sources: bool,
) -> tuple[ConfidenceLevel, str]:
    """Calculate confidence level for a response.

    Args:
        verification_result: Citation verification result with counts
        router_decision: Router's classification (includes complexity)
        has_knowledge_sources: Whether knowledge sources were found

    Returns:
        Tuple of (ConfidenceLevel, reason_string)
    """
    citations_checked = verification_result.citations_checked
    citations_verified = verification_result.citations_verified
    citations_removed = verification_result.citations_removed

    # No citations case
    if citations_checked == 0:
        if has_knowledge_sources:
            # Has knowledge sources but no citations - possibly general advice
            return (
                ConfidenceLevel.MEDIUM,
                "Response based on knowledge sources but no specific citations provided",
            )
        else:
            # No sources, no citations - general knowledge response
            return (
                ConfidenceLevel.LOW,
                "Response based on general knowledge without specific sources",
            )

    # Calculate verification rate
    verification_rate = citations_verified / citations_checked if citations_checked > 0 else 0.0

    # High confidence: All citations verified, no removals
    if citations_removed == 0 and verification_rate == 1.0:
        if citations_verified >= 3:
            return (
                ConfidenceLevel.HIGH,
                f"All {citations_verified} citations verified successfully",
            )
        elif citations_verified >= 1:
            return (
                ConfidenceLevel.HIGH,
                f"{citations_verified} citation(s) verified successfully",
            )

    # Medium confidence: Most citations verified, minimal removals
    if verification_rate >= 0.7 and citations_removed <= 1:
        return (
            ConfidenceLevel.MEDIUM,
            f"{citations_verified}/{citations_checked} citations verified "
            f"({int(verification_rate * 100)}% verification rate)",
        )

    # Low confidence: Poor verification rate or multiple removals
    if citations_removed > 1 or verification_rate < 0.5:
        return (
            ConfidenceLevel.LOW,
            f"Low citation verification rate: {citations_verified}/{citations_checked} verified, "
            f"{citations_removed} removed as unverifiable",
        )

    # Default to medium for edge cases
    return (
        ConfidenceLevel.MEDIUM,
        f"{citations_verified}/{citations_checked} citations verified",
    )
