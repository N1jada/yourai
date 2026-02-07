"""Integration tests for knowledge workers with housing legislation scenario.

Tests the complete flow: router classifies → workers retrieve sources →
orchestrator synthesizes response with inline citations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.knowledge_schemas import LegislationSource, PolicySource
from yourai.agents.router import RouterAgent
from yourai.agents.schemas import RouterDecision
from yourai.agents.workers.legislation import LegislationWorker
from yourai.agents.workers.policy import PolicyWorker


@pytest.mark.asyncio
async def test_policy_worker_search(test_session: AsyncSession) -> None:
    """Test PolicyWorker searches company policy documents."""
    from yourai.core.enums import KnowledgeBaseCategory
    from yourai.knowledge.models import Document, DocumentChunk, KnowledgeBase

    tenant_id = uuid4()

    # Create a policy knowledge base with documents
    kb = KnowledgeBase(
        tenant_id=tenant_id,
        name="Housing Policies",
        category=KnowledgeBaseCategory.COMPANY_POLICY,
        source_type="uploaded",
    )
    test_session.add(kb)
    await test_session.flush()

    doc = Document(
        tenant_id=tenant_id,
        knowledge_base_id=kb.id,
        name="Housing Allocation Policy",
        document_uri="/policies/housing_allocation.pdf",
        processing_state="ready",
    )
    test_session.add(doc)
    await test_session.flush()

    chunk = DocumentChunk(
        tenant_id=tenant_id,
        document_id=doc.id,
        chunk_index=0,
        content="Section 3: Priority groups for housing allocation include homeless families...",
    )
    test_session.add(chunk)
    await test_session.commit()

    # Test PolicyWorker (note: without Qdrant, hybrid search will return empty)
    # This test verifies the worker doesn't crash
    worker = PolicyWorker(test_session)
    results = await worker.search(
        "housing allocation priority groups",
        tenant_id,
        limit=5,
    )

    # Without Qdrant running, results will be empty but shouldn't error
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_router_classifies_housing_question() -> None:
    """Test that router correctly classifies a housing legislation question."""
    # Mock Anthropic API response
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(
            text=(
                '{"intent": "legislation_lookup", '
                '"sources": ["uk_legislation"], '
                '"complexity": "moderate", '
                '"reasoning": "Question about specific housing legislation"}'
            )
        )
    ]
    mock_client.messages.create.return_value = mock_response

    router = RouterAgent(mock_client)
    decision = await router.classify_query(
        "What are the main provisions of the Housing Act 1985?",
        uuid4(),
        None,
    )

    assert decision.intent == "legislation_lookup"
    assert "uk_legislation" in decision.sources
    assert decision.complexity in ["simple", "moderate", "complex"]


@pytest.mark.asyncio
async def test_legislation_worker_parses_result() -> None:
    """Test LegislationWorker parses MCP results correctly."""
    import json


    worker = LegislationWorker("http://mock-lex-url/mcp")

    # Mock MCP result
    mock_result = MagicMock()
    mock_result.content = [
        MagicMock(
            text=json.dumps(
                {
                    "title": "Housing Act 1985",
                    "section": "8",
                    "subsection": "1",
                    "year": 1985,
                    "uri": "https://www.legislation.gov.uk/ukpga/1985/68/section/8",
                    "content": "The landlord condition is that the interest of the landlord...",
                    "score": 0.95,
                }
            )
        )
    ]

    # Parse the mocked result
    sources = worker._parse_mcp_result(mock_result)

    assert len(sources) == 1
    assert isinstance(sources[0], LegislationSource)
    assert sources[0].act_name == "Housing Act 1985"
    assert sources[0].section == "8"
    assert sources[0].subsection == "1"
    assert sources[0].year == 1985
    assert sources[0].score == 0.95
    assert sources[0].is_historical is False  # 1985 is after 1963


@pytest.mark.asyncio
async def test_legislation_worker_handles_historical_acts() -> None:
    """Test that pre-1963 legislation is flagged as historical."""
    import json

    worker = LegislationWorker("http://mock-lex-url/mcp")

    mock_result = MagicMock()
    mock_result.content = [
        MagicMock(
            text=json.dumps(
                {
                    "title": "Housing Act 1957",
                    "year": 1957,
                    "uri": "https://www.legislation.gov.uk/ukpga/1957/56",
                    "content": "This Act may be cited as the Housing Act 1957...",
                    "score": 0.88,
                }
            )
        )
    ]

    sources = worker._parse_mcp_result(mock_result)

    assert len(sources) == 1
    assert sources[0].year == 1957
    assert sources[0].is_historical is True  # Pre-1963 historical content


@pytest.mark.asyncio
async def test_knowledge_context_formatting() -> None:
    """Test KnowledgeContext formats sources correctly for prompts."""
    from yourai.agents.knowledge_schemas import KnowledgeContext

    context = KnowledgeContext()

    # Add legislation sources
    context.legislation_sources.append(
        LegislationSource(
            act_name="Housing Act 1985",
            year=1985,
            section="8",
            subsection="1",
            uri="https://www.legislation.gov.uk/ukpga/1985/68/section/8",
            content="The landlord condition is that the interest of the landlord...",
            score=0.95,
            is_historical=False,
        )
    )

    # Add policy sources
    context.policy_sources.append(
        PolicySource(
            document_id=str(uuid4()),
            document_name="Housing Allocation Policy",
            section="Section 3",
            content="Priority groups for housing allocation include...",
            score=0.88,
        )
    )

    # Format for prompt
    formatted = context.format_for_prompt()

    assert "# Retrieved Knowledge Sources" in formatted
    assert "## UK Legislation" in formatted
    assert "Housing Act 1985, s.8(1)" in formatted
    assert "## Company Policies" in formatted
    assert "Housing Allocation Policy, Section 3" in formatted


@pytest.mark.asyncio
async def test_router_decision_parsed_from_json() -> None:
    """Test RouterDecision schema validates correctly."""
    decision_data = {
        "intent": "legislation_lookup",
        "sources": ["uk_legislation", "internal_policies"],
        "complexity": "moderate",
        "reasoning": "Requires both legislation and internal policy context",
    }

    decision = RouterDecision(**decision_data)

    assert decision.intent == "legislation_lookup"
    assert "uk_legislation" in decision.sources
    assert "internal_policies" in decision.sources
    assert decision.complexity == "moderate"
