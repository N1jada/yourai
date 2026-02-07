"""Compliance evaluator — evaluates policy text against specific criteria."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

from yourai.agents.model_routing import ModelRouter
from yourai.knowledge.search import SearchService
from yourai.policy.schemas import Citation, CriterionResult

if TYPE_CHECKING:
    from uuid import UUID

    import anthropic
    from sqlalchemy.ext.asyncio import AsyncSession

    from yourai.knowledge.lex_rest import LexRestClient
    from yourai.policy.schemas import ComplianceCriterion

logger = structlog.get_logger()

# System prompt for criterion evaluation
EVALUATION_SYSTEM_PROMPT = """You are evaluating a UK social housing policy document against \
a specific compliance criterion.

Your task:
1. Review the policy text and legislation/guidance provided
2. Determine if the policy adequately addresses the criterion
3. Assign a RAG rating:
   - GREEN: Policy fully complies with the criterion, addresses all key requirements
   - AMBER: Policy partially complies, has some gaps or unclear language
   - RED: Policy does not comply, significant gaps or missing requirements
4. Provide clear justification citing specific sections
5. List specific recommendations if rating is not GREEN

IMPORTANT:
- Only cite sources from the search results provided (legislation/guidance sections)
- If no relevant legislation was found, state this explicitly
- Use British English
- Distinguish between legal duties ("must"), regulatory expectations ("should"), \
and best practices ("could")
- Be specific: cite section numbers, quote relevant text
- If policy text is vague or ambiguous, this is a gap (AMBER or RED)

Return JSON with this structure:
{
  "rating": "green|amber|red",
  "justification": "Clear 2-3 sentence explanation with specific citations",
  "citations": [
    {
      "source_type": "legislation",
      "act_name": "Fire Safety Act 2021",
      "section": "Section 3",
      "uri": "https://www.legislation.gov.uk/...",
      "excerpt": "Brief relevant excerpt"
    }
  ],
  "recommendations": [
    "Specific improvement if not green"
  ]
}
"""


class ComplianceEvaluator:
    """Evaluates policy text against compliance criteria using LLM + search."""

    def __init__(
        self,
        session: AsyncSession,
        anthropic_client: anthropic.AsyncAnthropic,
        lex_client: LexRestClient,
    ):
        self._session = session
        self._client = anthropic_client
        self._lex_client = lex_client
        self._search_service = SearchService(session)

    async def evaluate_criterion(
        self,
        criterion: ComplianceCriterion,
        policy_text: str,
        tenant_id: UUID,
        tenant_industry: str = "social_housing",
    ) -> CriterionResult:
        """Evaluate policy text against a single compliance criterion.

        Steps:
        1. Search tenant knowledge base for relevant guidance
        2. Search Lex for relevant legislation
        3. Call LLM to evaluate policy against criterion with context
        4. Parse and return structured result
        """
        log = logger.bind(
            tenant_id=str(tenant_id),
            criterion_name=criterion.name,
            criterion_priority=criterion.priority,
        )

        log.info("criterion_evaluation_started")

        # Step 1: Search tenant knowledge base
        kb_results = await self._search_service.hybrid_search(
            query=f"{criterion.name}: {criterion.description}",
            tenant_id=tenant_id,
            limit=5,
        )

        log.info("knowledge_base_search_complete", result_count=len(kb_results))

        # Step 2: Search Lex for legislation (extract key terms from criterion description)
        lex_results = await self._lex_client.search_legislation_sections(
            query=criterion.description,
            size=5,
        )

        log.info("lex_search_complete", result_count=len(lex_results))

        # Step 3: Build evaluation prompt
        legislation_context = self._format_legislation_context(lex_results)
        guidance_context = self._format_guidance_context(kb_results)

        user_prompt = f"""Criterion: {criterion.name}
Priority: {criterion.priority}
Description: {criterion.description}
Compliance type: {criterion.criteria_type}

Relevant legislation (from Lex search):
{legislation_context}

Relevant sector guidance (from knowledge base):
{guidance_context}

Policy document text (relevant sections):
{policy_text[:4000]}

Evaluate the policy against this criterion and return the JSON response."""

        # Step 4: Call Sonnet for evaluation
        model = ModelRouter.get_model_for_orchestration()
        response = await self._client.messages.create(
            model=model,
            max_tokens=2000,
            system=EVALUATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Step 5: Parse response
        if not response.content:
            raise ValueError("Empty response from LLM")

        content_block = response.content[0]
        if not hasattr(content_block, "text"):
            raise ValueError("Response does not contain text")

        result_json = json.loads(content_block.text)

        # Step 6: Build CriterionResult
        citations = [
            Citation(
                source_type=c.get("source_type", "legislation"),
                act_name=c.get("act_name"),
                document_name=c.get("document_name"),
                section=c.get("section"),
                uri=c.get("uri"),
                excerpt=c.get("excerpt"),
                verified=False,  # Will be verified later
            )
            for c in result_json.get("citations", [])
        ]

        result = CriterionResult(
            criterion_name=criterion.name,
            criterion_priority=criterion.priority,
            rating=result_json["rating"],
            justification=result_json["justification"],
            citations=citations,
            recommendations=result_json.get("recommendations", []),
        )

        log.info(
            "criterion_evaluation_complete",
            rating=result.rating,
            citation_count=len(result.citations),
        )

        return result

    def _format_legislation_context(self, lex_results: list) -> str:  # type: ignore[type-arg]
        """Format Lex search results for prompt."""
        if not lex_results:
            return "No relevant legislation found in search."

        lines = []
        for i, result in enumerate(lex_results[:5], 1):
            title = result.legislation_title or "Unknown"
            uri = result.legislation_uri or ""
            excerpt = result.text[:500] if result.text else "No excerpt available"
            lines.append(f"{i}. {title}\n   URI: {uri}\n   Excerpt: {excerpt}\n")

        return "\n".join(lines)

    def _format_guidance_context(self, kb_results: list) -> str:  # type: ignore[type-arg]
        """Format knowledge base search results for prompt."""
        if not kb_results:
            return "No relevant sector guidance found in knowledge base."

        lines = []
        for i, result in enumerate(kb_results[:5], 1):
            doc_name = result.document_name
            content = result.content[:500]
            lines.append(f"{i}. {doc_name}\n   Content: {content}\n")

        return "\n".join(lines)
