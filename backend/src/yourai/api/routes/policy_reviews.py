"""Policy review routes — start reviews, get results, export PDFs, trends."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import anthropic
import structlog
from fastapi import APIRouter, Depends, Query, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.api.sse.dependencies import get_redis
from yourai.core.config import settings
from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, get_current_user, require_permission
from yourai.core.models import User
from yourai.core.schemas import TenantConfig
from yourai.knowledge.lex_rest import LexRestClient
from yourai.policy.enums import PolicyReviewState
from yourai.policy.pdf_export import ReportExporter
from yourai.policy.review_engine import PolicyReviewEngine
from yourai.policy.review_history import ReviewHistoryService
from yourai.policy.schemas import (
    ComparisonResult,
    PolicyReviewResponse,
    ReviewTrends,
    StartReviewRequest,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/policy-reviews", tags=["policy-reviews"])


@router.post("", response_model=PolicyReviewResponse, status_code=201)
async def start_policy_review(
    data: StartReviewRequest,
    tenant: TenantConfig = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("create_policy_review")),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> PolicyReviewResponse:
    """Start a new policy review.

    Triggers async review execution. Client should listen on SSE stream
    for progress updates.
    """
    log = logger.bind(tenant_id=str(tenant.id), user_id=str(current_user.id))
    policy_def_id = str(data.policy_definition_id) if data.policy_definition_id else None
    log.info("policy_review_start_requested", policy_definition_id=policy_def_id)

    # Create engine with dependencies
    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    lex_client = LexRestClient(base_url=settings.lex_base_url)

    engine = PolicyReviewEngine(
        session=session,
        redis=redis,
        anthropic_client=anthropic_client,
        lex_client=lex_client,
    )

    # Start review (async task in background)
    review_id = await engine.start_review(
        document_text=data.document_text,
        document_name=data.document_name,
        tenant_id=tenant.id,
        user_id=current_user.id,
        policy_definition_id=data.policy_definition_id,
    )

    await session.commit()

    # Fetch the created review to return
    from uuid import UUID as UUID_STD

    from sqlalchemy import select

    from yourai.policy.models import PolicyReview

    result = await session.execute(
        select(PolicyReview).where(
            PolicyReview.id == review_id,
            PolicyReview.tenant_id == tenant.id,
        )
    )
    review = result.scalar_one()

    return PolicyReviewResponse(
        id=UUID_STD(str(review.id)),
        tenant_id=UUID_STD(str(review.tenant_id)),
        request_id=UUID_STD(str(review.request_id)) if review.request_id else None,
        user_id=UUID_STD(str(review.user_id)),
        policy_definition_id=(
            UUID_STD(str(review.policy_definition_id)) if review.policy_definition_id else None
        ),
        state=review.state,
        result=review.result,
        source=review.source,
        citation_verification_result=review.citation_verification_result,
        version=review.version,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.get("/{review_id}", response_model=PolicyReviewResponse)
async def get_policy_review(
    review_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> PolicyReviewResponse:
    """Get a policy review by ID."""
    history_service = ReviewHistoryService(session)

    # Get review (returns list with single item)
    reviews, total = await history_service.list_reviews(
        tenant_id=tenant.id,
        page=1,
        page_size=1,
    )

    # Filter by ID in application (simpler than adding get_by_id method)
    from sqlalchemy import select

    from yourai.core.exceptions import NotFoundError
    from yourai.policy.models import PolicyReview

    result = await session.execute(
        select(PolicyReview).where(
            PolicyReview.id == review_id,
            PolicyReview.tenant_id == tenant.id,
        )
    )
    review = result.scalar_one_or_none()

    if review is None:
        raise NotFoundError(f"Policy review {review_id} not found")

    from uuid import UUID as UUID_STD

    return PolicyReviewResponse(
        id=UUID_STD(str(review.id)),
        tenant_id=UUID_STD(str(review.tenant_id)),
        request_id=UUID_STD(str(review.request_id)) if review.request_id else None,
        user_id=UUID_STD(str(review.user_id)),
        policy_definition_id=(
            UUID_STD(str(review.policy_definition_id)) if review.policy_definition_id else None
        ),
        state=review.state,
        result=review.result,
        source=review.source,
        citation_verification_result=review.citation_verification_result,
        version=review.version,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.get("", response_model=dict[str, object])
async def list_policy_reviews(
    policy_definition_id: UUID | None = Query(None),
    state: PolicyReviewState | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """List policy reviews with filtering and pagination.

    Returns: {items: [...], total: N, page: 1, page_size: 20}
    """
    history_service = ReviewHistoryService(session)

    reviews, total = await history_service.list_reviews(
        tenant_id=tenant.id,
        policy_definition_id=policy_definition_id,
        state=state,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

    return {
        "items": reviews,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{review_id}/cancel", status_code=204)
async def cancel_policy_review(
    review_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("create_policy_review")),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> Response:
    """Cancel a pending or processing policy review."""
    log = logger.bind(
        tenant_id=str(tenant.id), user_id=str(current_user.id), review_id=str(review_id)
    )
    log.info("policy_review_cancel_requested")

    # Create engine with minimal dependencies (only needs session + redis for cancellation)
    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    lex_client = LexRestClient(base_url=settings.lex_base_url)

    engine = PolicyReviewEngine(
        session=session,
        redis=redis,
        anthropic_client=anthropic_client,
        lex_client=lex_client,
    )

    await engine.cancel_review(review_id, tenant.id)
    await session.commit()

    log.info("policy_review_cancelled")
    return Response(status_code=204)


@router.get("/{review_id}/export", response_class=Response)
async def export_policy_review_pdf(
    review_id: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Export policy review as a branded PDF report."""
    log = logger.bind(tenant_id=str(tenant.id), review_id=str(review_id))
    log.info("policy_review_pdf_export_requested")

    exporter = ReportExporter(session)
    pdf_bytes = await exporter.export_pdf(review_id, tenant.id)

    log.info("policy_review_pdf_export_complete", size_bytes=len(pdf_bytes))

    # Return PDF with appropriate headers
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=policy_review_{review_id}.pdf"
        },
    )


@router.get("/trends/aggregate", response_model=ReviewTrends)
async def get_policy_review_trends(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("view_admin_dashboard")),
    session: AsyncSession = Depends(get_db_session),
) -> ReviewTrends:
    """Get aggregate compliance trends for admin dashboard.

    Requires admin dashboard permission.
    """
    history_service = ReviewHistoryService(session)

    trends = await history_service.get_trends(
        tenant_id=tenant.id,
        date_from=date_from,
        date_to=date_to,
    )

    return trends


@router.get("/{review_id_1}/compare/{review_id_2}", response_model=ComparisonResult)
async def compare_policy_reviews(
    review_id_1: UUID,
    review_id_2: UUID,
    tenant: TenantConfig = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> ComparisonResult:
    """Compare two reviews of the same policy type.

    Shows rating changes per criterion between the two reviews.
    """
    history_service = ReviewHistoryService(session)

    comparison = await history_service.compare_reviews(
        review_id_1=review_id_1,
        review_id_2=review_id_2,
        tenant_id=tenant.id,
    )

    return comparison
