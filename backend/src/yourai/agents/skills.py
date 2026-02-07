"""Skills Pattern — Automatic context injection for domain-specific guidance.

Inspired by Lex MCP's skills system. When agents invoke specific tools, relevant
domain-specific context and guidance is automatically injected into the system prompt.

This keeps the base system prompt lean while ensuring the agent receives appropriate
guidance exactly when it needs it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


@dataclass
class Skill:
    """A domain-specific skill that can be injected into agent context."""

    name: str
    description: str
    system_prompt_addition: str
    activated_by_sources: list[str]  # Router sources that activate this skill


# Built-in skills (loaded by default for all tenants)
BUILTIN_SKILLS: list[Skill] = [
    Skill(
        name="Legal Research",
        description="Guidance for UK legislation citation and interpretation",
        system_prompt_addition="""
# Legal Research Skill

You have access to UK legislation through the Lex API. When citing legislation:

## Citation Format
- Use neutral citation format: "Housing Act 1985, s.8(1)"
- Always include the year: "Data Protection Act 2018"
- For sections with subsections: "Companies Act 2006, s.21A(3)"
- For statutory instruments: "SI 2010/490, reg.5"

## Legislative Hierarchy
- **Primary Legislation**: Acts of Parliament (highest authority)
- **Secondary Legislation**: Statutory Instruments (delegated by primary legislation)
- **Amendments**: Always check if a provision has been amended or repealed

## Pre-1963 Legislation
If citing legislation published before 1963, include this disclaimer:
"⚠️ This is digitised historical content and may not reflect current law. Verify against official sources."

## Amendment Status
- Use phrases like "as amended by..." when relevant
- Note if a provision is "in force" or "not yet in force"
- Mention if a provision has been repealed

## Context and Interpretation
- Provide context on what the legislation is trying to achieve
- Explain technical terms in plain language
- Note any relevant case law interpretations (if available)
""",
        activated_by_sources=["uk_legislation"],
    ),
    Skill(
        name="Case Law Analysis",
        description="Guidance for UK case law citation and interpretation",
        system_prompt_addition="""
# Case Law Analysis Skill

You have access to UK court judgments. When citing case law:

## Citation Format
- **Neutral Citation**: [Year] Court Abbreviation Case Number
  - Example: "[2020] EWCA Crim 123"
  - Example: "[2019] UKSC 45"
- **Case Name**: Use "v" not "vs"
  - Example: "R v Smith [2020] EWCA Crim 123"
  - Example: "Jones v Brown [2019] EWHC 567 (QB)"

## Court Hierarchy (binding precedent)
1. **UK Supreme Court** (UKSC) — binds all lower courts
2. **Court of Appeal** (EWCA Civ/Crim) — binds High Court and below
3. **High Court** (EWHC) — persuasive but not binding on other High Court judges
4. **Crown/County/Magistrates** — not binding

## Precedent Weight
- **Binding precedent**: Lower courts must follow higher court decisions on the same legal point
- **Persuasive precedent**: Courts may consider but are not bound by lateral or lower decisions
- **Obiter dicta**: Comments made "by the way" are persuasive but not binding

## Summarising Judgments
- State the legal principle established
- Explain the facts briefly (only if relevant to the principle)
- Note if the decision has been appealed or overturned
- Mention if it's a leading case on the topic
""",
        activated_by_sources=["case_law"],
    ),
    Skill(
        name="Policy Interpretation",
        description="Guidance for interpreting internal policies",
        system_prompt_addition="""
# Policy Interpretation Skill

You have access to the organisation's internal policies. When interpreting policies:

## Interpretation Principles
- Policies are internal documents, not law — they can be changed by the organisation
- Look for defined terms in the policy (usually in a "Definitions" section)
- Consider the policy's stated purpose and objectives
- Apply the specific over the general (specific clauses override general ones)

## Cross-References
- If a policy references legislation, check that legislation is still current
- If a policy references external standards, note the version/date
- If multiple policies conflict, the most recent usually takes precedence

## Practical Application
- Translate policy language into practical steps
- Note any discretionary elements ("may" vs "must")
- Highlight any review/appeal mechanisms

## Disclaimers
- Note if a policy appears outdated (e.g., references repealed legislation)
- Flag any apparent conflicts with current legal requirements
- Suggest policy review if significant gaps or ambiguities are found
""",
        activated_by_sources=["internal_policies"],
    ),
]


class SkillRegistry:
    """Registry for managing and activating skills."""

    def __init__(self) -> None:
        self._builtin_skills = {skill.name: skill for skill in BUILTIN_SKILLS}
        # In future: tenant-specific skills loaded from database
        self._tenant_skills: dict[UUID, dict[str, Skill]] = {}

    def get_skills_for_sources(
        self,
        sources: list[str],
        tenant_id: UUID | None = None,
    ) -> list[Skill]:
        """Get all skills activated by the given sources.

        Args:
            sources: List of source types (e.g., ["uk_legislation", "internal_policies"])
            tenant_id: Optional tenant UUID for tenant-specific skills

        Returns:
            List of Skill objects to inject
        """
        activated_skills = []

        # Check builtin skills
        for skill in self._builtin_skills.values():
            if any(source in skill.activated_by_sources for source in sources):
                activated_skills.append(skill)

        # Check tenant-specific skills (future enhancement)
        if tenant_id and tenant_id in self._tenant_skills:
            for skill in self._tenant_skills[tenant_id].values():
                if any(source in skill.activated_by_sources for source in sources):
                    activated_skills.append(skill)

        return activated_skills

    def assemble_skills_prompt(
        self,
        sources: list[str],
        tenant_id: UUID | None = None,
    ) -> str:
        """Assemble the skills system prompt additions for given sources.

        Args:
            sources: List of source types
            tenant_id: Optional tenant UUID

        Returns:
            Combined skills prompt additions (empty string if no skills activated)
        """
        skills = self.get_skills_for_sources(sources, tenant_id)

        if not skills:
            return ""

        # Build combined prompt
        prompt_parts = ["\n---\n# Domain Skills\n"]
        prompt_parts.append(
            "The following domain-specific guidance applies to this query:\n"
        )

        for skill in skills:
            prompt_parts.append(skill.system_prompt_addition)
            prompt_parts.append("\n")

        return "".join(prompt_parts)


# Global registry instance
_skill_registry = SkillRegistry()


def get_skill_registry() -> SkillRegistry:
    """Get the global skill registry instance."""
    return _skill_registry
