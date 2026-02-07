"""Integration test for PolicyReviewEngine with mock fire safety policy."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import anthropic
import pytest
import uuid_utils
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.models import Tenant
from yourai.knowledge.lex_rest import LexRestClient
from yourai.policy.enums import PolicyReviewState, RAGRating
from yourai.policy.models import PolicyDefinition
from yourai.policy.review_engine import PolicyReviewEngine

# Mock social housing fire safety policy
MOCK_FIRE_SAFETY_POLICY = """
FIRE SAFETY POLICY

1. Policy Statement
This organisation is committed to ensuring the safety of all residents and staff
through robust fire safety procedures and compliance with all relevant legislation,
including the Regulatory Reform (Fire Safety) Order 2005 and the Fire Safety Act 2021.

2. Roles and Responsibilities
The Fire Safety Manager is the designated accountable person under the Building Safety
Act 2022 for all high-rise residential buildings over 18 metres.

3. Risk Assessment Process
Fire risk assessments will be conducted annually by a qualified fire risk assessor.
All findings will be recorded and remedial actions tracked to completion.

4. Evacuation Procedures
Each building has a tailored evacuation strategy. Residents will be informed of
evacuation procedures through welcome packs and annual fire safety communications.

5. Fire Detection and Alarm Systems
All buildings are equipped with fire detection systems compliant with BS 5839-1.
Systems are tested weekly and serviced quarterly by certified contractors.

6. Personal Emergency Evacuation Plans (PEEPs)
PEEPs are created for all residents who require assistance during evacuation.
Plans are reviewed annually and updated when resident circumstances change.

7. Resident Communication
Fire safety guidance is provided to all residents via:
- Welcome packs for new residents
- Annual fire safety newsletters
- Building notice boards
- Dedicated fire safety page on resident portal

