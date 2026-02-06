"""Lex API integration exceptions."""

from __future__ import annotations

from yourai.core.exceptions import YourAIError


class LexError(YourAIError):
    """Base exception for Lex API errors."""

    status_code = 502
    code = "lex_error"
    message = "Lex API request failed."


class LexConnectionError(LexError):
    """Lex API connection failed (unreachable, DNS, etc.)."""

    code = "lex_connection_error"
    message = "Could not connect to Lex API."


class LexTimeoutError(LexError):
    """Lex API request timed out."""

    code = "lex_timeout_error"
    message = "Lex API request timed out."


class LexNotFoundError(LexError):
    """Resource not found in Lex API (404)."""

    status_code = 404
    code = "lex_not_found"
    message = "Resource not found in Lex API."
