"""Tests for document chunking: section boundaries, token limits, overlap, strategy selection."""

from __future__ import annotations

from yourai.knowledge.chunking import Chunk, chunk_document
from yourai.knowledge.extraction import Section


class TestChunkDocument:
    """Tests for the chunk_document function."""

    def test_empty_text_returns_empty(self):
        result = chunk_document(
            "", sections=None, target_tokens=100, max_tokens=200, overlap_tokens=15
        )
        assert result == []

    def test_short_text_single_chunk(self):
        text = "This is a short document."
        result = chunk_document(
            text, sections=None, target_tokens=100, max_tokens=200, overlap_tokens=15
        )
        assert len(result) == 1
        assert result[0].content == text
        assert result[0].index == 0

    def test_structure_aware_with_sections(self):
        sections = [
            Section(heading="Introduction", content="This is the introduction.", level=1),
            Section(heading="Methods", content="These are the methods.", level=1),
            Section(heading="Results", content="These are the results.", level=1),
        ]
        text = "Introduction\nThis is the introduction.\nMethods\nThese are the methods.\nResults\nThese are the results."
        result = chunk_document(
            text,
            sections=sections,
            target_tokens=100,
            max_tokens=200,
            overlap_tokens=15,
        )
        assert len(result) == 3
        assert "Introduction" in result[0].content
        assert "Methods" in result[1].content
        assert "Results" in result[2].content

    def test_fixed_size_fallback_no_sections(self):
        # Create text long enough to require multiple chunks
        text = "This is a sentence. " * 200  # ~800 tokens
        result = chunk_document(
            text,
            sections=None,
            target_tokens=100,
            max_tokens=200,
            overlap_tokens=15,
        )
        assert len(result) > 1
        # Verify sequential indices
        for i, chunk in enumerate(result):
            assert chunk.index == i

    def test_chunk_indices_are_sequential(self):
        text = "Word " * 500
        result = chunk_document(
            text, sections=None, target_tokens=50, max_tokens=100, overlap_tokens=10
        )
        for i, chunk in enumerate(result):
            assert chunk.index == i

    def test_structure_aware_long_section_splits(self):
        """A section longer than max_tokens should be split at sentence boundaries."""
        long_content = "This is a sentence. " * 200
        sections = [
            Section(heading="Long Section", content=long_content, level=1),
            Section(heading="Short Section", content="Brief content.", level=1),
        ]
        text = f"Long Section\n{long_content}\nShort Section\nBrief content."
        result = chunk_document(
            text,
            sections=sections,
            target_tokens=100,
            max_tokens=200,
            overlap_tokens=15,
        )
        assert len(result) > 2
        # First chunk should include the heading
        assert "Long Section" in result[0].content

    def test_single_section_no_heading_uses_fixed_size(self):
        """A single section without a heading falls back to fixed-size."""
        text = "This is plain text without structure. " * 100
        sections = [Section(heading=None, content=text, level=0)]
        result = chunk_document(
            text,
            sections=sections,
            target_tokens=100,
            max_tokens=200,
            overlap_tokens=15,
        )
        # Should use fixed-size since only one section with no heading
        assert len(result) >= 1

    def test_byte_ranges_set(self):
        text = "Hello world. This is a test. " * 50
        result = chunk_document(
            text, sections=None, target_tokens=50, max_tokens=100, overlap_tokens=10
        )
        for chunk in result:
            assert chunk.byte_range_start is not None
            assert chunk.byte_range_end is not None
            assert chunk.byte_range_end > chunk.byte_range_start

    def test_chunk_is_dataclass(self):
        chunk = Chunk(content="test", index=0, token_count=1)
        assert chunk.content == "test"
        assert chunk.index == 0
        assert chunk.section_heading is None
