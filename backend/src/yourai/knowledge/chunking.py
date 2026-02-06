"""Document chunking: structure-aware and fixed-size strategies.

Structure-aware: splits on section boundaries, targets chunk_target_tokens,
never splits mid-sentence.

Fixed-size: sliding window of chunk_target_tokens with ~15% overlap.
Uses tiktoken (cl100k_base) for token counting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import tiktoken

from yourai.core.config import settings

if TYPE_CHECKING:
    from yourai.knowledge.extraction import Section

_ENCODING = tiktoken.get_encoding("cl100k_base")

# Sentence-ending pattern: period/question/exclamation followed by space or end
_SENTENCE_END = re.compile(r"[.!?]\s+|\n\n+")


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    return len(_ENCODING.encode(text))


@dataclass
class Chunk:
    """A chunk of text ready for embedding."""

    content: str
    index: int
    section_heading: str | None = None
    token_count: int = 0
    byte_range_start: int | None = None
    byte_range_end: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def chunk_document(
    text: str,
    sections: list[Section] | None = None,
    target_tokens: int | None = None,
    max_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[Chunk]:
    """Chunk a document using the best available strategy.

    If sections are provided and non-trivial, uses structure-aware chunking.
    Otherwise falls back to fixed-size sliding window.
    """
    target = target_tokens or settings.chunk_target_tokens
    maximum = max_tokens or settings.chunk_max_tokens
    overlap = overlap_tokens or settings.chunk_overlap_tokens

    # Use structure-aware if we have meaningful sections
    has_sections = sections and len(sections) > 1 and any(s.heading is not None for s in sections)

    if has_sections:
        assert sections is not None
        return _chunk_structure_aware(sections, target, maximum, overlap)
    return _chunk_fixed_size(text, target, maximum, overlap)


def _split_at_sentence_boundary(text: str, max_tokens: int) -> tuple[str, str]:
    """Split text at the last sentence boundary within max_tokens.

    Returns (first_part, remainder). If no sentence boundary found,
    splits at word boundary.
    """
    tokens = _ENCODING.encode(text)
    if len(tokens) <= max_tokens:
        return text, ""

    # Decode to max_tokens position
    truncated = _ENCODING.decode(tokens[:max_tokens])

    # Find the last sentence boundary
    last_boundary = -1
    for match in _SENTENCE_END.finditer(truncated):
        last_boundary = match.end()

    if last_boundary > 0:
        return text[:last_boundary].rstrip(), text[last_boundary:].lstrip()

    # Fall back to word boundary
    space_pos = truncated.rfind(" ")
    if space_pos > 0:
        return text[:space_pos].rstrip(), text[space_pos:].lstrip()

    # No good boundary found — hard split
    return truncated, text[len(truncated) :]


def _chunk_structure_aware(
    sections: list[Section],
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Chunk using section boundaries. Sections longer than max_tokens are
    split at sentence boundaries."""
    chunks: list[Chunk] = []
    chunk_index = 0
    byte_offset = 0

    for section in sections:
        heading = section.heading
        text = section.content.strip()
        if not text and not heading:
            continue

        # Prepend heading to content for context
        full_text = f"{heading}\n{text}" if heading and text else (heading or text)
        full_tokens = _count_tokens(full_text)

        if full_tokens <= max_tokens:
            # Whole section fits in one chunk
            chunk_bytes = len(full_text.encode("utf-8"))
            chunks.append(
                Chunk(
                    content=full_text,
                    index=chunk_index,
                    section_heading=heading,
                    token_count=full_tokens,
                    byte_range_start=byte_offset,
                    byte_range_end=byte_offset + chunk_bytes,
                )
            )
            chunk_index += 1
            byte_offset += chunk_bytes
        else:
            # Section is too large — split at sentence boundaries
            remaining = full_text
            while remaining:
                part, remaining = _split_at_sentence_boundary(remaining, target_tokens)
                if not part:
                    break
                part_tokens = _count_tokens(part)
                part_bytes = len(part.encode("utf-8"))
                chunks.append(
                    Chunk(
                        content=part,
                        index=chunk_index,
                        section_heading=heading,
                        token_count=part_tokens,
                        byte_range_start=byte_offset,
                        byte_range_end=byte_offset + part_bytes,
                    )
                )
                chunk_index += 1
                byte_offset += part_bytes

    return chunks


def _chunk_fixed_size(
    text: str,
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Fixed-size sliding window chunking with overlap."""
    text = text.strip()
    if not text:
        return []

    tokens = _ENCODING.encode(text)
    total_tokens = len(tokens)

    if total_tokens <= max_tokens:
        return [
            Chunk(
                content=text,
                index=0,
                token_count=total_tokens,
                byte_range_start=0,
                byte_range_end=len(text.encode("utf-8")),
            )
        ]

    chunks: list[Chunk] = []
    chunk_index = 0
    start = 0
    byte_offset = 0

    while start < total_tokens:
        end = min(start + target_tokens, total_tokens)
        chunk_text = _ENCODING.decode(tokens[start:end])

        # Try to end at a sentence boundary (unless it's the last chunk)
        if end < total_tokens:
            chunk_text, _ = _split_at_sentence_boundary(
                _ENCODING.decode(tokens[start:end]),
                target_tokens,
            )
            if not chunk_text:
                chunk_text = _ENCODING.decode(tokens[start:end])

        chunk_tokens = _count_tokens(chunk_text)
        chunk_bytes = len(chunk_text.encode("utf-8"))

        chunks.append(
            Chunk(
                content=chunk_text,
                index=chunk_index,
                token_count=chunk_tokens,
                byte_range_start=byte_offset,
                byte_range_end=byte_offset + chunk_bytes,
            )
        )

        chunk_index += 1
        byte_offset += chunk_bytes

        # Advance by (tokens used - overlap)
        advance = max(chunk_tokens - overlap_tokens, 1)
        start += advance

    return chunks
