"""Review history service — track reviews, trends, and comparisons."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from yourai.policy.enums import PolicyReviewState
from yourai.policy.models import PolicyDefinition, PolicyReview
from yourai.policy.schemas import (
    ComparisonResult,
    CriterionComparison,
    PolicyReviewResponse,
    ReviewTrends,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class ReviewHistoryService:
    """Service for review history, comparisons, and trend analysis."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_reviews(
        self,
        tenant_id: UUID,
        policy_definition_id: UUID | None = None,
        state: PolicyReviewState | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PolicyReviewResponse], int]:
        """List reviews with filtering and pagination.

        Returns (reviews, total_count).
        """
        # Build query
        query = select(PolicyReview).where(PolicyReview.tenant_id == tenant_id)

        if policy_definition_id is not None:
            query = query.where(PolicyReview.policy_definition_id == policy_definition_id)

        if state is not None:
            query = query.where(PolicyReview.state == state)

        if date_from is not None:
            query = query.where(PolicyReview.created_at >= date_from)

        if date_to is not None:
            query = query.where(PolicyReview.created_at <= date_to)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self._session.execute(count_query)
        total_count = count_result.scalar_one()

        # Apply pagination and ordering
        query = query.order_by(PolicyReview.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(query)
        reviews = result.scalars().all()

        return [self._to_response(r) for r in reviews], total_count

    async def compare_reviews(
        self,
        review_id_1: UUID,
        review_id_2: UUID,
        tenant_id: UUID,
    ) -> ComparisonResult:
        """Compare two reviews of the same policy type.

        Shows rating changes per criterion.
        """
        # Load both reviews
        result = await self._session.execute(
            select(PolicyReview).where(
                PolicyReview.id.in_([review_id_1, review_id_2]),
                PolicyReview.tenant_id == tenant_id,
            )
        )
        reviews = list(result.scalars().all())

        if len(reviews) != 2:
            raise ValueError("Both reviews must exist and belong to the tenant")

        review1, review2 = sorted(reviews, key=lambda r: r.created_at or 0)

        if review1.policy_definition_id != review2.policy_definition_id:
            raise ValueError("Reviews must be for the same policy definition")

        # Compare criterion results
        criteria_comparisons: list[CriterionComparison] = []

        result1 = review1.result or {}
        result2 = review2.result or {}

        legal_eval1 = result1.get("legal_evaluation", [])
        legal_eval2 = result2.get("legal_evaluation", [])

        # Build map of criterion name -> rating for both reviews
        ratings1 = {c["criterion_name"]: c["rating"] for c in legal_eval1}
        ratings2 = {c["criterion_name"]: c["rating"] for c in legal_eval2}

        # Compare each criterion
        all_criteria = set(ratings1.keys()) | set(ratings2.keys())
        for criterion_name in sorted(all_criteria):
            rating1 = ratings1.get(criterion_name)
            rating2 = ratings2.get(criterion_name)

            if rating1 != rating2:
                criteria_comparisons.append(
                    CriterionComparison(
                        criterion_name=criterion_name,
                        previous_rating=rating1 or "unknown",
                        current_rating=rating2 or "unknown",
                        changed=True,
                    )
                )
            else:
                criteria_comparisons.append(
                    CriterionComparison(
                        criterion_name=criterion_name,
                        previous_rating=rating1 or "unknown",
                        current_rating=rating2 or "unknown",
                        changed=False,
                    )
                )

        return ComparisonResult(
            review1_id=review1.id,
            review1_date=review1.created_at,
            review1_overall_rating=result1.get("overall_rating", "unknown"),
            review2_id=review2.id,
            review2_date=review2.created_at,
            review2_overall_rating=result2.get("overall_rating", "unknown"),
            criteria_comparisons=criteria_comparisons,
        )

    async def get_trends(
        self,
        tenant_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ReviewTrends:
        """Get aggregate compliance trends for admin dashboard."""
        # Build base query
        query = select(PolicyReview).where(
            PolicyReview.tenant_id == tenant_id,
            PolicyReview.state == PolicyReviewState.COMPLETE,
        )

        if date_from is not None:
            query = query.where(PolicyReview.created_at >= date_from)

        if date_to is not None:
            query = query.where(PolicyReview.created_at <= date_to)

        result = await self._session.execute(query)
        reviews = list(result.scalars().all())

        if not reviews:
            return ReviewTrends(
                total_reviews=0,
                green_count=0,
                amber_count=0,
                red_count=0,
                green_percentage=0.0,
                amber_percentage=0.0,
                red_percentage=0.0,
                required_policies_reviewed_count=0,
                required_policies_total=0,
                required_policies_coverage_percentage=0.0,
            )

        # Count RAG ratings
        green_count = 0
        amber_count = 0
        red_count = 0

        for review in reviews:
            result_data = review.result or {}
            overall_rating = result_data.get("overall_rating", "").lower()
            if overall_rating == "green":
                green_count += 1
            elif overall_rating == "amber":
                amber_count += 1
            elif overall_rating == "red":
                red_count += 1

        total = len(reviews)

        # Get count of required policy definitions
        required_query = select(func.count()).select_from(
            select(PolicyDefinition)
            .where(
                PolicyDefinition.tenant_id == tenant_id,
                PolicyDefinition.is_required == True,  # noqa: E712
                PolicyDefinition.status == "active",
            )
            .subquery()
        )
        required_result = await self._session.execute(required_query)
        required_total = required_result.scalar_one()

        # Count how many required policies have at least one review
        reviewed_required_query = select(
            func.count(func.distinct(PolicyReview.policy_definition_id))
        ).where(
            PolicyReview.tenant_id == tenant_id,
            PolicyReview.state == PolicyReviewState.COMPLETE,
            PolicyReview.policy_definition_id.in_(
                select(PolicyDefinition.id).where(
                    PolicyDefinition.tenant_id == tenant_id,
                    PolicyDefinition.is_required == True,  # noqa: E712
                    PolicyDefinition.status == "active",
                )
            ),
        )

        if date_from is not None:
            reviewed_required_query = reviewed_required_query.where(
                PolicyReview.created_at >= date_from
            )
        if date_to is not None:
            reviewed_required_query = reviewed_required_query.where(
                PolicyReview.created_at <= date_to
            )

        reviewed_required_result = await self._session.execute(reviewed_required_query)
        reviewed_required_count = reviewed_required_result.scalar_one()

        return ReviewTrends(
            total_reviews=total,
            green_count=green_count,
            amber_count=amber_count,
            red_count=red_count,
            green_percentage=round((green_count / total) * 100, 1) if total > 0 else 0.0,
            amber_percentage=round((amber_count / total) * 100, 1) if total > 0 else 0.0,
            red_percentage=round((red_count / total) * 100, 1) if total > 0 else 0.0,
            required_policies_reviewed_count=reviewed_required_count,
            required_policies_total=required_total,
            required_policies_coverage_percentage=(
                round((reviewed_required_count / required_total) * 100, 1)
                if required_total > 0
                else 0.0
            ),
        )

    @staticmethod
    def _to_response(review: PolicyReview) -> PolicyReviewResponse:
        """Convert ORM model to response schema."""
        from uuid import UUID

        return PolicyReviewResponse(
            id=UUID(str(review.id)),
            tenant_id=UUID(str(review.tenant_id)),
            request_id=UUID(str(review.request_id)) if review.request_id else None,
            user_id=UUID(str(review.user_id)),
            policy_definition_id=(
                UUID(str(review.policy_definition_id)) if review.policy_definition_id else None
            ),
            state=review.state,
            result=review.result,
            source=review.source,
            citation_verification_result=review.citation_verification_result,
            version=review.version,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
