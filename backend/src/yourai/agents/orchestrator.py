"""Orchestrator agent — Sonnet-class conversation management.

Manages conversation flow, delegates to knowledge workers, assembles system prompts,
and generates streaming responses with inline citations.

Session 2: Delegates knowledge gathering to specialist workers (policy, legislation, caselaw).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from anthropic import AsyncAnthropic

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from yourai.agents.models import Message, Persona
    from yourai.agents.schemas import RouterDecision

from yourai.agents.knowledge_schemas import KnowledgeContext
from yourai.agents.model_routing import ModelRouter
from yourai.agents.prompts.base import BASE_SYSTEM_PROMPT
from yourai.agents.workers.policy import PolicyWorker
from yourai.api.sse.events import ContentDeltaEvent

logger = structlog.get_logger()


class OrchestratorAgent:
    """Sonnet-class agent for conversation management and response generation."""

    def __init__(
        self, anthropic_client: AsyncAnthropic, session: AsyncSession | None = None
    ) -> None:
        self._client = anthropic_client
        self._session = session  # Needed for PolicyWorker

    async def generate_response(
        self,
        query: str,
        conversation_id: UUID,
        tenant_id: UUID,
        conversation_history: list[Message],
        persona: Persona | None = None,
        router_decision: RouterDecision | None = None,
    ) -> AsyncGenerator[ContentDeltaEvent, None]:
        """Generates streaming response using Anthropic API with knowledge retrieval.

        Flow:
        1. Invoke knowledge workers in parallel (based on router decision)
        2. Aggregate knowledge sources into context
        3. Assemble system prompt with knowledge context
        4. Stream response from Claude with inline citations

        Args:
            query: User's current question
            conversation_id: Conversation UUID for logging
            tenant_id: Tenant UUID for logging
            conversation_history: Previous messages in this conversation
            persona: Optional persona to apply (adds system instructions)
            router_decision: Router classification determining which workers to invoke

        Yields:
            ContentDeltaEvent for each text chunk from the streaming response
        """
        # Step 1: Invoke knowledge workers in parallel (Session 2)
        knowledge_context = await self._invoke_knowledge_workers(query, tenant_id, router_decision)

        # Step 2: Assemble system prompt with knowledge context and skills
        system_prompt = self._assemble_system_prompt(
            persona, knowledge_context, router_decision, tenant_id
        )
        messages = self._build_messages(conversation_history, query)
        model = ModelRouter.get_model_for_orchestration()

        logger.info(
            "orchestrator_generating_response",
            conversation_id=str(conversation_id),
            tenant_id=str(tenant_id),
            model=model,
            persona_id=str(persona.id) if persona else None,
            history_count=len(conversation_history),
            sources_found=len(knowledge_context.all_sources) if knowledge_context else 0,
        )

        try:
            async with self._client.messages.stream(
                model=model,
                max_tokens=4000,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
            ) as stream:
                async for text in stream.text_stream:
                    yield ContentDeltaEvent(text=text)

            # Append mandatory disclaimer (Session 4)
            disclaimer = (
                "\n\n---\n\n"
                "*This information is provided for general guidance only and does not "
                "constitute legal advice. For specific legal matters, please consult "
                "qualified legal counsel.*"
            )
            yield ContentDeltaEvent(text=disclaimer)

        except Exception as exc:
            logger.error(
                "orchestrator_generation_failed",
                conversation_id=str(conversation_id),
                tenant_id=str(tenant_id),
                error=str(exc),
                exc_info=True,
            )
            raise

    async def _invoke_knowledge_workers(
        self,
        query: str,
        tenant_id: UUID,
        router_decision: RouterDecision | None,
    ) -> KnowledgeContext:
        """Invoke knowledge workers in parallel based on router decision.

        Args:
            query: User's query
            tenant_id: Tenant ID
            router_decision: Router's classification of required sources

        Returns:
            KnowledgeContext with aggregated sources from all workers
        """
        if router_decision is None:
            return KnowledgeContext()

        sources = router_decision.sources
        tasks = []

        # Policy Worker (internal documents)
        if "internal_policies" in sources and self._session is not None:
            policy_worker = PolicyWorker(self._session)
            tasks.append(policy_worker.search(query, tenant_id, limit=5))

        # Legislation Worker (UK statutes)
        if "uk_legislation" in sources:
            tasks.append(self._search_legislation(query, tenant_id))  # type: ignore[arg-type]

        # Case Law Worker (court judgments)
        if "case_law" in sources:
            tasks.append(self._search_caselaw(query, tenant_id))  # type: ignore[arg-type]

        # Execute workers in parallel
        if not tasks:
            return KnowledgeContext()

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        context = KnowledgeContext()
        for result in results:
            if isinstance(result, Exception):
                logger.warning("knowledge_worker_error", error=str(result))
                continue

            if isinstance(result, list):
                for source in result:
                    # Dispatch to appropriate field based on source_type
                    if hasattr(source, "source_type"):
                        if source.source_type.value == "company_policy":
                            context.policy_sources.append(source)
                        elif source.source_type.value == "uk_legislation":
                            context.legislation_sources.append(source)  # type: ignore[arg-type]
                        elif source.source_type.value == "case_law":
                            context.case_law_sources.append(source)  # type: ignore[arg-type]

        logger.info(
            "knowledge_workers_complete",
            tenant_id=str(tenant_id),
            policy_count=len(context.policy_sources),
            legislation_count=len(context.legislation_sources),
            caselaw_count=len(context.case_law_sources),
        )

        return context

    async def _search_legislation(self, query: str, tenant_id: UUID) -> list[object]:
        """Search legislation via Lex REST API.

        Searches both act-level metadata and section-level text in parallel.
        Sections provide the actual provision text that Claude needs to give
        substantive answers; act-level results provide titles for citation.

        After the initial search, fetches additional sections from the most
        relevant acts so Claude has fuller coverage of each act rather than
        scattered fragments across many acts.
        """
        from yourai.knowledge.lex_health import get_lex_health
        from yourai.knowledge.lex_rest import LexRestClient

        lex = get_lex_health()
        client = LexRestClient(lex.active_url, timeout=30.0)
        try:
            # Search acts (for titles) and sections (for provision text) in parallel
            act_result, sections = await asyncio.gather(
                client.search_legislation(query, limit=5, include_text=True),
                client.search_legislation_sections(query, size=15, include_text=True),
            )

            from yourai.agents.knowledge_schemas import LegislationSource, VerificationStatus

            # Build act title lookup from act-level results
            act_titles: dict[str, str] = {}
            for item in act_result.results:
                act_id = item.get("id", "")
                act_titles[act_id] = item.get("title", "Unknown Act")

            # Group initial sections by parent act to identify top acts
            from collections import Counter

            act_hit_counts = Counter(sec.legislation_id for sec in sections)
            top_acts = [act_id for act_id, _ in act_hit_counts.most_common(3)]

            # Fetch additional sections from top acts for fuller coverage
            seen_section_ids = {sec.id for sec in sections}
            enrich_tasks = []
            for act_id in top_acts:
                enrich_tasks.append(
                    client.search_legislation_sections(
                        query, legislation_id=act_id, size=8, include_text=True
                    )
                )

            extra_sections = []
            if enrich_tasks:
                enrich_results = await asyncio.gather(*enrich_tasks, return_exceptions=True)
                for result in enrich_results:
                    if isinstance(result, list):
                        for sec in result:
                            if sec.id not in seen_section_ids:
                                extra_sections.append(sec)
                                seen_section_ids.add(sec.id)

            all_sections = sections + extra_sections
            sources: list[object] = []

            # Section-level sources (primary — these have the actual provision text)
            for sec in all_sections:
                act_name = act_titles.get(sec.legislation_id, "")
                if not act_name:
                    act_name = (
                        f"{sec.legislation_type.value.upper()} "
                        f"{sec.legislation_year} c.{sec.legislation_number}"
                    )
                sources.append(
                    LegislationSource(
                        act_name=act_name,
                        year=sec.legislation_year,
                        section=str(sec.number) if sec.number is not None else None,
                        content=sec.text or sec.title,
                        uri=sec.uri,
                        score=0.9,
                        is_historical=sec.legislation_year < 1963,
                        verification_status=VerificationStatus.VERIFIED,
                    )
                )

            # Add act-level sources for acts not already covered by sections
            covered_acts = {sec.legislation_id for sec in all_sections}
            for item in act_result.results:
                if item.get("id", "") not in covered_acts:
                    sources.append(
                        LegislationSource(
                            act_name=item.get("title", "Unknown Act"),
                            year=item.get("year"),
                            section=None,
                            content=item.get("text", "") or item.get("description", ""),
                            uri=item.get("uri", ""),
                            score=0.85,
                            is_historical=item.get("year", 2000) < 1963,
                            verification_status=VerificationStatus.VERIFIED,
                        )
                    )

            logger.info(
                "legislation_rest_search_complete",
                tenant_id=str(tenant_id),
                sources_found=len(sources),
                section_sources=len(all_sections),
                enriched_sections=len(extra_sections),
                act_sources=len(act_result.results),
            )
            return sources
        except Exception as exc:
            logger.warning(
                "legislation_rest_search_failed", error=str(exc), tenant_id=str(tenant_id)
            )
            return []
        finally:
            await client.aclose()

    async def _search_caselaw(self, query: str, tenant_id: UUID) -> list[object]:
        """Case law search — Lex does not currently expose case law tools."""
        logger.info(
            "caselaw_search_skipped",
            tenant_id=str(tenant_id),
            msg="Lex instance does not expose case law search tools",
        )
        return []

    def _assemble_system_prompt(
        self,
        persona: Persona | None,
        knowledge_context: KnowledgeContext | None = None,
        router_decision: RouterDecision | None = None,
        tenant_id: UUID | None = None,
    ) -> str:
        """Assembles system prompt from base + persona + skills + knowledge context.

        Args:
            persona: Optional persona with custom system_instructions
            knowledge_context: Retrieved knowledge sources from workers
            router_decision: Router classification (for skills activation)
            tenant_id: Tenant UUID (for tenant-specific skills)

        Returns:
            Complete system prompt string with instructions to cite sources
        """
        prompt = BASE_SYSTEM_PROMPT

        if persona and persona.system_instructions:
            prompt += f"\n\n# Persona Instructions\n\n{persona.system_instructions}"

        # Add skills guidance based on activated sources (Session 4)
        if router_decision and router_decision.sources:
            from yourai.agents.skills import get_skill_registry

            skill_registry = get_skill_registry()
            skills_prompt = skill_registry.assemble_skills_prompt(
                router_decision.sources, tenant_id
            )
            if skills_prompt:
                prompt += skills_prompt

        # Add knowledge context if sources were found (Session 2)
        if knowledge_context and knowledge_context.has_sources:
            prompt += "\n\n" + knowledge_context.format_for_prompt()
            prompt += (
                "\n\n**IMPORTANT**: Use ONLY the sources provided above to answer "
                "the user's question. Cite sources inline using their exact citations. "
                "If the provided sources don't contain enough information, say so clearly."
                "\n\n**NOTE ON LEGISLATION SOURCES**: The legislation sections above are "
                "the most relevant provisions retrieved from the indexed legislation "
                "database. They represent the key provisions matching the user's query, "
                "not the complete text of each Act. Treat these as authoritative extracts "
                "from the current revised versions of UK legislation. Do NOT caveat that "
                "you only have partial access — instead, answer substantively based on "
                "the provisions provided and cite specific section numbers."
            )

        return prompt

    def _build_messages(self, history: list[Message], current_query: str) -> list[dict[str, str]]:
        """Converts Message ORM objects to Anthropic API format.

        Args:
            history: Previous messages in the conversation
            current_query: Current user question to append

        Returns:
            List of message dicts in Anthropic format: [{"role": "user", "content": "..."}]
        """
        messages: list[dict[str, str]] = []

        # Add conversation history (last 20 messages to avoid context overflow)
        for msg in history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})

        # Only append current query if history doesn't already end with a user message
        # (the route creates the user message before invoking the agent, so history
        # typically includes it; appending again would create consecutive user messages
        # which the Anthropic API rejects)
        if not messages or messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": current_query})

        return messages
