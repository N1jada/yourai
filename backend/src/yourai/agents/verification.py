"""Citation Verification Agent — validates legal citations after response generation.

Runs after the orchestrator generates a response to independently verify every citation
via Lex API lookup. Marks citations as verified/unverified/removed based on validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from uuid import UUID

    from mcp.types import CallToolResult

from yourai.agents.schemas import (
    CitationVerificationResultSchema,
    VerifiedCitationSchema,
)
from yourai.api.sse.enums import VerificationStatus
from yourai.knowledge.exceptions import LexError
from yourai.knowledge.lex_mcp import LexMcpClient

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Citation Extraction
# ---------------------------------------------------------------------------


@dataclass
class ExtractedCitation:
    """A citation extracted from response text."""

    text: str  # Full citation text as it appears in response
    citation_type: str  # "legislation", "case_law", "policy"
    act_name: str | None = None
    section: str | None = None
    subsection: str | None = None
    case_name: str | None = None
    neutral_citation: str | None = None
    document_name: str | None = None


class CitationExtractor:
    """Extracts citations from assistant response text using regex patterns."""

    # UK Legislation patterns
    # Matches: "Housing Act 1985, s.8(1)" or "Data Protection Act 2018, s.45"
    # Captures broadly, we'll clean up in processing
    LEGISLATION_PATTERN = re.compile(
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+Act\s+\d{4})"  # Act name with year
        r"(?:,\s*s\.(\d+[A-Z]?)"  # Optional section
        r"(?:\((\d+[a-z]?)\))?)?"  # Optional subsection
    )

    # Case Law patterns
    # Matches: "R v Smith [2020] EWCA Crim 123"
    CASE_LAW_PATTERN = re.compile(
        # Case name (allows single-letter names like "R")
        r"([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]+)*\s+v\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)"
        r"\s+\[(\d{4})\]\s+"  # Year in brackets
        r"([A-Z]+(?:\s+[A-Z][a-z]+)?)\s+"  # Court abbreviation
        r"(\d+)"  # Case number
    )

    # Policy citation patterns
    # Matches: "Housing Allocation Policy, Section 3"
    POLICY_PATTERN = re.compile(
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+Policy)"  # Document name ending in 'Policy'
        r"(?:,\s*(Section\s+[\w\d]+))?"  # Optional section
    )

    @classmethod
    def extract_all(cls, text: str) -> list[ExtractedCitation]:
        """Extract all citations from response text.

        Args:
            text: Assistant response text

        Returns:
            List of ExtractedCitation objects
        """
        citations: list[ExtractedCitation] = []

        # Common preceding words to strip
        preceding_words = [
            "The ",
            "A ",
            "An ",
            "See ",
            "According to the ",
            "Under the ",
            "As established in ",
            "As ",
            "In ",
            "From ",
        ]

        # Extract legislation citations
        for match in cls.LEGISLATION_PATTERN.finditer(text):
            act_name = match.group(1).strip()
            section = match.group(2)
            subsection = match.group(3)

            # Strip common preceding words
            for prefix in preceding_words:
                if act_name.startswith(prefix):
                    act_name = act_name[len(prefix) :]
                    break

            # Reconstruct clean citation text
            citation_text = act_name
            if section:
                citation_text += f", s.{section}"
                if subsection:
                    citation_text += f"({subsection})"

            citations.append(
                ExtractedCitation(
                    text=citation_text,
                    citation_type="legislation",
                    act_name=act_name,
                    section=section,
                    subsection=subsection,
                )
            )

        # Extract case law citations
        for match in cls.CASE_LAW_PATTERN.finditer(text):
            case_name = match.group(1).strip()
            year = match.group(2)
            court = match.group(3)
            number = match.group(4)

            # Strip common preceding words
            for prefix in preceding_words:
                if case_name.startswith(prefix):
                    case_name = case_name[len(prefix) :]
                    break

            neutral_citation = f"[{year}] {court} {number}"
            citation_text = f"{case_name} {neutral_citation}"

            citations.append(
                ExtractedCitation(
                    text=citation_text,
                    citation_type="case_law",
                    case_name=case_name,
                    neutral_citation=neutral_citation,
                )
            )

        # Extract policy citations
        for match in cls.POLICY_PATTERN.finditer(text):
            document_name = match.group(1).strip()
            section = match.group(2)

            # Strip common preceding words
            for prefix in preceding_words:
                if document_name.startswith(prefix):
                    document_name = document_name[len(prefix) :]
                    break

            # Reconstruct clean citation text
            citation_text = document_name
            if section:
                citation_text += f", {section}"

            citations.append(
                ExtractedCitation(
                    text=citation_text,
                    citation_type="policy",
                    document_name=document_name,
                    section=section,
                )
            )

        logger.info(
            "citations_extracted",
            total_count=len(citations),
            legislation_count=sum(1 for c in citations if c.citation_type == "legislation"),
            case_law_count=sum(1 for c in citations if c.citation_type == "case_law"),
            policy_count=sum(1 for c in citations if c.citation_type == "policy"),
        )

        return citations


# ---------------------------------------------------------------------------
# Citation Verification Agent
# ---------------------------------------------------------------------------


class CitationVerificationAgent:
    """Agent that verifies citations after response generation."""

    def __init__(self, lex_mcp_url: str) -> None:
        self._lex_mcp_url = lex_mcp_url
        self._client: LexMcpClient | None = None

    async def connect(self) -> None:
        """Establish MCP connection. Call before verify_response()."""
        if self._client is None:
            self._client = LexMcpClient(self._lex_mcp_url)
            await self._client.connect()

    async def disconnect(self) -> None:
        """Close MCP connection. Call when done."""
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def verify_response(
        self,
        response_text: str,
        tenant_id: UUID,
    ) -> CitationVerificationResultSchema:
        """Verify all citations in the assistant response.

        Args:
            response_text: The assistant's response text
            tenant_id: Tenant ID for logging

        Returns:
            CitationVerificationResult with verification outcomes
        """
        if self._client is None:
            raise RuntimeError("CitationVerificationAgent not connected. Call connect() first.")

        logger.info(
            "citation_verification_starting",
            tenant_id=str(tenant_id),
            response_length=len(response_text),
        )

        # Extract all citations
        extracted = CitationExtractor.extract_all(response_text)

        if not extracted:
            logger.info("citation_verification_no_citations", tenant_id=str(tenant_id))
            return CitationVerificationResultSchema(
                citations_checked=0,
                citations_verified=0,
                citations_unverified=0,
                citations_removed=0,
                verified_citations=[],
                issues=[],
            )

        # Verify each citation
        verified_citations: list[VerifiedCitationSchema] = []
        issues: list[str] = []

        for citation in extracted:
            if citation.citation_type == "legislation":
                result = await self._verify_legislation(citation, tenant_id)
            elif citation.citation_type == "case_law":
                result = await self._verify_caselaw(citation, tenant_id)
            elif citation.citation_type == "policy":
                result = await self._verify_policy(citation, tenant_id)
            else:
                result = VerifiedCitationSchema(
                    citation_text=citation.text,
                    citation_type=citation.citation_type,
                    verification_status=VerificationStatus.UNVERIFIED.value,
                    confidence_score=0.0,
                    error_message="Unknown citation type",
                )

            verified_citations.append(result)

            # Track issues
            if result.verification_status in (
                VerificationStatus.UNVERIFIED,
                VerificationStatus.REMOVED,
            ):
                issues.append(f"{result.citation_text}: {result.error_message}")

        # Aggregate results
        verified_count = sum(
            1 for c in verified_citations if c.verification_status == VerificationStatus.VERIFIED
        )
        unverified_count = sum(
            1 for c in verified_citations if c.verification_status == VerificationStatus.UNVERIFIED
        )
        removed_count = sum(
            1 for c in verified_citations if c.verification_status == VerificationStatus.REMOVED
        )

        logger.info(
            "citation_verification_complete",
            tenant_id=str(tenant_id),
            total=len(extracted),
            verified=verified_count,
            unverified=unverified_count,
            removed=removed_count,
        )

        return CitationVerificationResultSchema(
            citations_checked=len(extracted),
            citations_verified=verified_count,
            citations_unverified=unverified_count,
            citations_removed=removed_count,
            verified_citations=verified_citations,
            issues=issues,
        )

    async def _verify_legislation(
        self, citation: ExtractedCitation, tenant_id: UUID
    ) -> VerifiedCitationSchema:
        """Verify a UK legislation citation via Lex API.

        Args:
            citation: Extracted legislation citation
            tenant_id: Tenant ID for logging

        Returns:
            VerifiedCitation with verification status
        """
        try:
            # Use search_for_legislation_acts to verify the legislation exists
            # This searches by act name and returns matching legislation
            result = await self._client.call_tool(  # type: ignore[union-attr]
                "search_for_legislation_acts",
                {
                    "query": citation.act_name or citation.text,
                    "limit": 1,
                    "include_text": False,
                },
            )

            # Parse result
            if self._is_verification_successful(result):
                return VerifiedCitationSchema(
                    citation_text=citation.text,
                    citation_type="legislation",
                    verification_status=VerificationStatus.VERIFIED.value,
                    confidence_score=1.0,
                )
            else:
                return VerifiedCitationSchema(
                    citation_text=citation.text,
                    citation_type="legislation",
                    verification_status=VerificationStatus.REMOVED.value,
                    confidence_score=0.0,
                    error_message="Legislation not found or section does not exist",
                )

        except LexError as exc:
            logger.warning(
                "legislation_verification_lex_error",
                tenant_id=str(tenant_id),
                citation=citation.text,
                error=str(exc),
            )
            return VerifiedCitationSchema(
                citation_text=citation.text,
                citation_type="legislation",
                verification_status=VerificationStatus.UNVERIFIED.value,
                confidence_score=0.0,
                error_message=f"Lex API error: {exc}",
            )

        except Exception as exc:
            logger.error(
                "legislation_verification_failed",
                tenant_id=str(tenant_id),
                citation=citation.text,
                error=str(exc),
                exc_info=True,
            )
            return VerifiedCitationSchema(
                citation_text=citation.text,
                citation_type="legislation",
                verification_status=VerificationStatus.UNVERIFIED.value,
                confidence_score=0.0,
                error_message=f"Verification error: {exc}",
            )

    async def _verify_caselaw(
        self, citation: ExtractedCitation, tenant_id: UUID
    ) -> VerifiedCitationSchema:
        """Verify a case law citation via Lex API.

        Args:
            citation: Extracted case law citation
            tenant_id: Tenant ID for logging

        Returns:
            VerifiedCitation with verification status
        """
        try:
            # Lex does not currently expose case law search tools.
            # Return unverified rather than calling a non-existent tool.
            logger.info(
                "caselaw_verification_skipped",
                tenant_id=str(tenant_id),
                citation=citation.text,
                msg="Case law verification not available in current Lex instance",
            )
            return VerifiedCitationSchema(
                citation_text=citation.text,
                citation_type="case_law",
                verification_status=VerificationStatus.UNVERIFIED.value,
                confidence_score=0.0,
                error_message="Case law verification not available",
            )

        except LexError as exc:
            logger.warning(
                "caselaw_verification_lex_error",
                tenant_id=str(tenant_id),
                citation=citation.text,
                error=str(exc),
            )
            return VerifiedCitationSchema(
                citation_text=citation.text,
                citation_type="case_law",
                verification_status=VerificationStatus.UNVERIFIED.value,
                confidence_score=0.0,
                error_message=f"Lex API error: {exc}",
            )

        except Exception as exc:
            logger.error(
                "caselaw_verification_failed",
                tenant_id=str(tenant_id),
                citation=citation.text,
                error=str(exc),
                exc_info=True,
            )
            return VerifiedCitationSchema(
                citation_text=citation.text,
                citation_type="case_law",
                verification_status=VerificationStatus.UNVERIFIED.value,
                confidence_score=0.0,
                error_message=f"Verification error: {exc}",
            )

    async def _verify_policy(
        self, citation: ExtractedCitation, tenant_id: UUID
    ) -> VerifiedCitationSchema:
        """Verify a policy citation against internal documents.

        For now, policy citations are marked as UNVERIFIED since we don't have
        a verification mechanism for internal documents yet. This can be extended
        to query the document database in the future.

        Args:
            citation: Extracted policy citation
            tenant_id: Tenant ID for logging

        Returns:
            VerifiedCitation with UNVERIFIED status
        """
        logger.info(
            "policy_verification_skipped",
            tenant_id=str(tenant_id),
            citation=citation.text,
        )

        # TODO: Implement policy verification by querying document database
        return VerifiedCitationSchema(
            citation_text=citation.text,
            citation_type="policy",
            verification_status=VerificationStatus.UNVERIFIED.value,
            confidence_score=0.5,
            error_message="Policy verification not yet implemented",
        )

    def _is_verification_successful(self, result: CallToolResult) -> bool:
        """Parse MCP CallToolResult to determine if verification succeeded.

        Args:
            result: MCP tool call result

        Returns:
            True if citation was verified, False otherwise
        """
        import json as _json

        for block in result.content:
            if hasattr(block, "text"):
                text = block.text if isinstance(block.text, str) else ""
                text_lower = text.lower()

                # Legacy format: {"verified": true} or {"found": true}
                if "verified" in text_lower and "true" in text_lower:
                    return True
                if "found" in text_lower and "true" in text_lower:
                    return True
                if "exists" in text_lower and "true" in text_lower:
                    return True

                # Lex search result format: {"results": [...], "total": N}
                try:
                    data = _json.loads(text)
                    if isinstance(data, dict):
                        total = data.get("total", 0)
                        if total and int(total) > 0:
                            return True
                        results = data.get("results", [])
                        if results:
                            return True
                    elif isinstance(data, list) and len(data) > 0:
                        return True
                except (ValueError, TypeError):
                    pass

        # If we got here, verification failed
        return False
