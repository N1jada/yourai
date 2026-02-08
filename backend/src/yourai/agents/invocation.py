"""Agent invocation engine — main entry point for AI operations.

Orchestrates the complete agent invocation flow:
1. Router agent classifies the query
2. Orchestrator agent generates the response (streaming)
3. SSE events emitted at each stage
4. Database records created for messages and invocations

Session 2+ will add knowledge worker delegation between steps 1 and 2.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import select

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.agents.confidence import calculate_confidence
from yourai.agents.enums import AgentInvocationMode, MessageRole, MessageState
from yourai.agents.models import AgentInvocation, Conversation, Message, Persona
from yourai.agents.orchestrator import OrchestratorAgent
from yourai.agents.router import RouterAgent
from yourai.agents.schemas import CitationVerificationResultSchema
from yourai.agents.semantic_cache import SemanticCacheService
from yourai.agents.streaming import emit_agent_event
from yourai.agents.title_generation import TitleGenerationAgent
from yourai.api.sse.channels import SSEChannel
from yourai.api.sse.events import (
    AgentCompleteEvent,
    AgentStartEvent,
    ConfidenceUpdateEvent,
    ConversationTitleUpdatedEvent,
    ConversationTitleUpdatingEvent,
    MessageCompleteEvent,
    VerificationResultEvent,
)

logger = structlog.get_logger()


class AgentEngine:
    """Main entry point for AI agent invocations."""

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        anthropic_client: AsyncAnthropic,
        enable_semantic_cache: bool = True,
    ) -> None:
        self._session = session
        self._redis = redis
        self._client = anthropic_client
        self._router = RouterAgent(anthropic_client)
        self._orchestrator = OrchestratorAgent(anthropic_client, session)
        # Semantic cache for response caching (uses embedder internally)
        # Can be disabled in tests to avoid voyageai dependency
        self._semantic_cache: SemanticCacheService | None = None
        if enable_semantic_cache:
            try:
                self._semantic_cache = SemanticCacheService(session)
            except Exception as exc:
                logger.warning(
                    "semantic_cache_init_failed",
                    error=str(exc),
                    msg="Semantic cache disabled - embedder not available",
                )

    async def invoke(
        self,
        message: str,
        conversation_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        persona_id: UUID | None = None,
        attachments: list[dict[str, object]] | None = None,
    ) -> None:
        """Main agent invocation. Emits SSE events during processing.

        Flow:
        1. Create user message in DB
        2. Load conversation history
        3. Load persona (if provided)
        4. Create agent_invocation record
        5. Emit AgentStartEvent (router)
        6. Call router agent
        7. Emit AgentCompleteEvent (router)
        8. Emit AgentStartEvent (orchestrator)
        9. Call orchestrator (streaming)
        10. Emit ContentDeltaEvent for each chunk
        11. Emit AgentCompleteEvent (orchestrator)
        12. Create assistant message in DB
        13. Emit MessageCompleteEvent

        Args:
            message: User's message content
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID
            user_id: User UUID
            persona_id: Optional persona to apply

        Raises:
            Exception: If any stage fails (logged and re-raised)
        """
        channel = SSEChannel.for_conversation(tenant_id, conversation_id)

        try:
            # 1. Load conversation history (user message already created by the route)
            history = await self._load_history(conversation_id, tenant_id)

            # 3. Load persona
            persona = None
            if persona_id:
                # Fetch the ORM object for use in orchestrator
                result = await self._session.execute(
                    select(Persona).where(Persona.id == persona_id, Persona.tenant_id == tenant_id)
                )
                persona = result.scalar_one_or_none()

            # 4. Create invocation record
            invocation = AgentInvocation(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                user_id=user_id,
                mode=AgentInvocationMode.CONVERSATION,
                query=message,
                persona_id=persona_id,
                state="running",
                attachments=attachments or [],
            )
            self._session.add(invocation)
            await self._session.flush()

            # 5-7. Router phase
            await emit_agent_event(
                self._redis,
                channel,
                AgentStartEvent(
                    agent_name="router", task_description="Classifying query intent..."
                ),
            )

            router_start = time.time()
            router_decision = await self._router.classify_query(message, tenant_id, history)
            router_duration = int((time.time() - router_start) * 1000)

            await emit_agent_event(
                self._redis,
                channel,
                AgentCompleteEvent(agent_name="router", duration_ms=router_duration),
            )

            # 8-11. Orchestrator phase
            await emit_agent_event(
                self._redis,
                channel,
                AgentStartEvent(
                    agent_name="orchestrator", task_description="Generating response..."
                ),
            )

            orchestrator_start = time.time()
            assistant_content = ""

            async for delta in self._orchestrator.generate_response(
                message, conversation_id, tenant_id, history, persona, router_decision
            ):
                assistant_content += delta.text
                await emit_agent_event(self._redis, channel, delta)

            orchestrator_duration = int((time.time() - orchestrator_start) * 1000)

            await emit_agent_event(
                self._redis,
                channel,
                AgentCompleteEvent(agent_name="orchestrator", duration_ms=orchestrator_duration),
            )

            # 12. Create assistant message
            assistant_msg = Message(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                state=MessageState.SUCCESS,
            )
            self._session.add(assistant_msg)
            await self._session.flush()

            # 12a. Citation verification phase (Session 3)
            # Gracefully degrade when Lex is unavailable
            verification_result = CitationVerificationResultSchema(
                citations_checked=0,
                citations_verified=0,
                citations_unverified=0,
                citations_removed=0,
                verified_citations=[],
                issues=[],
            )
            try:
                await emit_agent_event(
                    self._redis,
                    channel,
                    AgentStartEvent(
                        agent_name="verification", task_description="Verifying citations..."
                    ),
                )

                verification_start = time.time()

                # Use REST-based verification (faster than MCP for one-shot)
                verification_result = await self._verify_citations_rest(
                    assistant_content, tenant_id
                )

                verification_duration = int((time.time() - verification_start) * 1000)
            except Exception as lex_exc:
                logger.warning(
                    "citation_verification_skipped",
                    tenant_id=str(tenant_id),
                    conversation_id=str(conversation_id),
                    error=str(lex_exc),
                    msg="Lex MCP unavailable — skipping citation verification",
                )
                verification_duration = 0

            # Store verification result in message
            assistant_msg.verification_result = verification_result.model_dump()
            await self._session.flush()

            # Emit verification result event
            await emit_agent_event(
                self._redis,
                channel,
                VerificationResultEvent(
                    citations_checked=verification_result.citations_checked,
                    citations_verified=verification_result.citations_verified,
                    issues=verification_result.issues,
                ),
            )

            await emit_agent_event(
                self._redis,
                channel,
                AgentCompleteEvent(agent_name="verification", duration_ms=verification_duration),
            )

            # 12b. Quality assurance review (Session 4, testing mode)
            try:
                from yourai.agents.qa_agent import QualityAssuranceAgent

                qa_agent = QualityAssuranceAgent()
                qa_result = await qa_agent.review_response(
                    response=assistant_content,
                    confidence_level=None,  # type: ignore[arg-type]  # Scored next
                    verification_result=verification_result.model_dump(),
                    tenant_id=tenant_id,
                )

                logger.info(
                    "qa_review_complete",
                    tenant_id=str(tenant_id),
                    conversation_id=str(conversation_id),
                    approved=qa_result.approved,
                    issues_count=len(qa_result.issues),
                    completeness_score=qa_result.completeness_score,
                    clarity_score=qa_result.clarity_score,
                )
            except Exception as qa_exc:
                logger.warning(
                    "qa_review_skipped",
                    tenant_id=str(tenant_id),
                    error=str(qa_exc),
                )

            # 12c. Confidence scoring (Session 4)
            # Infer whether sources were used based on router decision
            has_sources = len(router_decision.sources) > 0 if router_decision else False
            confidence_level, confidence_reason = calculate_confidence(
                verification_result=verification_result,
                router_decision=router_decision,
                has_knowledge_sources=has_sources,
            )

            assistant_msg.confidence_level = confidence_level
            await self._session.flush()

            await emit_agent_event(
                self._redis,
                channel,
                ConfidenceUpdateEvent(level=confidence_level, reason=confidence_reason),
            )

            # 13. Emit completion
            await emit_agent_event(
                self._redis,
                channel,
                MessageCompleteEvent(message_id=str(assistant_msg.id)),
            )

            # Update invocation state
            invocation.state = "complete"
            from yourai.agents.model_routing import ModelRouter

            invocation.model_used = ModelRouter.get_model_for_orchestration()

            # 14. Title generation for first message (Session 4)
            # Check if conversation needs a title (first exchange)
            # Load fresh conversation object to check title
            conv_result = await self._session.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.tenant_id == tenant_id,
                )
            )
            current_conversation = conv_result.scalar_one()

            if not current_conversation.title and len(history) <= 1:
                await emit_agent_event(
                    self._redis,
                    channel,
                    ConversationTitleUpdatingEvent(conversation_id=str(conversation_id)),
                )

                title_agent = TitleGenerationAgent(self._client)
                generated_title = await title_agent.generate_title(
                    message, conversation_id, tenant_id
                )

                # Update conversation title
                current_conversation.title = generated_title
                await self._session.flush()

                await emit_agent_event(
                    self._redis,
                    channel,
                    ConversationTitleUpdatedEvent(
                        conversation_id=str(conversation_id), title=generated_title
                    ),
                )

            await self._session.commit()

            # 15. Store in semantic cache (Session 4, best-effort)
            # Only cache responses with HIGH confidence
            if self._semantic_cache and confidence_level.value == "high":  # type: ignore[attr-defined]
                try:
                    await self._semantic_cache.store_in_cache(
                        query=message,
                        response=assistant_content,
                        sources=[],  # TODO: extract from router_decision or knowledge workers
                        tenant_id=tenant_id,
                        ttl_seconds=2592000,  # 30 days
                    )
                except Exception as cache_exc:
                    # Log but don't fail the request
                    logger.warning(
                        "semantic_cache_store_failed",
                        tenant_id=str(tenant_id),
                        error=str(cache_exc),
                    )

            logger.info(
                "agent_invocation_complete",
                invocation_id=str(invocation.id),
                tenant_id=str(tenant_id),
                conversation_id=str(conversation_id),
                user_id=str(user_id),
                router_ms=router_duration,
                orchestrator_ms=orchestrator_duration,
                verification_ms=verification_duration,
                citations_checked=verification_result.citations_checked,
                citations_verified=verification_result.citations_verified,
            )

        except Exception as exc:
            logger.error(
                "agent_invocation_failed",
                tenant_id=str(tenant_id),
                conversation_id=str(conversation_id),
                error=str(exc),
                exc_info=True,
            )
            # Rollback on error
            await self._session.rollback()
            raise

    async def cancel(self, invocation_id: UUID, tenant_id: UUID) -> None:
        """Cancel a running invocation."""
        result = await self._session.execute(
            select(AgentInvocation).where(
                AgentInvocation.id == invocation_id,
                AgentInvocation.tenant_id == tenant_id,
                AgentInvocation.state == "running",
            )
        )
        invocation = result.scalar_one_or_none()
        if invocation is None:
            from yourai.core.exceptions import NotFoundError

            raise NotFoundError("Running invocation not found.")

        invocation.state = "cancelled"
        self._session.add(invocation)
        await self._session.flush()

        if invocation.conversation_id:
            channel = SSEChannel.for_conversation(tenant_id, invocation.conversation_id)
            from yourai.api.sse.events import ConversationCancelledEvent

            await emit_agent_event(
                self._redis,
                channel,
                ConversationCancelledEvent(conversation_id=str(invocation.conversation_id)),
            )

        logger.info(
            "invocation_cancelled",
            invocation_id=str(invocation_id),
            tenant_id=str(tenant_id),
        )

    async def _verify_citations_rest(
        self, response_text: str, tenant_id: UUID
    ) -> CitationVerificationResultSchema:
        """Verify citations using Lex REST API (faster than MCP).

        Extracts citations from the response, then checks each legislation
        citation against the Lex REST search endpoint.
        """
        from yourai.agents.schemas import VerifiedCitationSchema
        from yourai.agents.verification import CitationExtractor
        from yourai.api.sse.enums import VerificationStatus
        from yourai.knowledge.lex_health import get_lex_health
        from yourai.knowledge.lex_rest import LexRestClient

        extracted = CitationExtractor.extract_all(response_text)
        if not extracted:
            return CitationVerificationResultSchema(
                citations_checked=0, citations_verified=0, citations_unverified=0,
                citations_removed=0, verified_citations=[], issues=[],
            )

        lex = get_lex_health()
        client = LexRestClient(lex.active_url, timeout=15.0)
        verified_citations: list[VerifiedCitationSchema] = []
        issues: list[str] = []

        # Deduplicate by act_name to avoid repeated API calls for the same Act
        act_name_cache: dict[str, bool] = {}

        try:
            for citation in extracted:
                if citation.citation_type == "legislation" and citation.act_name:
                    act_key = citation.act_name.lower().strip()

                    # Check cache first
                    if act_key in act_name_cache:
                        found = act_name_cache[act_key]
                    else:
                        try:
                            result = await client.search_legislation(
                                citation.act_name, limit=1, include_text=False
                            )
                            found = result.total > 0
                        except Exception as exc:
                            logger.warning(
                                "citation_verification_error",
                                citation=citation.text,
                                error=str(exc),
                            )
                            found = False
                            issues.append(f"{citation.text}: {exc}")
                        act_name_cache[act_key] = found

                    if found:
                        verified_citations.append(VerifiedCitationSchema(
                            citation_text=citation.text,
                            citation_type="legislation",
                            verification_status=VerificationStatus.VERIFIED.value,
                            confidence_score=1.0,
                        ))
                    else:
                        verified_citations.append(VerifiedCitationSchema(
                            citation_text=citation.text,
                            citation_type="legislation",
                            verification_status=VerificationStatus.UNVERIFIED.value,
                            confidence_score=0.0,
                            error_message="Legislation not found in Lex database",
                        ))
                        if f"{citation.text}: not found" not in str(issues):
                            issues.append(f"{citation.text}: not found in Lex database")
                else:
                    # Non-legislation citations (case law, policy) — skip
                    verified_citations.append(VerifiedCitationSchema(
                        citation_text=citation.text,
                        citation_type=citation.citation_type,
                        verification_status=VerificationStatus.UNVERIFIED.value,
                        confidence_score=0.0,
                        error_message=f"{citation.citation_type} verification not available",
                    ))
        finally:
            await client.aclose()

        checked = len(verified_citations)
        verified_count = sum(
            1 for v in verified_citations if v.verification_status == VerificationStatus.VERIFIED.value
        )

        return CitationVerificationResultSchema(
            citations_checked=checked,
            citations_verified=verified_count,
            citations_unverified=checked - verified_count,
            citations_removed=0,
            verified_citations=verified_citations,
            issues=issues,
        )

    async def _load_history(self, conversation_id: UUID, tenant_id: UUID) -> list[Message]:
        """Loads recent conversation history (last 20 messages).

        Args:
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID

        Returns:
            List of Message ORM objects, ordered by created_at ascending
        """
        result = await self._session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.tenant_id == tenant_id,
            )
            .order_by(Message.created_at.asc())
            .limit(20)
        )
        return list(result.scalars().all())
