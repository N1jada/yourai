"""Contextual prefix generation using Anthropic Haiku.

For each chunk, calls Haiku with the full document context (truncated to 50k chars)
to generate a short contextual prefix that situates the chunk within the document.
Uses a semaphore to limit concurrent API calls.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import anthropic
import structlog

from yourai.core.config import settings

if TYPE_CHECKING:
    from yourai.knowledge.chunking import Chunk

logger = structlog.get_logger()

_MAX_DOC_CONTEXT_CHARS = 50_000
_MAX_CONCURRENT = 10

_SYSTEM_PROMPT = (
    "You are a document contextualiser. Given a full document and a specific chunk, "
    "write a brief (1-2 sentence) contextual prefix that situates the chunk within "
    "the broader document. The prefix should help a reader understand what part of "
    "the document this chunk comes from and its relevance. Be concise and factual."
)


async def contextualise_chunks(
    chunks: list[Chunk],
    full_text: str,
    tenant_id: str,
) -> list[str | None]:
    """Generate contextual prefixes for each chunk.

    Returns a list of prefix strings (or None on failure) in the same order as chunks.
    """
    truncated_text = full_text[:_MAX_DOC_CONTEXT_CHARS]
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _contextualise_one(chunk: Chunk) -> str | None:
        async with semaphore:
            try:
                user_msg = (
                    f"<document>\n{truncated_text}\n</document>\n\n"
                    f"<chunk>\n{chunk.content}\n</chunk>\n\n"
                    "Write a brief contextual prefix for this chunk."
                )
                response = await client.messages.create(
                    model=settings.yourai_model_fast,
                    max_tokens=150,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_msg}],
                )
                block = response.content[0] if response.content else None
                text = block.text if block and hasattr(block, "text") else None
                return text
            except Exception:
                logger.warning(
                    "contextualise_chunk_failed",
                    tenant_id=tenant_id,
                    chunk_index=chunk.index,
                    exc_info=True,
                )
                return None

    results = await asyncio.gather(*[_contextualise_one(c) for c in chunks])
    return list(results)