8. High-Rise Specific Requirements
For buildings over 18 metres:
- Fire doors are inspected quarterly
- Communal areas are inspected weekly for fire hazards
- Fire safety information is displayed prominently in all common areas
"""


@pytest.fixture
async def mock_redis() -> Redis:  # type: ignore[type-arg]
    """Create mock Redis client."""
    redis = AsyncMock()

    # Mock pipeline
    mock_pipeline = AsyncMock()
    mock_pipeline.zadd = Mock(return_value=mock_pipeline)
    mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
    mock_pipeline.expire = Mock(return_value=mock_pipeline)
    mock_pipeline.publish = Mock(return_value=mock_pipeline)
    mock_pipeline.execute = AsyncMock(return_value=[1, 0, True, 1])

    redis.pipeline = Mock(return_value=mock_pipeline)
    redis.publish = AsyncMock(return_value=1)

    return redis  # type: ignore[return-value]


@pytest.fixture
async def mock_anthropic_client() -> anthropic.AsyncAnthropic:
    """Create mock Anthropic client."""
    return AsyncMock(spec=anthropic.AsyncAnthropic)


@pytest.fixture
async def mock_lex_client() -> LexRestClient:
    """Create mock Lex client with realistic fire safety legislation results."""
    client = AsyncMock(spec=LexRestClient)

    # Mock search results for fire safety legislation
    mock_legislation_sections = [
        Mock(
            legislation_title="Regulatory Reform (Fire Safety) Order 2005",
            legislation_uri="https://www.legislation.gov.uk/uksi/2005/1541",
            text="The responsible person must ensure that a suitable and sufficient "
            "assessment of the risks to which relevant persons are exposed is made. "
            "The assessment must be reviewed regularly and whenever there is reason "
            "to suspect that it is no longer valid.",
        ),
        Mock(
            legislation_title="Fire Safety Act 2021",
            legislation_uri="https://www.legislation.gov.uk/ukpga/2021/24",
            text="The Fire Safety Order is amended to clarify that the responsible "
            "person must ensure fire safety in the structure and external walls of "
            "buildings, including cladding, balconies, and windows.",
        ),
        Mock(
            legislation_title="Building Safety Act 2022",
            legislation_uri="https://www.legislation.gov.uk/ukpga/2022/30",
            text="The accountable person must take all reasonable steps to prevent "
            "a building safety risk materialising. For high-rise residential buildings, "
            "the accountable person must register the building and demonstrate ongoing "
            "compliance with safety requirements.",
        ),
    ]

    client.search_legislation_sections = AsyncMock(return_value=mock_legislation_sections)

    return client  # type: ignore[return-value]


@pytest.fixture
async def fire_safety_policy_definition(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> PolicyDefinition:
    """Create fire safety policy definition with compliance criteria."""
    definition = PolicyDefinition(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        name="Fire Safety Policy",
        uri="fire-safety-policy",
        status="active",
        description="Comprehensive fire safety policy for social housing",
        is_required=True,
        review_cycle="annual",
        required_sections=[
            "Policy Statement",
            "Roles and Responsibilities",
            "Risk Assessment Process",
            "Evacuation Procedures",
            "Fire Detection and Alarm Systems",
            "Resident Communication",
        ],
        compliance_criteria=[
            {
                "name": "References Current Fire Safety Legislation",
                "priority": "high",
                "description": "Policy must reference the Regulatory Reform (Fire Safety) Order 2005, "
                "Fire Safety Act 2021, and Building Safety Act 2022",
                "criteria_type": "mandatory",
            },
            {
                "name": "Defines Accountable Person Duties",
                "priority": "high",
                "description": "Policy must clearly define the accountable person under the Building "
                "Safety Act 2022 for high-rise residential buildings",
                "criteria_type": "mandatory",
            },
            {
                "name": "Includes PEEPs Process",
                "priority": "medium",
                "description": "Policy must describe the process for creating and maintaining Personal "
                "Emergency Evacuation Plans for vulnerable residents",
                "criteria_type": "regulatory",
            },
        ],
        legislation_references=[
            {
                "act_name": "Regulatory Reform (Fire Safety) Order 2005",
                "uri": "https://www.legislation.gov.uk/uksi/2005/1541",
            },
            {
                "act_name": "Fire Safety Act 2021",
                "uri": "https://www.legislation.gov.uk/ukpga/2021/24",
            },
            {
                "act_name": "Building Safety Act 2022",
                "uri": "https://www.legislation.gov.uk/ukpga/2022/30",
            },
        ],
    )

    test_session.add(definition)
    await test_session.flush()
    return definition


def mock_criterion_evaluation(criterion_name: str) -> str:
    """Generate mock LLM evaluation response for a criterion."""
    if "Current Fire Safety Legislation" in criterion_name:
        return """{
  "rating": "green",
  "justification": "The policy explicitly references all three key pieces of fire safety legislation: Regulatory Reform (Fire Safety) Order 2005, Fire Safety Act 2021, and Building Safety Act 2022. This demonstrates full compliance with the requirement to reference current legislation.",
  "citations": [
    {
      "source_type": "legislation",
      "act_name": "Regulatory Reform (Fire Safety) Order 2005",
      "section": "Article 9",
      "uri": "https://www.legislation.gov.uk/uksi/2005/1541",
      "excerpt": "The responsible person must ensure that a suitable and sufficient assessment of the risks to which relevant persons are exposed is made."
    },
    {
      "source_type": "legislation",
      "act_name": "Fire Safety Act 2021",
      "section": "Section 1",
      "uri": "https://www.legislation.gov.uk/ukpga/2021/24",
      "excerpt": "The Fire Safety Order is amended to clarify that the responsible person must ensure fire safety in the structure and external walls of buildings."
    },
    {
      "source_type": "legislation",
      "act_name": "Building Safety Act 2022",
      "section": "Section 72",
      "uri": "https://www.legislation.gov.uk/ukpga/2022/30",
      "excerpt": "The accountable person must take all reasonable steps to prevent a building safety risk materialising."
    }
  ],
  "recommendations": []
}"""
    elif "Accountable Person" in criterion_name:
        return """{
  "rating": "green",
  "justification": "The policy clearly defines the Fire Safety Manager as the designated accountable person under the Building Safety Act 2022 for all high-rise residential buildings over 18 metres. This directly addresses the legislative requirement.",
  "citations": [
    {
      "source_type": "legislation",
      "act_name": "Building Safety Act 2022",
      "section": "Section 72",
      "uri": "https://www.legislation.gov.uk/ukpga/2022/30",
      "excerpt": "The accountable person must take all reasonable steps to prevent a building safety risk materialising."
    }
  ],
  "recommendations": []
}"""
    elif "PEEPs" in criterion_name:
        return """{
  "rating": "green",
  "justification": "The policy includes a dedicated section on Personal Emergency Evacuation Plans (PEEPs) describing the process for creating plans for residents requiring assistance, with annual reviews and updates when circumstances change. This fully meets the requirement.",
  "citations": [],
  "recommendations": []
}"""
    else:
        return """{
  "rating": "amber",
  "justification": "Criterion partially addressed but could be strengthened.",
  "citations": [],
  "recommendations": ["Add more specific details"]
}"""


@pytest.mark.asyncio
async def test_policy_review_end_to_end(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user,  # type: ignore[no-untyped-def]
    fire_safety_policy_definition: PolicyDefinition,
    mock_redis: Redis,  # type: ignore[type-arg]
    mock_anthropic_client: anthropic.AsyncAnthropic,
    mock_lex_client: LexRestClient,
) -> None:
    """Test full policy review pipeline with mock fire safety policy.

    This test verifies:
    1. Policy type is identified (or pre-specified)
    2. Each compliance criterion is evaluated
    3. RAG ratings are assigned with justification
    4. Citations from Lex are included
    5. Gap analysis is generated
    6. Recommended actions are created
    7. Overall rating is calculated
    8. Review state progresses to COMPLETE
    """
    # Mock Anthropic responses for criterion evaluations
    def mock_create_response(criterion_prompt: str) -> Mock:
        mock_response = Mock()
        mock_content_block = Mock()

        # Determine which criterion is being evaluated based on prompt content
        if "Current Fire Safety Legislation" in criterion_prompt:
            mock_content_block.text = mock_criterion_evaluation(
                "Current Fire Safety Legislation"
            )
        elif "Accountable Person" in criterion_prompt:
            mock_content_block.text = mock_criterion_evaluation("Accountable Person")
        elif "PEEPs" in criterion_prompt:
            mock_content_block.text = mock_criterion_evaluation("PEEPs")
        else:
            # Summary generation
            mock_content_block.text = (
                "This fire safety policy demonstrates strong compliance with current "
                "legislation. All three key pieces of fire safety legislation are "
                "referenced. The accountable person role is clearly defined. PEEPs "
                "process is comprehensive. The policy is rated GREEN overall."
            )

        mock_response.content = [mock_content_block]
        return mock_response

    # Mock Anthropic client to return appropriate responses
    async def mock_messages_create(**kwargs):  # type: ignore[no-untyped-def]
        messages = kwargs.get("messages", [])
        if messages:
            user_content = messages[0].get("content", "")
            return mock_create_response(user_content)
        return mock_create_response("")

    mock_anthropic_client.messages.create = AsyncMock(side_effect=mock_messages_create)

    # Create review engine
    engine = PolicyReviewEngine(
        test_session,
        mock_redis,
        mock_anthropic_client,
        mock_lex_client,
    )

    # Start review with pre-specified policy definition (skip type identification)
    review_id = await engine.start_review(
        document_text=MOCK_FIRE_SAFETY_POLICY,
        document_name="fire-safety-policy-2024.pdf",
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        policy_definition_id=fire_safety_policy_definition.id,
    )

    # Verify review was created
    assert review_id is not None

    # Fetch review result
    review = await engine.get_review(review_id, sample_tenant.id)

    # Verify review state
    assert review.state == PolicyReviewState.COMPLETE

    # Verify result structure
    assert review.result is not None
    assert "overall_rating" in review.result
    assert "legal_evaluation" in review.result
    assert "gap_analysis" in review.result
    assert "recommended_actions" in review.result
    assert "summary" in review.result

    # Verify criterion evaluations
    legal_evaluation = review.result["legal_evaluation"]
    assert len(legal_evaluation) == 3  # 3 compliance criteria

    # Verify all criteria have RAG ratings
    for criterion_result in legal_evaluation:
        assert criterion_result["rating"] in [RAGRating.GREEN, RAGRating.AMBER, RAGRating.RED]
        assert criterion_result["justification"]
        assert "criterion_name" in criterion_result

    # Verify citations are present (from Lex search)
    legislation_criterion = next(
        (
            c
            for c in legal_evaluation
            if "Legislation" in c["criterion_name"]
        ),
        None,
    )
    assert legislation_criterion is not None
    assert len(legislation_criterion["citations"]) > 0

    # Verify citation structure
    first_citation = legislation_criterion["citations"][0]
    assert first_citation["source_type"] == "legislation"
    assert first_citation["act_name"]
    assert first_citation["uri"]

    # Verify overall rating calculation (all green = overall green)
    assert review.result["overall_rating"] == RAGRating.GREEN

    # Verify summary was generated
    assert len(review.result["summary"]) > 50  # Should be a substantial summary

    # Verify SSE events were published
    # Note: In real implementation, we'd verify specific event types
    assert mock_redis.publish.called or mock_redis.publish.called  # Either sync or async

    # Verify Lex was queried for legislation
    assert mock_lex_client.search_legislation_sections.called
    call_args = mock_lex_client.search_legislation_sections.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_policy_review_with_red_rating(
    test_session: AsyncSession,
    sample_tenant: Tenant,
    sample_user,  # type: ignore[no-untyped-def]
    mock_redis: Redis,  # type: ignore[type-arg]
    mock_anthropic_client: anthropic.AsyncAnthropic,
    mock_lex_client: LexRestClient,
) -> None:
    """Test review with non-compliant policy that should get RED ratings."""
    # Create policy definition with stricter criteria
    definition = PolicyDefinition(
        id=uuid_utils.uuid7(),
        tenant_id=sample_tenant.id,
        name="Test Policy",
        uri="test-policy",
        status="active",
        required_sections=["Critical Section", "Another Critical Section"],
        compliance_criteria=[
            {
                "name": "Critical Compliance Item",
                "priority": "high",
                "description": "Must include critical compliance element",
                "criteria_type": "mandatory",
            }
        ],
    )
    test_session.add(definition)
    await test_session.flush()

    # Mock non-compliant policy (missing critical content)
    non_compliant_policy = "This is a very brief policy with no real content."

    # Mock LLM to return RED rating
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.text = """{
  "rating": "red",
  "justification": "Policy does not address the critical compliance requirement. No evidence of required procedures or legislative references.",
  "citations": [],
  "recommendations": [
    "Add section addressing critical compliance requirement",
    "Include references to relevant legislation"
  ]
}"""
    mock_response.content = [mock_content_block]
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    # Create and run review
    engine = PolicyReviewEngine(
        test_session,
        mock_redis,
        mock_anthropic_client,
        mock_lex_client,
    )

    review_id = await engine.start_review(
        document_text=non_compliant_policy,
        document_name="non-compliant-policy.pdf",
        tenant_id=sample_tenant.id,
        user_id=sample_user.id,
        policy_definition_id=definition.id,
    )

    review = await engine.get_review(review_id, sample_tenant.id)

    # Verify RED overall rating
    assert review.result["overall_rating"] == RAGRating.RED

    # Verify gap analysis was generated (missing required sections)
    assert len(review.result["gap_analysis"]) >= 2  # At least 2 missing sections

    # Verify recommended actions were generated
    assert len(review.result["recommended_actions"]) > 0

    # Verify at least one critical priority action
    assert any(
        action["priority"] == "critical"
        for action in review.result["recommended_actions"]
    )
