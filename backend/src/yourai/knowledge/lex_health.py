"""Health check and automatic failover between primary and fallback Lex endpoints."""

from __future__ import annotations

import structlog

from yourai.knowledge.exceptions import LexConnectionError, LexTimeoutError
from yourai.knowledge.lex_mcp import LexMcpClient
from yourai.knowledge.lex_rest import LexRestClient

logger = structlog.get_logger()


class LexHealthManager:
    """Manages Lex endpoint selection with automatic failover.

    After ``max_failures`` consecutive health-check failures on the primary
    endpoint the manager switches to the fallback.  A successful
    ``check_health()`` against the primary resets the counter and switches
    back.
    """

    def __init__(
        self,
        primary_url: str,
        fallback_url: str,
        *,
        max_failures: int = 3,
    ) -> None:
        self._primary_url = primary_url.rstrip("/")
        self._fallback_url = fallback_url.rstrip("/")
        self._max_failures = max_failures
        self._consecutive_failures: int = 0
        self._using_fallback: bool = False
        self._log = logger.bind(
            lex_primary=self._primary_url,
            lex_fallback=self._fallback_url,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_url(self) -> str:
        """Return the URL currently in use."""
        return self._fallback_url if self._using_fallback else self._primary_url

    @property
    def is_using_fallback(self) -> bool:
        return self._using_fallback

    @property
    def status(self) -> str:
        """Return ``'connected'``, ``'fallback'``, or ``'error'``."""
        if not self._using_fallback:
            return "connected"
        # If fallback is active, try to assume it's reachable (health check
        # will update this). We report "fallback" rather than "error" because
        # the system is still operational via the fallback.
        return "fallback"

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def check_health(self) -> bool:
        """Ping the **primary** endpoint's ``/healthcheck``.

        * On success with data: reset failure counter and switch back to primary.
        * On success but no data (0 collections): treat as failure → use fallback.
        * On failure: increment counter; switch to fallback if threshold met.

        Returns ``True`` if the primary is healthy **and has data**.
        """
        client = LexRestClient(self._primary_url, timeout=10.0)
        try:
            result = await client.health_check()

            # Check if the instance actually has ingested data
            collections = result.get("collections", 0)
            if collections == 0:
                self._log.warning(
                    "lex_health_no_data",
                    msg="Primary Lex instance healthy but has 0 collections — using fallback",
                )
                self._using_fallback = True
                return False

            # Primary is back / still healthy with data
            if self._using_fallback:
                self._log.info("lex_health_primary_recovered")
            self._consecutive_failures = 0
            self._using_fallback = False
            return True
        except (LexConnectionError, LexTimeoutError, Exception) as exc:
            self._consecutive_failures += 1
            self._log.warning(
                "lex_health_check_failed",
                failures=self._consecutive_failures,
                error=str(exc),
            )
            if self._consecutive_failures >= self._max_failures and not self._using_fallback:
                self._using_fallback = True
                self._log.warning("lex_health_failover_activated")
            return False
        finally:
            await client.aclose()

    # ------------------------------------------------------------------
    # Client factories
    # ------------------------------------------------------------------

    def get_rest_client(self, *, timeout: float = 30.0) -> LexRestClient:
        """Return a :class:`LexRestClient` pointed at the active endpoint."""
        return LexRestClient(self.active_url, timeout=timeout)

    def get_mcp_client(self) -> LexMcpClient:
        """Return a :class:`LexMcpClient` pointed at the active endpoint's ``/mcp``."""
        return LexMcpClient(f"{self.active_url}/mcp")

    # ------------------------------------------------------------------
    # Manual overrides
    # ------------------------------------------------------------------

    def force_primary(self) -> None:
        """Reset to primary endpoint (e.g. after manual recovery)."""
        self._using_fallback = False
        self._consecutive_failures = 0
        self._log.info("lex_health_forced_primary")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_lex_health: LexHealthManager | None = None


def get_lex_health() -> LexHealthManager:
    """Return the shared :class:`LexHealthManager` singleton.

    Lazily created from ``settings.lex_base_url`` / ``settings.lex_public_fallback_url``.
    """
    global _lex_health  # noqa: PLW0603
    if _lex_health is None:
        from yourai.core.config import settings

        _lex_health = LexHealthManager(
            primary_url=settings.lex_base_url,
            fallback_url=settings.lex_public_fallback_url,
        )
    return _lex_health
