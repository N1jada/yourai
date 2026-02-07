"""Policy review engine — main orchestrator for compliance reviews."""

from __future__ import annotations

from datetime import UTC, datetime
import asyncio
from typing import TYPE_CHECKING

import structlog
import uuid_utils
from sqlalchemy import select

from yourai.agents.model_routing import ModelRouter
from yourai.api.sse.channels import SSEChannel
from yourai.api.sse.events import (
    AgentCompleteEvent,
    AgentProgressEvent,
    AgentStartEvent,
)
from yourai.api.sse.publisher import EventPublisher
from yourai.policy.enums import PolicyReviewState, RAGRating
from yourai.policy.evaluator import ComplianceEvaluator
from yourai.policy.models import PolicyDefinition, PolicyReview
from yourai.policy.schemas import (
    Action,
    ComplianceCriterion,
    CriterionResult,
    GapItem,
    PolicyReviewResult,
)
from yourai.policy.type_identifier import PolicyTypeIdentifier

if TYPE_CHECKING:
    from uuid import UUID

    import anthropic
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

    from yourai.knowledge.lex_rest import LexRestClient

logger = structlog.get_logger()


class PolicyReviewEngine:
    """Main orchestrator for policy compliance reviews."""

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        anthropic_client: anthropic.AsyncAnthropic,
        lex_client: LexRestClient,
    ):
        self._session = session
        self._redis = redis
        self._client = anthropic_client
        self._lex_client = lex_client
        self._type_identifier = PolicyTypeIdentifier(anthropic_client)
        self._evaluator = ComplianceEvaluator(session, anthropic_client, lex_client)
        self._publisher = EventPublisher(redis)

    async def start_review(
        self,
        document_text: str,
        document_name: str,
        tenant_id: UUID,
        user_id: UUID,
        policy_definition_id: UUID | None = None,
    ) -> UUID:
        """Start a policy review. Returns review_id.

        If policy_definition_id is None, will auto-identify policy type.
        """
        log = logger.bind(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            document_name=document_name,
        )

        # Create review record
        review = PolicyReview(
            id=uuid_utils.uuid7(),
            tenant_id=tenant_id,
            user_id=user_id,
            policy_definition_id=policy_definition_id,
            state=PolicyReviewState.PENDING,
            source=document_name,
            version=1,
        )
        self._session.add(review)
        await self._session.flush()

        log.info("policy_review_created", review_id=str(review.id))

        # Emit start event
        channel = SSEChannel.for_user(tenant_id, user_id)
        await self._publisher.publish(
            channel,
            AgentStartEvent(
                agent_name="policy_review",
                task_description=f"Reviewing policy: {document_name}",
            ),
        )

        # Start async review (this would normally be a Celery task)
        # For now, run synchronously
        await self._execute_review(
            review.id,
            document_text,
            document_name,
            tenant_id,
            user_id,
            policy_definition_id,
        )

        return review.id

    async def _execute_review(
        self,
        review_id: UUID,
        document_text: str,
        document_name: str,
        tenant_id: UUID,
        user_id: UUID,
        policy_definition_id: UUID | None = None,
    ) -> None:
        """Execute the full review pipeline."""
        log = logger.bind(
            review_id=str(review_id),
            tenant_id=str(tenant_id),
            document_name=document_name,
        )

        channel = SSEChannel.for_user(tenant_id, user_id)

        try:
            # Update state to PROCESSING
            review = await self._get_review(review_id, tenant_id)
            review.state = PolicyReviewState.PROCESSING
            await self._session.flush()

            # Step 1: Identify policy type if not provided
            if policy_definition_id is None:
                await self._publisher.publish(
                    channel,
                    AgentProgressEvent(
                        agent_name="policy_review",
                        status_text="Identifying policy type...",
                    ),
                )

                identification = await self._type_identifier.identify_policy_type(
                    document_text, tenant_id, self._session
                )

                if identification.matched_definition_id is None:
                    raise ValueError("Could not identify policy type")

                policy_definition_id = identification.matched_definition_id
                review.policy_definition_id = policy_definition_id
                await self._session.flush()

                log.info(
                    "policy_type_identified",
                    policy_definition_id=str(policy_definition_id),
                    confidence=identification.confidence,
                )

            # Step 2: Load policy definition with criteria
            await self._publisher.publish(
                channel,
                AgentProgressEvent(
                    agent_name="policy_review",
                    status_text="Loading compliance criteria...",
                ),
            )

            policy_def = await self._get_policy_definition(policy_definition_id, tenant_id)

            # Step 3: Evaluate each compliance criterion
            log.info(
                "evaluating_criteria",
                criterion_count=len(policy_def.compliance_criteria),
            )

            criterion_results: list[CriterionResult] = []

            # Parse compliance criteria from JSON to Pydantic models
            criteria = [
                ComplianceCriterion(**c)
                if isinstance(c, dict)
                else c
                for c in policy_def.compliance_criteria
            ]


            for criterion in criteria:
                await self._publisher.publish(
                    channel,
                    AgentProgressEvent(
                        agent_name="policy_review",
                        status_text=f"Evaluating: {criterion.name}",
                    ),
                )

                result = await self._evaluator.evaluate_criterion(
                    criterion, document_text, tenant_id
                )
                criterion_results.append(result)

                log.info(
                    "criterion_evaluated",
                    criterion_name=criterion.name,
                    rating=result.rating,
                )

            # Step 4: Generate gap analysis
            await self._publisher.publish(
                channel,
                AgentProgressEvent(
                    agent_name="policy_review",
                    status_text="Analyzing gaps and generating recommendations...",
                ),
            )

            gap_analysis = await self._generate_gap_analysis(
                policy_def, document_text, criterion_results
            )

            # Step 5: Generate recommended actions
            recommended_actions = await self._generate_recommended_actions(
                criterion_results, gap_analysis
            )

            # Step 6: Calculate overall rating
            overall_rating = self._calculate_overall_rating(criterion_results)

            # Step 7: Generate summary
            summary = await self._generate_summary(
                policy_def, overall_rating, criterion_results, gap_analysis
            )

            # Step 8: Assemble result
            review_result = PolicyReviewResult(
                policy_definition_id=policy_def.id,
                policy_definition_name=policy_def.name,
                overall_rating=overall_rating,
                confidence="medium",  # TODO: Calculate based on criteria
                legal_evaluation=criterion_results,
                gap_analysis=gap_analysis,
                recommended_actions=recommended_actions,
                summary=summary,
                created_at=datetime.now(UTC),
            )

            # Step 9: Save result and update state
            review.result = review_result.model_dump()
            review.state = PolicyReviewState.COMPLETE
            await self._session.commit()

            # Step 10: Emit completion event
            await self._publisher.publish(
                channel,
                AgentCompleteEvent(
                    agent_name="policy_review",
                    duration_ms=0,  # TODO: Track actual duration
                ),
            )

            log.info(
                "policy_review_complete",
                overall_rating=overall_rating,
                criterion_count=len(criterion_results),
                gap_count=len(gap_analysis),
            )

        except TimeoutError:
            log.error("policy_review_timeout", review_id=str(review_id))
            review = await self._get_review(review_id, tenant_id)
            review.state = PolicyReviewState.ERROR
            review.result = {
                "error": "POLICY_REVIEW_TIMEOUT",
                "message": "Review exceeded maximum processing time",
            }
            await self._session.commit()

            # Emit error event
            await self._publisher.publish(
                channel,
                AgentCompleteEvent(
                    agent_name="policy_review",
                    duration_ms=0,
                    error="Review timed out",
                ),
            )
            raise

        except ValueError as e:
            # Handle validation errors (e.g., could not identify policy type)
            log.error("policy_review_validation_error", review_id=str(review_id), error=str(e))
            review = await self._get_review(review_id, tenant_id)
            review.state = PolicyReviewState.ERROR
            review.result = {
                "error": "VALIDATION_ERROR",
                "message": str(e),
            }
            await self._session.commit()

            await self._publisher.publish(
                channel,
                AgentCompleteEvent(
                    agent_name="policy_review",
                    duration_ms=0,
                    error=str(e),
                ),
            )
            raise

        except Exception as e:
            log.error("policy_review_failed", review_id=str(review_id), error=str(e))
            review = await self._get_review(review_id, tenant_id)
            review.state = PolicyReviewState.ERROR
            review.result = {
                "error": "INTERNAL_ERROR",
                "message": f"Unexpected error: {str(e)}",
            }
            await self._session.commit()

            await self._publisher.publish(
                channel,
                AgentCompleteEvent(
                    agent_name="policy_review",
                    duration_ms=0,
                    error=str(e),
                ),
            )
            raise

    async def _get_review(self, review_id: UUID, tenant_id: UUID) -> PolicyReview:
        """Get review by ID (tenant-scoped)."""
        result = await self._session.execute(
            select(PolicyReview).where(
                PolicyReview.id == review_id,
                PolicyReview.tenant_id == tenant_id,
            )
        )
        review = result.scalar_one_or_none()
        if review is None:
            raise ValueError(f"Review {review_id} not found")
        return review

    async def _get_policy_definition(
        self, definition_id: UUID, tenant_id: UUID
    ) -> PolicyDefinition:
        """Get policy definition by ID (tenant-scoped)."""
        result = await self._session.execute(
            select(PolicyDefinition).where(
                PolicyDefinition.id == definition_id,
                PolicyDefinition.tenant_id == tenant_id,
            )
        )
        definition = result.scalar_one_or_none()
        if definition is None:
            raise ValueError(f"Policy definition {definition_id} not found")
        return definition

    async def _generate_gap_analysis(
        self,
        policy_def: PolicyDefinition,
        document_text: str,
        criterion_results: list[CriterionResult],
    ) -> list[GapItem]:
        """Generate gap analysis from criterion evaluations."""
        gaps: list[GapItem] = []

        # Check for missing required sections
        for required_section in policy_def.required_sections:
            if required_section.lower() not in document_text.lower():
                gaps.append(
                    GapItem(
                        area=f"Missing required section: {required_section}",
                        severity="critical",
                        description=(
                            f"Policy definition requires a '{required_section}' section "
                            "but it was not found in the document."
                        ),
                        relevant_legislation=[],
                    )
                )

        # Add gaps from RED criterion results
        for result in criterion_results:
            if result.rating == RAGRating.RED:
                gaps.append(
                    GapItem(
                        area=result.criterion_name,
                        severity="critical" if result.criterion_priority == "high" else "important",
                        description=result.justification,
                        relevant_legislation=result.citations,
                    )
                )

        return gaps

    async def _generate_recommended_actions(
        self,
        criterion_results: list[CriterionResult],
        gap_analysis: list[GapItem],
    ) -> list[Action]:
        """Generate prioritised recommended actions."""
        actions: list[Action] = []

        # Add actions for non-green criterion results
        for result in criterion_results:
            if result.rating != RAGRating.GREEN and result.recommendations:
                for recommendation in result.recommendations:
                    actions.append(
                        Action(
                            priority=(
                                "critical"
                                if result.rating == RAGRating.RED
                                and result.criterion_priority == "high"
                                else "important"
                                if result.rating == RAGRating.RED
                                else "advisory"
                            ),
                            description=recommendation,
                            related_criteria=[result.criterion_name],
                            related_legislation=result.citations,
                        )
                    )

        # Sort by priority
        priority_order = {"critical": 0, "important": 1, "advisory": 2}
        actions.sort(key=lambda a: priority_order.get(a.priority, 3))

        return actions

    def _calculate_overall_rating(self, criterion_results: list[CriterionResult]) -> str:
        """Calculate overall RAG rating from criterion results."""
        if not criterion_results:
            return RAGRating.RED

        # Count ratings
        red_count = sum(1 for r in criterion_results if r.rating == RAGRating.RED)
        amber_count = sum(1 for r in criterion_results if r.rating == RAGRating.AMBER)

        # If any high-priority criterion is RED, overall is RED
        high_priority_red = any(
            r.rating == RAGRating.RED and r.criterion_priority == "high"
            for r in criterion_results
        )

        if high_priority_red or red_count > len(criterion_results) / 3:
            return RAGRating.RED
        elif amber_count > len(criterion_results) / 3 or red_count > 0:
            return RAGRating.AMBER
        else:
            return RAGRating.GREEN

    async def _generate_summary(
        self,
        policy_def: PolicyDefinition,
        overall_rating: str,
        criterion_results: list[CriterionResult],
        gap_analysis: list[GapItem],
    ) -> str:
        """Generate executive summary of review using LLM."""
        # Build summary prompt
        criterion_summary = "\n".join(
            f"- {r.criterion_name}: {r.rating.upper()} - {r.justification}"
            for r in criterion_results
        )

        gap_summary = "\n".join(
            f"- {g.area} ({g.severity}): {g.description}" for g in gap_analysis
        )

        prompt = f"""Provide a concise executive summary (3-4 sentences) of this policy review:

Policy: {policy_def.name}
Overall Rating: {overall_rating.upper()}

Criterion Results:
{criterion_summary}

Key Gaps:
{gap_summary}

Summarise the key findings, main strengths, and critical areas for improvement."""

        model = ModelRouter.get_model_for_orchestration()
        response = await self._client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            metadata={"feature_id": "policy-review", "task": "summary_generation"},
        )

        # Log token usage
        if hasattr(response, "usage"):
            logger.info(
                "summary_generation_tokens",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

        if not response.content:
            return "Summary generation failed"

        content_block = response.content[0]
        if hasattr(content_block, "text"):
            return content_block.text

        return "Summary generation failed"

    async def cancel_review(self, review_id: UUID, tenant_id: UUID) -> None:
        """Cancel an in-progress review."""
        review = await self._get_review(review_id, tenant_id)
        if review.state in (PolicyReviewState.PENDING, PolicyReviewState.PROCESSING):
            review.state = PolicyReviewState.CANCELLED
            await self._session.commit()
            logger.info("policy_review_cancelled", review_id=str(review_id))

    async def get_review(self, review_id: UUID, tenant_id: UUID) -> PolicyReview:
        """Get review by ID (tenant-scoped)."""
        return await self._get_review(review_id, tenant_id)
