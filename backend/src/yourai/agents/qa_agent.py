"""Quality Assurance Agent — Reviews response quality before delivery.

Sonnet-class agent that checks responses for:
- Completeness, clarity, relevance, professionalism
- Mandatory disclaimer presence
- Appropriate confidence indicators
- Citation formatting

Currently operates in TESTING MODE: Always auto-approves responses but logs findings
for analysis. Can be enabled in future to block low-quality responses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from uuid import UUID

    from yourai.agents.enums import ConfidenceLevel

logger = structlog.get_logger()

# QA is in testing mode (never blocks)
QA_TESTING_MODE = True


class QAResult:
    """Result of QA review."""

    def __init__(
        self,
        approved: bool,
        completeness_score: float,
        clarity_score: float,
        professionalism_score: float,
        has_disclaimer: bool,
        confidence_appropriate: bool,
        issues: list[str],
        recommendations: list[str],
    ) -> None:
        self.approved = approved
        self.completeness_score = completeness_score
        self.clarity_score = clarity_score
        self.professionalism_score = professionalism_score
        self.has_disclaimer = has_disclaimer
        self.confidence_appropriate = confidence_appropriate
        self.issues = issues
        self.recommendations = recommendations


class QualityAssuranceAgent:
    """Sonnet-class agent for quality review (currently in testing mode)."""

    def __init__(self) -> None:
        pass

    async def review_response(
        self,
        response: str,
        confidence_level: ConfidenceLevel,
        verification_result: dict,  # type: ignore[type-arg]
        tenant_id: UUID,
    ) -> QAResult:
        """Review a response for quality issues.

        Args:
            response: The assistant's response text
            confidence_level: Assigned confidence level
            verification_result: Citation verification results
            tenant_id: Tenant UUID for logging

        Returns:
            QAResult with approval status and findings
        """
        issues: list[str] = []
        recommendations: list[str] = []

        # 1. Check for mandatory disclaimer
        has_disclaimer = self._check_disclaimer(response)
        if not has_disclaimer:
            issues.append("Missing mandatory disclaimer")
            recommendations.append("Add legal advice disclaimer at end of response")

        # 2. Check completeness (heuristic: length and structure)
        completeness_score = self._score_completeness(response)
        if completeness_score < 0.5:
            issues.append("Response may be incomplete or too brief")
            recommendations.append("Expand response with more detail or examples")

        # 3. Check clarity (heuristic: sentence structure, jargon)
        clarity_score = self._score_clarity(response)
        if clarity_score < 0.5:
            issues.append("Response may be unclear or use excessive jargon")
            recommendations.append("Simplify language and add explanations")

        # 4. Check professionalism (heuristic: tone)
        professionalism_score = self._score_professionalism(response)
        if professionalism_score < 0.5:
            issues.append("Response may lack professional tone")
            recommendations.append("Maintain formal, respectful tone")

        # 5. Check confidence level appropriateness
        confidence_appropriate = self._check_confidence_appropriate(
            confidence_level, verification_result
        )
        if not confidence_appropriate:
            issues.append("Confidence level may not match verification results")
            recommendations.append("Review confidence scoring algorithm")

        # In testing mode: always approve, but log findings
        if QA_TESTING_MODE:
            approved = True
            logger.info(
                "qa_review_complete_testing_mode",
                tenant_id=str(tenant_id),
                approved=approved,
                issues_count=len(issues),
                recommendations_count=len(recommendations),
                completeness_score=completeness_score,
                clarity_score=clarity_score,
                professionalism_score=professionalism_score,
                has_disclaimer=has_disclaimer,
                confidence_appropriate=confidence_appropriate,
            )
        else:
            # Production mode: block if critical issues found
            critical_issues = ["Missing mandatory disclaimer"]
            approved = not any(issue in critical_issues for issue in issues)

            logger.info(
                "qa_review_complete_production_mode",
                tenant_id=str(tenant_id),
                approved=approved,
                issues=issues,
                recommendations=recommendations,
            )

        return QAResult(
            approved=approved,
            completeness_score=completeness_score,
            clarity_score=clarity_score,
            professionalism_score=professionalism_score,
            has_disclaimer=has_disclaimer,
            confidence_appropriate=confidence_appropriate,
            issues=issues,
            recommendations=recommendations,
        )

    @staticmethod
    def _check_disclaimer(response: str) -> bool:
        """Check if mandatory disclaimer is present."""
        disclaimer_phrases = [
            "does not constitute legal advice",
            "not constitute legal advice",
            "consult qualified legal counsel",
            "legal advice",
        ]
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in disclaimer_phrases)

    @staticmethod
    def _score_completeness(response: str) -> float:
        """Score response completeness (0.0-1.0).

        Heuristic: longer responses with structure are more complete.
        """
        # Check length
        word_count = len(response.split())
        if word_count < 50:
            length_score = 0.3
        elif word_count < 150:
            length_score = 0.7
        else:
            length_score = 1.0

        # Check structure (paragraphs, lists, headings)
        has_structure = "\n\n" in response or "\n-" in response or "\n#" in response
        structure_score = 1.0 if has_structure else 0.5

        return (length_score + structure_score) / 2

    @staticmethod
    def _score_clarity(response: str) -> float:
        """Score response clarity (0.0-1.0).

        Heuristic: shorter sentences and less jargon = more clear.
        """
        # Average sentence length (rough proxy for clarity)
        sentences = response.split(". ")
        if not sentences:
            return 0.5

        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)

        # Prefer 15-25 words per sentence
        if avg_sentence_length < 15:
            sentence_score = 0.8
        elif avg_sentence_length < 30:
            sentence_score = 1.0
        else:
            sentence_score = 0.6

        # Check for excessive legal jargon (very basic heuristic)
        jargon_words = ["thereof", "whereof", "heretofore", "aforementioned"]
        jargon_count = sum(1 for word in jargon_words if word in response.lower())
        jargon_score = 1.0 if jargon_count == 0 else max(0.5, 1.0 - (jargon_count * 0.1))

        return (sentence_score + jargon_score) / 2

    @staticmethod
    def _score_professionalism(response: str) -> float:
        """Score response professionalism (0.0-1.0).

        Heuristic: avoid informal language and maintain respectful tone.
        """
        # Check for informal language
        informal_phrases = [
            "gonna",
            "wanna",
            "kinda",
            "sorta",
            "yeah",
            "nope",
            "dunno",
        ]
        informal_count = sum(1 for phrase in informal_phrases if phrase in response.lower())

        if informal_count > 0:
            return 0.3

        # Check for appropriate tone markers
        polite_phrases = ["please", "kindly", "you may", "we recommend"]
        has_polite_tone = any(phrase in response.lower() for phrase in polite_phrases)

        return 1.0 if has_polite_tone else 0.8

    @staticmethod
    def _check_confidence_appropriate(
        confidence_level: ConfidenceLevel,
        verification_result: dict,  # type: ignore[type-arg]
    ) -> bool:
        """Check if confidence level matches verification results."""
        # If high confidence but low verification rate, flag as inappropriate
        from yourai.agents.enums import ConfidenceLevel as CL

        if confidence_level == CL.HIGH:
            citations_verified = verification_result.get("citations_verified", 0)
            citations_removed = verification_result.get("citations_removed", 0)

            # HIGH confidence should have no removed citations
            if citations_removed > 0:
                return False

            # HIGH confidence should have verified citations (if any citations present)
            citations_checked = verification_result.get("citations_checked", 0)
            if citations_checked > 0 and citations_verified == 0:
                return False

        return True
