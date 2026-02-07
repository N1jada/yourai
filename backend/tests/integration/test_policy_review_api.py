"""Integration tests for policy review API endpoints."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest

from yourai.policy.enums import PolicyReviewState
from yourai.policy.schemas import (
    ComplianceCriterion,
    PolicyDefinitionResponse,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

    from tests.integration.conftest import IntegrationTestContext


@pytest.fixture
async def policy_definition(ctx: IntegrationTestContext) -> PolicyDefinitionResponse:
    """Create a test policy definition."""
    # Create via service (not API, to simplify setup)
    from yourai.policy.ontology import PolicyOntologyService
    from yourai.policy.schemas import CreatePolicyDefinition

    service = PolicyOntologyService(ctx.session)

    definition = await service.create_policy_definition(
        ctx.tenant.id,
        CreatePolicyDefinition(
            name="Fire Safety Policy (Test)",
            uri="fire-safety-test",
            description="Test fire safety policy definition",
            compliance_criteria=[
                ComplianceCriterion(
                    name="Fire Risk Assessment",
                    priority="high",
                    description="Policy must require regular fire risk assessments",
                    criteria_type="mandatory",
                ),
                ComplianceCriterion(
                    name="Evacuation Procedures",
                    priority="high",
                    description="Policy must define clear evacuation procedures",
                    criteria_type="mandatory",
                ),
            ],
        ),
    )

    await ctx.session.commit()
    return definition


@pytest.mark.asyncio
async def test_start_policy_review_and_poll_status(
    client: AsyncClient,
    ctx: IntegrationTestContext,
    policy_definition: PolicyDefinitionResponse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test starting a policy review and polling for completion."""
    from anthropic.types import Message, TextBlock, Usage

    # Mock Anthropic API to return immediate success
    mock_message = Message(
        id="msg_test",
        type="message",
        role="assistant",
        content=[
            TextBlock(
                type="text",
                text='{"rating": "green", "justification": "Compliant", "citations": []}',
            )
        ],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        usage=Usage(input_tokens=100, output_tokens=50),
    )

    async def mock_create(*args, **kwargs):  # noqa: ANN002, ANN003, ARG001
        return mock_message

    # Mock SearchService to avoid voyageai dependency
    mock_search = AsyncMock()
    mock_search.hybrid_search = AsyncMock(return_value=[])

    # Mock LexRestClient
    mock_lex = AsyncMock()
    mock_lex.search_legislation_sections = AsyncMock(return_value=[])

    # Mock Redis pipeline for SSE events
    mock_pipeline = AsyncMock()
    mock_pipeline.zadd = Mock(return_value=mock_pipeline)
    mock_pipeline.expire = Mock(return_value=mock_pipeline)
    mock_pipeline.execute = AsyncMock(return_value=[1, True])

    # Patch all dependencies
    monkeypatch.setattr("yourai.policy.evaluator.SearchService", lambda session: mock_search)
    monkeypatch.setattr("anthropic.AsyncAnthropic.messages.create", mock_create)
    monkeypatch.setattr(
        "yourai.policy.type_identifier.PolicyTypeIdentifier.identify_policy_type",
        AsyncMock(
            return_value={
                "matched_definition_id": policy_definition.id,
                "matched_definition_uri": policy_definition.uri,
                "matched_definition_name": policy_definition.name,
                "confidence": 0.95,
                "reasoning": "Test match",
                "alternative_matches": [],
            }
        ),
    )

    # Mock redis.pipeline()
    async def mock_redis_init(url: str):  # noqa: ARG001
        redis_mock = AsyncMock()
        redis_mock.pipeline = Mock(return_value=mock_pipeline)
        return redis_mock

    monkeypatch.setattr("redis.asyncio.from_url", mock_redis_init)

    # Mock Lex client in routes
    monkeypatch.setattr("yourai.api.routes.policy_reviews.LexRestClient", lambda **kwargs: mock_lex)

    # Start a policy review
    document_text = """
    Fire Safety Policy

    1. Fire Risk Assessment
    We conduct regular fire risk assessments annually and whenever significant changes occur.

    2. Evacuation Procedures
    In the event of a fire alarm:
    - Evacuate via the nearest safe exit
    - Assemble at the designated meeting point
    - Do not use lifts
    - Do not re-enter the building until authorized
    """

    response = await client.post(
        "/api/v1/policy-reviews",
        json={
            "document_text": document_text,
            "document_name": "test_fire_safety.txt",
            "policy_definition_id": str(policy_definition.id),
        },
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 201
    review_data = response.json()
    review_id = review_data["id"]
    assert review_data["state"] == PolicyReviewState.PENDING

    # Poll for completion (simulate async execution by waiting briefly)
    # In a real scenario, the background task would complete.
    # Here we just verify the endpoint works.
    await asyncio.sleep(0.1)

    response = await client.get(
        f"/api/v1/policy-reviews/{review_id}",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 200
    review = response.json()
    assert review["id"] == review_id
    # State may still be PENDING since we didn't actually run the background task


@pytest.mark.asyncio
async def test_list_policy_reviews_with_filters(
    client: AsyncClient,
    ctx: IntegrationTestContext,
    policy_definition: PolicyDefinitionResponse,
) -> None:
    """Test listing policy reviews with filters."""
    # Create a few test reviews manually in the database
    from yourai.policy.models import PolicyReview

    review1 = PolicyReview(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        policy_definition_id=policy_definition.id,
        state=PolicyReviewState.COMPLETE,
        result={"overall_rating": "green"},
        source="test",
        version=1,
    )

    review2 = PolicyReview(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        policy_definition_id=policy_definition.id,
        state=PolicyReviewState.COMPLETE,
        result={"overall_rating": "amber"},
        source="test",
        version=1,
    )

    ctx.session.add(review1)
    ctx.session.add(review2)
    await ctx.session.commit()

    # List all reviews
    response = await client.get(
        "/api/v1/policy-reviews",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    # Filter by policy_definition_id
    response = await client.get(
        f"/api/v1/policy-reviews?policy_definition_id={policy_definition.id}",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2

    # Filter by state
    response = await client.get(
        f"/api/v1/policy-reviews?state={PolicyReviewState.COMPLETE}",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    for item in data["items"]:
        assert item["state"] == PolicyReviewState.COMPLETE


@pytest.mark.asyncio
async def test_export_pdf(
    client: AsyncClient,
    ctx: IntegrationTestContext,
    policy_definition: PolicyDefinitionResponse,
) -> None:
    """Test exporting a policy review as PDF."""
    # Create a complete review with full result
    from yourai.policy.models import PolicyReview

    review = PolicyReview(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        policy_definition_id=policy_definition.id,
        state=PolicyReviewState.COMPLETE,
        result={
            "policy_definition_id": str(policy_definition.id),
            "policy_definition_name": policy_definition.name,
            "overall_rating": "green",
            "confidence": "high",
            "legal_evaluation": [
                {
                    "criterion_name": "Fire Risk Assessment",
                    "criterion_priority": "high",
                    "rating": "green",
                    "justification": "Policy requires regular assessments",
                    "citations": [],
                    "recommendations": [],
                }
            ],
            "gap_analysis": [],
            "recommended_actions": [],
            "summary": "Policy is fully compliant with fire safety requirements.",
        },
        source="test",
        version=1,
    )

    ctx.session.add(review)
    await ctx.session.commit()

    # Export PDF
    response = await client.get(
        f"/api/v1/policy-reviews/{review.id}/export",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers["content-disposition"]

    # Verify PDF is not empty
    pdf_bytes = response.content
    assert len(pdf_bytes) > 1000  # Should be at least a few KB
    assert pdf_bytes[:4] == b"%PDF"  # PDF magic number


@pytest.mark.asyncio
async def test_compare_reviews(
    client: AsyncClient,
    ctx: IntegrationTestContext,
    policy_definition: PolicyDefinitionResponse,
) -> None:
    """Test comparing two reviews of the same policy type."""
    from yourai.policy.models import PolicyReview

    # Create two reviews with different ratings
    review1 = PolicyReview(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        policy_definition_id=policy_definition.id,
        state=PolicyReviewState.COMPLETE,
        result={
            "policy_definition_id": str(policy_definition.id),
            "policy_definition_name": policy_definition.name,
            "overall_rating": "amber",
            "legal_evaluation": [
                {
                    "criterion_name": "Fire Risk Assessment",
                    "rating": "amber",
                },
                {
                    "criterion_name": "Evacuation Procedures",
                    "rating": "green",
                },
            ],
        },
        source="test",
        version=1,
    )

    review2 = PolicyReview(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        policy_definition_id=policy_definition.id,
        state=PolicyReviewState.COMPLETE,
        result={
            "policy_definition_id": str(policy_definition.id),
            "policy_definition_name": policy_definition.name,
            "overall_rating": "green",
            "legal_evaluation": [
                {
                    "criterion_name": "Fire Risk Assessment",
                    "rating": "green",
                },
                {
                    "criterion_name": "Evacuation Procedures",
                    "rating": "green",
                },
            ],
        },
        source="test",
        version=1,
    )

    ctx.session.add(review1)
    ctx.session.add(review2)
    await ctx.session.commit()

    # Compare the two reviews
    response = await client.get(
        f"/api/v1/policy-reviews/{review1.id}/compare/{review2.id}",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 200
    comparison = response.json()

    assert comparison["review1_id"] == str(review1.id)
    assert comparison["review2_id"] == str(review2.id)
    assert comparison["review1_overall_rating"] == "amber"
    assert comparison["review2_overall_rating"] == "green"

    # Verify criteria comparisons
    assert len(comparison["criteria_comparisons"]) == 2

    # Find the Fire Risk Assessment comparison
    fire_assessment_comparison = next(
        c
        for c in comparison["criteria_comparisons"]
        if c["criterion_name"] == "Fire Risk Assessment"
    )
    assert fire_assessment_comparison["previous_rating"] == "amber"
    assert fire_assessment_comparison["current_rating"] == "green"
    assert fire_assessment_comparison["changed"] is True

    # Evacuation Procedures should be unchanged
    evacuation_comparison = next(
        c
        for c in comparison["criteria_comparisons"]
        if c["criterion_name"] == "Evacuation Procedures"
    )
    assert evacuation_comparison["previous_rating"] == "green"
    assert evacuation_comparison["current_rating"] == "green"
    assert evacuation_comparison["changed"] is False


@pytest.mark.asyncio
async def test_get_trends(
    client: AsyncClient,
    ctx: IntegrationTestContext,
    policy_definition: PolicyDefinitionResponse,
) -> None:
    """Test getting compliance trends."""
    from yourai.policy.models import PolicyReview

    # Mark the policy definition as required
    await ctx.session.execute(
        """
        UPDATE policy_definitions
        SET is_required = true
        WHERE id = :id
        """,
        {"id": policy_definition.id},
    )

    # Create multiple reviews with different ratings
    reviews = [
        PolicyReview(
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
            policy_definition_id=policy_definition.id,
            state=PolicyReviewState.COMPLETE,
            result={"overall_rating": "green"},
            source="test",
            version=1,
        ),
        PolicyReview(
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
            policy_definition_id=policy_definition.id,
            state=PolicyReviewState.COMPLETE,
            result={"overall_rating": "amber"},
            source="test",
            version=1,
        ),
        PolicyReview(
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
            policy_definition_id=policy_definition.id,
            state=PolicyReviewState.COMPLETE,
            result={"overall_rating": "red"},
            source="test",
            version=1,
        ),
    ]

    for review in reviews:
        ctx.session.add(review)

    await ctx.session.commit()

    # Get trends
    response = await client.get(
        "/api/v1/policy-reviews/trends/aggregate",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 200
    trends = response.json()

    assert trends["total_reviews"] >= 3
    assert trends["green_count"] >= 1
    assert trends["amber_count"] >= 1
    assert trends["red_count"] >= 1

    # Verify percentages add up to ~100
    total_pct = (
        trends["green_percentage"] + trends["amber_percentage"] + trends["red_percentage"]
    )
    assert 99.0 <= total_pct <= 101.0  # Allow for rounding

    # Verify required policy coverage
    assert trends["required_policies_total"] >= 1
    assert trends["required_policies_reviewed_count"] >= 1
    assert trends["required_policies_coverage_percentage"] > 0


@pytest.mark.asyncio
async def test_cancel_review(
    client: AsyncClient,
    ctx: IntegrationTestContext,
    policy_definition: PolicyDefinitionResponse,
) -> None:
    """Test cancelling a policy review."""
    from yourai.policy.models import PolicyReview

    # Create a pending review
    review = PolicyReview(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        policy_definition_id=policy_definition.id,
        state=PolicyReviewState.PENDING,
        source="test",
        version=1,
    )

    ctx.session.add(review)
    await ctx.session.commit()

    # Cancel the review
    response = await client.post(
        f"/api/v1/policy-reviews/{review.id}/cancel",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    assert response.status_code == 204

    # Verify review was cancelled
    await ctx.session.refresh(review)
    assert review.state == PolicyReviewState.CANCELLED


@pytest.mark.asyncio
async def test_cannot_cancel_completed_review(
    client: AsyncClient,
    ctx: IntegrationTestContext,
    policy_definition: PolicyDefinitionResponse,
) -> None:
    """Test that completed reviews cannot be cancelled."""
    from yourai.policy.models import PolicyReview

    # Create a completed review
    review = PolicyReview(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        policy_definition_id=policy_definition.id,
        state=PolicyReviewState.COMPLETE,
        result={"overall_rating": "green"},
        source="test",
        version=1,
    )

    ctx.session.add(review)
    await ctx.session.commit()

    # Try to cancel the review
    response = await client.post(
        f"/api/v1/policy-reviews/{review.id}/cancel",
        headers={"Authorization": f"Bearer {ctx.access_token}"},
    )

    # Should fail (either 400 or 409)
    assert response.status_code in (400, 409, 422)
