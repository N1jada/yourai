"""Policy type identification agent — Haiku-powered classification."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from yourai.policy.models import PolicyDefinition
from yourai.policy.schemas import (
    AlternativeMatch,
    PolicyTypeIdentificationResult,
)

logger = structlog.get_logger()


IDENTIFICATION_SYSTEM_PROMPT = """You are a policy classification agent. Your task is to identify which policy type a document matches from the tenant's policy ontology.

Analyze the document excerpt and match it against the provided policy definitions based on:
1. Document title and subject matter
2. Key themes and topics covered
3. Required sections present
4. Terminology and language used

Respond with JSON only (no markdown, no explanation):
{
  "matched_definition_uri": "health-and-safety-policy" | null,
  "confidence": 0.95,
  "reasoning": "Document discusses risk assessments, incident reporting, and workplace safety procedures, matching the Health & Safety Policy definition.",
  "alternative_matches": [
    {"uri": "fire-safety-policy", "confidence": 0.3, "name": "Fire Safety Policy"}
  ]
}

If no clear match is found (confidence < 0.6), set matched_definition_uri to null and explain why in reasoning."""


class PolicyTypeIdentifier:
    """Haiku-class agent for identifying policy type from uploaded documents."""

    def __init__(self, anthropic_client: AsyncAnthropic) -> None:
        self._client = anthropic_client

    async def identify_policy_type(
        self,
        document_text: str,
        tenant_id: UUID,
        session: AsyncSession,
    ) -> PolicyTypeIdentificationResult:
        """Identify which PolicyDefinition matches the uploaded document.

        Args:
            document_text: Text content of the uploaded policy document
            tenant_id: Tenant UUID
            session: Database session for loading policy definitions

        Returns:
            PolicyTypeIdentificationResult with matched definition and confidence

        Raises:
            Exception: If Anthropic API call fails
        """
        # 1. Load tenant's policy definitions
        from sqlalchemy import select

        db_result = await session.execute(
            select(PolicyDefinition).where(
                PolicyDefinition.tenant_id == tenant_id,
                PolicyDefinition.status == "active",
            )
        )
        definitions = list(db_result.scalars().all())

        if not definitions:
            logger.warning(
                "policy_type_identification_no_definitions",
                tenant_id=str(tenant_id),
            )
            return PolicyTypeIdentificationResult(
                matched_definition_id=None,
                matched_definition_uri=None,
                matched_definition_name=None,
                confidence=0.0,
                reasoning="No policy definitions found for tenant. Please create policy definitions first.",
                alternative_matches=[],
            )

        # 2. Build classification prompt
        prompt = self._build_prompt(definitions, document_text)

        # 3. Call Haiku model
        try:
            from yourai.agents.model_routing import ModelRouter

            model = ModelRouter.get_model_for_routing()  # Haiku

            response = await self._client.messages.create(
                model=model,
                max_tokens=1000,
                system=IDENTIFICATION_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # 4. Parse structured response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text = block.text
                    break

            parsed = json.loads(response_text)

            # 5. Lookup matched definition
            matched_definition = None
            if parsed.get("matched_definition_uri"):
                for defn in definitions:
                    if defn.uri == parsed["matched_definition_uri"]:
                        matched_definition = defn
                        break

            result = PolicyTypeIdentificationResult(
                matched_definition_id=UUID(str(matched_definition.id))
                if matched_definition
                else None,
                matched_definition_uri=matched_definition.uri if matched_definition else None,
                matched_definition_name=matched_definition.name if matched_definition else None,
                confidence=parsed["confidence"],
                reasoning=parsed["reasoning"],
                alternative_matches=[
                    AlternativeMatch(**alt) for alt in parsed.get("alternative_matches", [])
                ],
            )

            logger.info(
                "policy_type_identified",
                tenant_id=str(tenant_id),
                matched_uri=result.matched_definition_uri,
                confidence=result.confidence,
            )

            return result

        except Exception as exc:
            logger.error(
                "policy_type_identification_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            raise

    def _build_prompt(
        self,
        definitions: list[PolicyDefinition],
        document_text: str,
    ) -> str:
        """Build classification prompt with definitions and document excerpt.

        Args:
            definitions: List of policy definitions to match against
            document_text: Document text to classify

        Returns:
            Prompt text
        """
        # Format definitions
        definitions_text = "Tenant's Policy Definitions:\n\n"
        for i, defn in enumerate(definitions, 1):
            definitions_text += f"{i}. {defn.name} [uri: {defn.uri}]\n"
            if defn.description:
                definitions_text += f"   Description: {defn.description}\n"
            if defn.name_variants:
                definitions_text += f"   Name variants: {json.dumps(defn.name_variants)}\n"
            if defn.required_sections:
                definitions_text += f"   Required sections: {json.dumps(defn.required_sections)}\n"
            definitions_text += "\n"

        # Truncate document to first 2000 characters for prompt
        document_excerpt = document_text[:2000]
        if len(document_text) > 2000:
            document_excerpt += "\n\n[... document continues ...]"

        prompt = f"""{definitions_text}

Document to classify (first 2000 characters):

{document_excerpt}

Classify this document against the policy definitions above."""

        return prompt
