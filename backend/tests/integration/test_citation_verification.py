"""Integration tests for citation verification end-to-end.

Tests the two critical scenarios:
1. Fake citation (fabricated section number) → marked as REMOVED
2. Real citation (valid section) → marked as VERIFIED
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from yourai.agents.verification import CitationVerificationAgent
from yourai.api.sse.enums import VerificationStatus


@pytest.mark.asyncio
async def test_fake_citation_marked_as_removed() -> None:
    """Test that a fabricated citation is caught and marked as REMOVED.

    Scenario: Assistant generates a response citing "Housing Act 1985, s.999"
    but section 999 does not exist. Verification should catch this and mark
    the citation as REMOVED.
    """
    # Response text with a fake section number
    assistant_response = (
        "According to the Housing Act 1985, s.999, landlords must provide "
        "proof of residence. This section outlines the requirements."
    )

    agent = CitationVerificationAgent("http://mock-lex-url/mcp")
    agent._client = AsyncMock()

    # Mock Lex API response indicating the section does NOT exist
    mock_result = MagicMock()
    mock_result.content = [
        MagicMock(text='{"verified": false, "error": "Section not found"}')
    ]
    agent._client.call_tool.return_value = mock_result

    # Run verification
    result = await agent.verify_response(assistant_response, uuid4())

    # Assertions
    assert result.citations_checked == 1, "Should have found one citation"
    assert result.citations_verified == 0, "Should have zero verified citations"
    assert result.citations_removed == 1, "Should have marked one citation as removed"
    assert len(result.issues) > 0, "Should have reported an issue"

    # Check the specific citation
    verified_citation = result.verified_citations[0]
    assert verified_citation.citation_text == "Housing Act 1985, s.999"
    assert verified_citation.verification_status == VerificationStatus.REMOVED.value
    assert "not found" in verified_citation.error_message.lower()


@pytest.mark.asyncio
async def test_real_citation_marked_as_verified() -> None:
    """Test that a real, valid citation is marked as VERIFIED.

    Scenario: Assistant generates a response citing "Housing Act 1985, s.8(1)"
    which is a real section. Verification should confirm this and mark the
    citation as VERIFIED.
    """
    # Response text with a real, valid section number
    assistant_response = (
        "The Housing Act 1985, s.8(1) defines the landlord condition as "
        "the requirement that the interest of the landlord belongs to one "
        "of the prescribed bodies."
    )

    agent = CitationVerificationAgent("http://mock-lex-url/mcp")
    agent._client = AsyncMock()

    # Mock Lex API response indicating the section EXISTS and is valid
    mock_result = MagicMock()
    mock_result.content = [MagicMock(text='{"verified": true, "found": true}')]
    agent._client.call_tool.return_value = mock_result

    # Run verification
    result = await agent.verify_response(assistant_response, uuid4())

    # Assertions
    assert result.citations_checked == 1, "Should have found one citation"
    assert result.citations_verified == 1, "Should have verified one citation"
    assert result.citations_removed == 0, "Should have no removed citations"
    assert len(result.issues) == 0, "Should have no issues"

    # Check the specific citation
    verified_citation = result.verified_citations[0]
    assert verified_citation.citation_text == "Housing Act 1985, s.8(1)"
    assert verified_citation.verification_status == VerificationStatus.VERIFIED.value
    assert verified_citation.confidence_score == 1.0
    assert verified_citation.error_message is None


@pytest.mark.asyncio
async def test_mixed_citations_verified_and_fake() -> None:
    """Test response with both valid and fake citations.

    Ensures that verification correctly handles mixed citation quality.
    """
    # Response with both real and fake citations
    assistant_response = (
        "The Housing Act 1985, s.8(1) defines the landlord condition. "
        "Additionally, the Housing Act 1985, s.999 specifies additional requirements. "
        "This was confirmed in R v Smith [2020] EWCA Crim 123."
    )

    agent = CitationVerificationAgent("http://mock-lex-url/mcp")
    agent._client = AsyncMock()

    # Mock Lex API responses - different for each citation
    def mock_call_tool(tool_name: str, args: dict) -> MagicMock:
        result = MagicMock()
        if args.get("section") == "8":
            # Real section - verified
            result.content = [MagicMock(text='{"verified": true, "found": true}')]
        elif args.get("section") == "999":
            # Fake section - not found
            result.content = [MagicMock(text='{"verified": false}')]
        else:
            # Case law - verified
            result.content = [MagicMock(text='{"verified": true}')]
        return result

    agent._client.call_tool.side_effect = mock_call_tool

    # Run verification
    result = await agent.verify_response(assistant_response, uuid4())

    # Assertions
    assert result.citations_checked == 3, "Should have found three citations"
    assert result.citations_verified == 2, "Should have verified two citations"
    assert result.citations_removed == 1, "Should have removed one fake citation"
    assert len(result.issues) == 1, "Should have one issue (the fake citation)"

    # Find the fake citation
    fake_citations = [
        c
        for c in result.verified_citations
        if c.verification_status == VerificationStatus.REMOVED.value
    ]
    assert len(fake_citations) == 1
    assert "999" in fake_citations[0].citation_text


@pytest.mark.asyncio
async def test_no_citations_in_response() -> None:
    """Test verification of response with no citations."""
    assistant_response = (
        "This is a general response that does not contain any specific "
        "legal citations or references to legislation."
    )

    agent = CitationVerificationAgent("http://mock-lex-url/mcp")
    agent._client = AsyncMock()

    result = await agent.verify_response(assistant_response, uuid4())

    # Assertions
    assert result.citations_checked == 0
    assert result.citations_verified == 0
    assert result.citations_removed == 0
    assert len(result.verified_citations) == 0
    assert len(result.issues) == 0


@pytest.mark.asyncio
async def test_verification_with_lex_api_error() -> None:
    """Test that verification handles Lex API errors gracefully."""
    from yourai.knowledge.exceptions import LexError

    assistant_response = "The Housing Act 1985, s.8 defines eligibility."

    agent = CitationVerificationAgent("http://mock-lex-url/mcp")
    agent._client = AsyncMock()

    # Mock Lex API throwing an error
    agent._client.call_tool.side_effect = LexError("Connection timeout")

    result = await agent.verify_response(assistant_response, uuid4())

    # Should mark as UNVERIFIED, not fail
    assert result.citations_checked == 1
    assert result.citations_verified == 0
    assert result.citations_unverified == 1
    assert len(result.issues) > 0

    verified_citation = result.verified_citations[0]
    assert verified_citation.verification_status == VerificationStatus.UNVERIFIED.value
    assert "error" in verified_citation.error_message.lower()
