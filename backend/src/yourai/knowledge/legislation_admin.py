"""Admin service for Lex legislation management — health, search, and detail lookups.

Wraps :class:`LexHealthManager` and :class:`LexRestClient` to provide
a single interface for the legislation admin routes.  All data lives in
Lex's own Qdrant — no YourAI database tables are touched.
"""

from __future__ import annotations

from typing import Any

import structlog

from yourai.knowledge.exceptions import LexConnectionError, LexError, LexTimeoutError
from yourai.knowledge.lex_health import LexHealthManager, get_lex_health

logger = structlog.get_logger()


class LegislationAdminService:
    """Read-only admin proxy to the Lex legislation API."""

    def __init__(self, health_manager: LexHealthManager | None = None) -> None:
        self._health = health_manager or get_lex_health()

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    async def get_overview(self) -> dict[str, Any]:
        """Return combined health status and dataset statistics.

        Returns a dict with keys: status, active_url, primary_url,
        fallback_url, is_using_fallback, stats (or None if unreachable).
        """
        overview: dict[str, Any] = {
            "status": self._health.status,
            "active_url": self._health.active_url,
            "primary_url": self._health._primary_url,
            "fallback_url": self._health._fallback_url,
            "is_using_fallback": self._health.is_using_fallback,
            "stats": None,
        }

        client = self._health.get_rest_client(timeout=10.0)
        try:
            overview["stats"] = await client.get_stats()
        except (LexConnectionError, LexTimeoutError, LexError) as exc:
            logger.warning("legislation_admin_stats_failed", error=str(exc))
        finally:
            await client.aclose()

        return overview

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        *,
        query: str,
        year_from: int | None = None,
        year_to: int | None = None,
        legislation_type: list[str] | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Forward a legislation search to the active Lex endpoint."""
        client = self._health.get_rest_client()
        try:
            result = await client.search_legislation(
                query,
                year_from=year_from,
                year_to=year_to,
                legislation_type=legislation_type,
                offset=offset,
                limit=limit,
                include_text=False,
            )
            return result.model_dump()
        finally:
            await client.aclose()

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    async def get_detail(
        self,
        legislation_type: str,
        year: int,
        number: int,
    ) -> dict[str, Any]:
        """Lookup a single piece of legislation with its sections and amendments."""
        client = self._health.get_rest_client()
        try:
            legislation = await client.lookup_legislation(legislation_type, year, number)

            sections = await client.get_legislation_sections(legislation.id, limit=200)

            amendments: list[dict[str, Any]] = []
            try:
                raw = await client.search_amendments(legislation.id)
                amendments = [a.model_dump() for a in raw]
            except LexError:
                pass  # Amendments are optional — don't fail the whole request

            return {
                "legislation": legislation.model_dump(),
                "sections": [s.model_dump() for s in sections],
                "amendments": amendments,
            }
        finally:
            await client.aclose()

    # ------------------------------------------------------------------
    # Health management
    # ------------------------------------------------------------------

    async def check_health(self) -> dict[str, Any]:
        """Trigger a primary health check and return the result."""
        primary_healthy = await self._health.check_health()
        return {
            "primary_healthy": primary_healthy,
            "status": self._health.status,
            "active_url": self._health.active_url,
        }

    def force_primary(self) -> dict[str, Any]:
        """Reset failover to use the primary endpoint."""
        self._health.force_primary()
        return {
            "status": self._health.status,
            "active_url": self._health.active_url,
        }
