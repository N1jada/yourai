"""Model routing logic — determines which Claude model to use for each agent task.

Routes based on task complexity:
- Haiku: Fast classification, routing decisions
- Sonnet: Standard conversation management, analysis
- Opus: Complex synthesis, enterprise-tier features (Session 2+)
"""

from __future__ import annotations

from yourai.core.config import settings


class ModelRouter:
    """Routes agent tasks to appropriate Claude model tier."""

    @staticmethod
    def get_model_for_routing() -> str:
        """Returns Haiku model for fast query classification.

        Used by RouterAgent to determine intent and required knowledge sources.
        """
        return settings.yourai_model_fast

    @staticmethod
    def get_model_for_orchestration() -> str:
        """Returns Sonnet model for conversation management and response generation.

        Used by OrchestratorAgent for main conversation flow.
        """
        return settings.yourai_model_standard

    @staticmethod
    def get_model_for_synthesis() -> str:
        """Returns Opus model for complex synthesis tasks (Enterprise tier).

        Used for advanced features like policy review, complex multi-source synthesis.
        Session 2+ feature.
        """
        return settings.yourai_model_advanced
