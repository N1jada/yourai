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
from yourai.agents.messages import MessageService
from yourai.agents.models import AgentInvocation, Conversation, Message, Persona
from yourai.agents.orchestrator import OrchestratorAgent
from yourai.agents.router import RouterAgent
from yourai.agents.semantic_cache import SemanticCacheService
from yourai.agents.streaming import emit_agent_event
from yourai.agents.title_generation import TitleGenerationAgent
from yourai.agents.verification import CitationVerificationAgent
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
from yourai.core.config import settings

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
            # 1. Create user message
            msg_service = MessageService(self._session)
            await msg_service.create_message(
                conversation_id,
                tenant_id,
                # We create the message via service, but SendMessage schema expects content
                # For now, we'll create the Message ORM directly to avoid circular import
                type("SendMessage", (), {"content": message, "attachments": None})(),
            )

            # 2. Load conversation history
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
            await emit_agent_event(
                self._redis,
                channel,
                AgentStartEvent(
                    agent_name="verification", task_description="Verifying citations..."
                ),
            )

            verification_start = time.time()
            verification_agent = CitationVerificationAgent(settings.lex_base_url + "/mcp")

            try:
                await verification_agent.connect()
                verification_result = await verification_agent.verify_response(
                    assistant_content, tenant_id
                )
            finally:
                await verification_agent.disconnect()

            verification_duration = int((time.time() - verification_start) * 1000)

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
            from yourai.agents.qa_agent import QualityAssuranceAgent

            qa_agent = QualityAssuranceAgent()
            qa_result = await qa_agent.review_response(
                response=assistant_content,
                confidence_level=None,  # type: ignore[arg-type]  # Scored next
                verification_result=verification_result.model_dump(),
                tenant_id=tenant_id,
            )

            # In testing mode, QA always approves but logs findings
            logger.info(
                "qa_review_complete",
                tenant_id=str(tenant_id),
                conversation_id=str(conversation_id),
                approved=qa_result.approved,
                issues_count=len(qa_result.issues),
                completeness_score=qa_result.completeness_score,
                clarity_score=qa_result.clarity_score,
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
