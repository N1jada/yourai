"""Title Generation Agent — auto-generates conversation titles.

Haiku-class agent that generates concise titles (max 70 chars) from the first
user message in a conversation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from uuid import UUID

    from anthropic import AsyncAnthropic

from yourai.agents.model_routing import ModelRouter

logger = structlog.get_logger()


class TitleGenerationAgent:
    """Haiku-class agent for generating conversation titles."""

    SYSTEM_PROMPT = """You are a title generation assistant.
Generate a concise, descriptive title for a conversation based on
the user's first message.

Rules:
- Maximum 70 characters
- Capitalize appropriately (title case)
- Be specific and descriptive
- No quotes or special formatting
- Focus on the main topic or question

Examples:
- "Housing Act 1985 Landlord Conditions"
- "GDPR Data Subject Access Requests"
- "Employment Tribunal Appeal Process"

Respond with ONLY the title, nothing else."""

    def __init__(self, anthropic_client: AsyncAnthropic) -> None:
        self._client = anthropic_client

    async def generate_title(
        self,
        first_user_message: str,
        conversation_id: UUID,
        tenant_id: UUID,
    ) -> str:
        """Generate a title for the conversation.

        Args:
            first_user_message: The first message from the user
            conversation_id: Conversation UUID
            tenant_id: Tenant UUID

        Returns:
            Generated title (max 70 characters)
        """
        logger.info(
            "title_generation_starting",
            conversation_id=str(conversation_id),
            tenant_id=str(tenant_id),
            message_length=len(first_user_message),
        )

        try:
            model = ModelRouter.get_model_for_routing()  # Haiku for speed

            response = await self._client.messages.create(
                model=model,
                max_tokens=50,  # Short response
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Generate a title for this query:\n\n{first_user_message[:500]}"
                        ),
                    }
                ],
            )

            # Extract title from response
            title = ""
            for block in response.content:
                if hasattr(block, "text"):
                    title = block.text.strip()
                    break

            # Enforce max length
            if len(title) > 70:
                title = title[:67] + "..."

            logger.info(
                "title_generation_complete",
                conversation_id=str(conversation_id),
                tenant_id=str(tenant_id),
                generated_title=title,
            )

            return title

        except Exception as exc:
            logger.error(
                "title_generation_failed",
                conversation_id=str(conversation_id),
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            # Fallback to truncated first message
            fallback = first_user_message[:67].strip()
            if len(first_user_message) > 67:
                fallback += "..."
            return fallback
