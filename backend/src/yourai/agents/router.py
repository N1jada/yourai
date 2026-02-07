"""Router agent — Haiku-class query classification.

Analyses user queries to determine intent, required knowledge sources, and complexity.
This routing decision informs the orchestrator about which knowledge workers to engage.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic

if TYPE_CHECKING:
    from yourai.agents.models import Message

from yourai.agents.model_routing import ModelRouter
from yourai.agents.prompts.router import ROUTER_SYSTEM_PROMPT
from yourai.agents.schemas import RouterDecision

logger = structlog.get_logger()


class RouterAgent:
    """Haiku-class agent for query classification and routing."""

    def __init__(self, anthropic_client: AsyncAnthropic) -> None:
        self._client = anthropic_client

    async def classify_query(
        self,
        query: str,
        tenant_id: UUID,
        conversation_history: list[Message] | None = None,
    ) -> RouterDecision:
        """Classifies query intent and determines routing strategy.

        Args:
            query: User's current question
            tenant_id: Tenant ID for logging
            conversation_history: Optional previous messages for context

        Returns:
            RouterDecision with intent, sources, complexity, and reasoning

        Raises:
            Exception: If Anthropic API call fails or response is invalid
        """
        model = ModelRouter.get_model_for_routing()

        # For Session 1, we don't pass conversation history to keep it simple.
        # Session 2+ will use history to better classify follow-up questions.
        messages: list[dict[str, str]] = [{"role": "user", "content": query}]

        logger.info(
            "router_agent_classifying",
            tenant_id=str(tenant_id),
            model=model,
            query_preview=query[:100],
        )

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=500,
                system=ROUTER_SYSTEM_PROMPT,
                messages=messages,  # type: ignore[arg-type]
            )

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Parse JSON response
            classification = json.loads(response_text)

            decision = RouterDecision(
                intent=classification["intent"],
                sources=classification["sources"],
                complexity=classification["complexity"],
                reasoning=classification["reasoning"],
            )

            logger.info(
                "router_agent_classified",
                tenant_id=str(tenant_id),
                intent=decision.intent,
                sources=decision.sources,
                complexity=decision.complexity,
            )

            return decision

        except json.JSONDecodeError as exc:
            logger.error(
                "router_agent_json_parse_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                response_text=response_text[:200],
            )
            # Fallback to safe default
            return RouterDecision(
                intent="general_compliance",
                sources=["internal_policies", "uk_legislation"],
                complexity="moderate",
                reasoning="Failed to parse router response, using safe default",
            )

        except Exception as exc:
            logger.error(
                "router_agent_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            raise
