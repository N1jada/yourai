"""Unit tests for citation verification agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from yourai.agents.verification import CitationExtractor, CitationVerificationAgent
from yourai.api.sse.enums import VerificationStatus


class TestCitationExtractor:
    """Tests for citation extraction from response text."""

    def test_extract_legislation_citation_with_section(self) -> None:
        """Test extracting UK legislation citation with section."""
        text = "According to the Housing Act 1985, s.8(1), the landlord condition applies."

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 1
        assert citations[0].citation_type == "legislation"
        assert citations[0].act_name == "Housing Act 1985"
        assert citations[0].section == "8"
        assert citations[0].subsection == "1"
        assert citations[0].text == "Housing Act 1985, s.8(1)"

    def test_extract_legislation_citation_without_section(self) -> None:
        """Test extracting UK legislation citation without section."""
        text = "The Data Protection Act 2018 governs data handling."

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 1
        assert citations[0].citation_type == "legislation"
        assert citations[0].act_name == "Data Protection Act 2018"
        assert citations[0].section is None
        assert citations[0].subsection is None

    def test_extract_case_law_citation(self) -> None:
        """Test extracting case law citation."""
        text = "As established in R v Smith [2020] EWCA Crim 123, the test requires..."

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 1
        assert citations[0].citation_type == "case_law"
        assert citations[0].case_name == "R v Smith"
        assert citations[0].neutral_citation == "[2020] EWCA Crim 123"

    def test_extract_policy_citation_with_section(self) -> None:
        """Test extracting policy citation with section."""
        text = "See Housing Allocation Policy, Section 3 for priority groups."

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 1
        assert citations[0].citation_type == "policy"
        assert citations[0].document_name == "Housing Allocation Policy"
        assert citations[0].section == "Section 3"

    def test_extract_policy_citation_without_section(self) -> None:
        """Test extracting policy citation without section."""
        text = "Refer to the Employee Benefits Policy for details."

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 1
        assert citations[0].citation_type == "policy"
        assert citations[0].document_name == "Employee Benefits Policy"
        assert citations[0].section is None

    def test_extract_multiple_citations(self) -> None:
        """Test extracting multiple citations from one text."""
        text = (
            "The Housing Act 1985, s.8(1) defines the landlord condition. "
            "This was confirmed in R v Smith [2020] EWCA Crim 123. "
            "See also our Housing Allocation Policy, Section 3."
        )

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 3
        assert citations[0].citation_type == "legislation"
        assert citations[1].citation_type == "case_law"
        assert citations[2].citation_type == "policy"

    def test_extract_no_citations(self) -> None:
        """Test extracting from text with no citations."""
        text = "This is some text without any legal citations."

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 0

    def test_extract_malformed_legislation(self) -> None:
        """Test handling malformed legislation citations."""
        # Missing year in act name
        text = "The Housing Act defines eligibility."

        citations = CitationExtractor.extract_all(text)

        # Should not match without year
        legislation_citations = [c for c in citations if c.citation_type == "legislation"]
        assert len(legislation_citations) == 0

    def test_extract_complex_section_numbers(self) -> None:
        """Test extracting citations with complex section numbers."""
        text = "See Companies Act 2006, s.21A(3)"

        citations = CitationExtractor.extract_all(text)

        assert len(citations) == 1
        assert citations[0].act_name == "Companies Act 2006"
        assert citations[0].section == "21A"
        assert citations[0].subsection == "3"


class TestCitationVerificationAgent:
    """Tests for citation verification logic."""

    @pytest.mark.asyncio
    async def test_verify_valid_legislation(self) -> None:
        """Test verifying a valid legislation citation."""
        from uuid import uuid4

        agent = CitationVerificationAgent("http://mock-lex-url/mcp")
        agent._client = AsyncMock()

        # Mock Lex API response indicating verification success
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text='{"verified": true, "found": true}')]
        agent._client.call_tool.return_value = mock_result

        from yourai.agents.verification import ExtractedCitation

        citation = ExtractedCitation(
            text="Housing Act 1985, s.8(1)",
            citation_type="legislation",
            act_name="Housing Act 1985",
            section="8",
            subsection="1",
        )

        result = await agent._verify_legislation(citation, uuid4())

        assert result.verification_status == VerificationStatus.VERIFIED.value
        assert result.confidence_score == 1.0
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_verify_invalid_legislation(self) -> None:
        """Test verifying an invalid legislation citation (fake section)."""
        from uuid import uuid4

        agent = CitationVerificationAgent("http://mock-lex-url/mcp")
        agent._client = AsyncMock()

        # Mock Lex API response indicating verification failure
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text='{"verified": false}')]
        agent._client.call_tool.return_value = mock_result

        from yourai.agents.verification import ExtractedCitation

        citation = ExtractedCitation(
            text="Housing Act 1985, s.999",  # Fake section number
            citation_type="legislation",
            act_name="Housing Act 1985",
            section="999",
        )

        result = await agent._verify_legislation(citation, uuid4())

        assert result.verification_status == VerificationStatus.REMOVED.value
        assert result.confidence_score == 0.0
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_verify_valid_case_law(self) -> None:
        """Test verifying a valid case law citation."""
        from uuid import uuid4

        agent = CitationVerificationAgent("http://mock-lex-url/mcp")
        agent._client = AsyncMock()

        # Mock Lex API success
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text='{"found": true, "verified": true}')]
        agent._client.call_tool.return_value = mock_result

        from yourai.agents.verification import ExtractedCitation

        citation = ExtractedCitation(
            text="R v Smith [2020] EWCA Crim 123",
            citation_type="case_law",
            case_name="R v Smith",
            neutral_citation="[2020] EWCA Crim 123",
        )

        result = await agent._verify_caselaw(citation, uuid4())

        assert result.verification_status == VerificationStatus.VERIFIED.value
        assert result.confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_verify_lex_error_handling(self) -> None:
        """Test handling Lex API errors gracefully."""
        from uuid import uuid4

        from yourai.knowledge.exceptions import LexError

        agent = CitationVerificationAgent("http://mock-lex-url/mcp")
        agent._client = AsyncMock()

        # Mock Lex API error
        agent._client.call_tool.side_effect = LexError("API unavailable")

        from yourai.agents.verification import ExtractedCitation

        citation = ExtractedCitation(
            text="Housing Act 1985, s.8",
            citation_type="legislation",
            act_name="Housing Act 1985",
            section="8",
        )

        result = await agent._verify_legislation(citation, uuid4())

        # Should mark as UNVERIFIED, not fail completely
        assert result.verification_status == VerificationStatus.UNVERIFIED.value
        assert "API" in result.error_message or "error" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_policy_verification_not_implemented(self) -> None:
        """Test that policy verification returns UNVERIFIED (not yet implemented)."""
        from uuid import uuid4

        agent = CitationVerificationAgent("http://mock-lex-url/mcp")

        from yourai.agents.verification import ExtractedCitation

        citation = ExtractedCitation(
            text="Housing Allocation Policy, Section 3",
            citation_type="policy",
            document_name="Housing Allocation Policy",
            section="Section 3",
        )

        result = await agent._verify_policy(citation, uuid4())

        assert result.verification_status == VerificationStatus.UNVERIFIED.value
        assert "not yet implemented" in result.error_message

    @pytest.mark.asyncio
    async def test_verify_response_no_citations(self) -> None:
        """Test verifying response with no citations."""
        from uuid import uuid4

        agent = CitationVerificationAgent("http://mock-lex-url/mcp")
        agent._client = AsyncMock()

        result = await agent.verify_response("This text has no citations.", uuid4())

        assert result.citations_checked == 0
        assert result.citations_verified == 0
        assert len(result.verified_citations) == 0
        assert len(result.issues) == 0
