"""Unit tests for PolicyTypeIdentifier — policy classification with mocked Anthropic API."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
import uuid_utils
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.models import Tenant
from yourai.policy.models import PolicyDefinition
from yourai.policy.type_identifier import PolicyTypeIdentifier


@pytest.fixture
def mock_anthropic_client():
    """Create a mocked Anthropic client."""
    return AsyncMock()


@pytest.fixture
async def sample_policy_definitions(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> list[PolicyDefinition]:
    """Create sample policy definitions for classification tests."""
    definitions = [
        PolicyDefinition(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            name="Health & Safety Policy",
            uri="health-and-safety-policy",
            status="active",
            description="Covers workplace safety, risk assessments, incident reporting",
            name_variants=["Workplace Safety Policy", "H&S Policy"],
            required_sections=["Policy Statement", "Risk Assessment", "Incident Reporting"],
        ),
        PolicyDefinition(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            name="Data Protection Policy",
            uri="data-protection-policy",
            status="active",
            description="GDPR compliance, data handling procedures",
            name_variants=["GDPR Policy", "Privacy Policy"],
            required_sections=["Data Subject Rights", "Processing Activities"],
        ),
        PolicyDefinition(
            id=uuid_utils.uuid7(),
            tenant_id=sample_tenant.id,
            name="Safeguarding Policy",
            uri="safeguarding-policy",
            status="active",
            description="Protection of vulnerable adults and children",
            name_variants=["Vulnerable Persons Policy"],
        ),
    ]

    for defn in definitions:
        test_session.add(defn)
    await test_session.flush()
    return definitions


async def test_identify_policy_type_with_match(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_policy_definitions: list[PolicyDefinition],
    mock_anthropic_client,
) -> None:
    """Identification returns matched definition when confidence is high."""
    # Mock Anthropic API response
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = json.dumps(
        {
            "matched_definition_uri": "health-and-safety-policy",
            "confidence": 0.92,
            "reasoning": "Document discusses risk assessments and incident reporting procedures",
            "alternative_matches": [
                {"uri": "safeguarding-policy", "name": "Safeguarding Policy", "confidence": 0.35}
            ],
        }
    )
    # Add hasattr check for 'text' attribute
    mock_response.content = [mock_content_block]

    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    # Test identification
    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    document_text = """
    Health and Safety Policy

    1. Policy Statement
    Our organization is committed to providing a safe working environment...

    2. Risk Assessment
    All work activities must be subject to risk assessment...

    3. Incident Reporting
    All accidents and near-misses must be reported immediately...
    """

    result = await identifier.identify_policy_type(
        document_text,
        sample_tenant.id,
        test_session,
    )

    # Verify result
    assert result.matched_definition_uri == "health-and-safety-policy"
    assert result.matched_definition_name == "Health & Safety Policy"
    assert result.confidence == 0.92
    assert "risk assessments" in result.reasoning.lower()
    assert len(result.alternative_matches) == 1
    assert result.alternative_matches[0].uri == "safeguarding-policy"

    # Verify API was called correctly
    mock_anthropic_client.messages.create.assert_called_once()
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert "system" in call_kwargs
    assert "messages" in call_kwargs
    assert call_kwargs["messages"][0]["role"] == "user"


async def test_identify_policy_type_no_match(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_policy_definitions: list[PolicyDefinition],
    mock_anthropic_client,
) -> None:
    """Identification returns null when no clear match found."""
    # Mock Anthropic API response with low confidence
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = json.dumps(
        {
            "matched_definition_uri": None,
            "confidence": 0.42,
            "reasoning": "Document appears to be a staff handbook, not matching any specific policy definition",
            "alternative_matches": [],
        }
    )
    mock_response.content = [mock_content_block]

    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    document_text = "Staff Handbook - General information about employment terms and conditions"

    result = await identifier.identify_policy_type(
        document_text,
        sample_tenant.id,
        test_session,
    )

    assert result.matched_definition_uri is None
    assert result.matched_definition_name is None
    assert result.matched_definition_id is None
    assert result.confidence == 0.42
    assert "staff handbook" in result.reasoning.lower()
    assert len(result.alternative_matches) == 0


async def test_identify_policy_type_no_definitions(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    mock_anthropic_client,
) -> None:
    """Identification returns helpful message when tenant has no policy definitions."""
    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    document_text = "Some policy document"

    result = await identifier.identify_policy_type(
        document_text,
        sample_tenant.id,
        test_session,
    )

    assert result.matched_definition_uri is None
    assert result.confidence == 0.0
    assert "No policy definitions found" in result.reasoning
    assert "create policy definitions first" in result.reasoning.lower()

    # API should not be called
    mock_anthropic_client.messages.create.assert_not_called()


async def test_identify_policy_type_filters_inactive(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    mock_anthropic_client,
) -> None:
    """Identification only uses active policy definitions."""
    # Create one active and one inactive definition
    active_defn = PolicyDefinition(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        name="Active Policy",
        uri="active-policy",
        status="active",
    )
    inactive_defn = PolicyDefinition(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        name="Inactive Policy",
        uri="inactive-policy",
        status="inactive",
    )
    test_session.add_all([active_defn, inactive_defn])
    await test_session.flush()

    # Mock response
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = json.dumps(
        {
            "matched_definition_uri": "active-policy",
            "confidence": 0.85,
            "reasoning": "Matches active policy",
            "alternative_matches": [],
        }
    )
    mock_response.content = [mock_content_block]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    result = await identifier.identify_policy_type(
        "Test document",
        sample_tenant.id,
        test_session,
    )

    # Verify only active definitions included in prompt
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    prompt = call_kwargs["messages"][0]["content"]
    assert "Active Policy" in prompt
    assert "Inactive Policy" not in prompt


async def test_identify_policy_type_tenant_isolation(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_policy_definitions: list[PolicyDefinition],
    mock_anthropic_client,
) -> None:
    """Identification only uses definitions from the correct tenant."""
    # Create second tenant with different definitions
    other_tenant = Tenant(
        id=uuid_utils.uuid7(),
        name="Other Tenant",
        slug="other-tenant",
        industry_vertical="healthcare",
        is_active=True,
    )
    test_session.add(other_tenant)
    await test_session.flush()

    other_defn = PolicyDefinition(
        id=uuid_utils.uuid7(),
        tenant_id=other_tenant.id,
        name="Other Tenant Policy",
        uri="other-tenant-policy",
        status="active",
    )
    test_session.add(other_defn)
    await test_session.flush()

    # Mock response
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = json.dumps(
        {
            "matched_definition_uri": "health-and-safety-policy",
            "confidence": 0.90,
            "reasoning": "Matches H&S policy",
            "alternative_matches": [],
        }
    )
    mock_response.content = [mock_content_block]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    result = await identifier.identify_policy_type(
        "Test document",
        sample_tenant.id,  # Use original tenant
        test_session,
    )

    # Verify only sample_tenant's definitions included in prompt
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    prompt = call_kwargs["messages"][0]["content"]
    assert "Health & Safety Policy" in prompt
    assert "Other Tenant Policy" not in prompt


@patch("yourai.agents.model_routing.ModelRouter.get_model_for_routing")
async def test_identify_policy_type_uses_haiku_model(
    mock_get_model,
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_policy_definitions: list[PolicyDefinition],
    mock_anthropic_client,
) -> None:
    """Identification uses Haiku model for cost efficiency."""
    mock_get_model.return_value = "claude-haiku-3-5-20241022"

    # Mock response
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = json.dumps(
        {
            "matched_definition_uri": "health-and-safety-policy",
            "confidence": 0.88,
            "reasoning": "Test",
            "alternative_matches": [],
        }
    )
    mock_response.content = [mock_content_block]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    await identifier.identify_policy_type(
        "Test document",
        sample_tenant.id,
        test_session,
    )

    # Verify Haiku model was used
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-3-5-20241022"


async def test_identify_policy_type_truncates_long_documents(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_policy_definitions: list[PolicyDefinition],
    mock_anthropic_client,
) -> None:
    """Document text is truncated to 2000 characters for classification."""
    # Mock response
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = json.dumps(
        {
            "matched_definition_uri": "health-and-safety-policy",
            "confidence": 0.90,
            "reasoning": "Test",
            "alternative_matches": [],
        }
    )
    mock_response.content = [mock_content_block]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    # Create very long document
    long_document = "A" * 5000

    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    await identifier.identify_policy_type(
        long_document,
        sample_tenant.id,
        test_session,
    )

    # Verify prompt contains truncated text
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    prompt = call_kwargs["messages"][0]["content"]
    assert "[... document continues ...]" in prompt
    assert len(prompt) < len(long_document)


async def test_build_prompt_includes_definition_metadata(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    mock_anthropic_client,
) -> None:
    """Prompt includes definition metadata like name variants and required sections."""
    # Create definition with rich metadata
    defn = PolicyDefinition(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        name="Test Policy",
        uri="test-policy",
        status="active",
        description="A test policy for prompt building",
        name_variants=["Alternative Name 1", "Alternative Name 2"],
        required_sections=["Section A", "Section B"],
    )
    test_session.add(defn)
    await test_session.flush()

    # Mock response
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = json.dumps(
        {
            "matched_definition_uri": "test-policy",
            "confidence": 0.75,
            "reasoning": "Test",
            "alternative_matches": [],
        }
    )
    mock_response.content = [mock_content_block]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    identifier = PolicyTypeIdentifier(mock_anthropic_client)
    await identifier.identify_policy_type(
        "Test document",
        sample_tenant.id,
        test_session,
    )

    # Verify prompt includes metadata
    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    prompt = call_kwargs["messages"][0]["content"]
    assert "Test Policy" in prompt
    assert "test-policy" in prompt
    assert "A test policy for prompt building" in prompt
    assert "Alternative Name 1" in prompt
    assert "Section A" in prompt
