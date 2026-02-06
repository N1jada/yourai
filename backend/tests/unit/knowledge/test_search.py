"""Tests for RRF fusion scoring, disjoint/overlapping merges, empty inputs."""

from __future__ import annotations

from uuid import UUID

from yourai.knowledge.schemas import KeywordResult, VectorResult
from yourai.knowledge.search import rrf_fusion


def _uuid(n: int) -> UUID:
    """Generate a deterministic UUID from an integer."""
    return UUID(int=n)


class TestRRFFusion:
    """Tests for the rrf_fusion function."""

    def test_empty_inputs(self):
        result = rrf_fusion([], [])
        assert result == []

    def test_vector_only(self):
        vector_results = [
            VectorResult(chunk_id=_uuid(1), document_id=_uuid(10), score=0.9, content="a"),
            VectorResult(chunk_id=_uuid(2), document_id=_uuid(10), score=0.8, content="b"),
        ]
        result = rrf_fusion(vector_results, [])
        assert len(result) == 2
        # First should have higher score
        assert result[0][0] == _uuid(1)
        assert result[0][1] > result[1][1]

    def test_keyword_only(self):
        keyword_results = [
            KeywordResult(chunk_id=_uuid(1), document_id=_uuid(10), score=0.9, content="a"),
            KeywordResult(chunk_id=_uuid(2), document_id=_uuid(10), score=0.8, content="b"),
        ]
        result = rrf_fusion([], keyword_results)
        assert len(result) == 2
        assert result[0][0] == _uuid(1)

    def test_overlapping_results_boosted(self):
        """Chunks appearing in both sets should have higher scores."""
        shared_id = _uuid(1)
        unique_vector = _uuid(2)
        unique_keyword = _uuid(3)

        vector_results = [
            VectorResult(chunk_id=shared_id, document_id=_uuid(10), score=0.9, content="a"),
            VectorResult(chunk_id=unique_vector, document_id=_uuid(10), score=0.8, content="b"),
        ]
        keyword_results = [
            KeywordResult(chunk_id=shared_id, document_id=_uuid(10), score=0.9, content="a"),
            KeywordResult(chunk_id=unique_keyword, document_id=_uuid(10), score=0.8, content="c"),
        ]

        result = rrf_fusion(vector_results, keyword_results)
        scores = dict(result)

        # Shared chunk should have higher score than either unique chunk
        assert scores[shared_id] > scores[unique_vector]
        assert scores[shared_id] > scores[unique_keyword]

    def test_disjoint_results_merged(self):
        """Completely disjoint results should all appear in output."""
        vector_results = [
            VectorResult(chunk_id=_uuid(1), document_id=_uuid(10), score=0.9, content="a"),
        ]
        keyword_results = [
            KeywordResult(chunk_id=_uuid(2), document_id=_uuid(10), score=0.9, content="b"),
        ]

        result = rrf_fusion(vector_results, keyword_results)
        assert len(result) == 2
        chunk_ids = {r[0] for r in result}
        assert _uuid(1) in chunk_ids
        assert _uuid(2) in chunk_ids

    def test_rrf_k_parameter(self):
        """Different k values should produce different scores."""
        vector_results = [
            VectorResult(chunk_id=_uuid(1), document_id=_uuid(10), score=0.9, content="a"),
        ]
        result_k30 = rrf_fusion(vector_results, [], k=30)
        result_k60 = rrf_fusion(vector_results, [], k=60)

        # With k=30, rank 1 score = 1/(30+1); with k=60, score = 1/(60+1)
        assert result_k30[0][1] > result_k60[0][1]

    def test_ordering_is_by_score_descending(self):
        vector_results = [
            VectorResult(chunk_id=_uuid(i), document_id=_uuid(10), score=0.9, content=f"chunk {i}")
            for i in range(1, 6)
        ]
        keyword_results = [
            KeywordResult(chunk_id=_uuid(i), document_id=_uuid(10), score=0.9, content=f"chunk {i}")
            for i in range(3, 8)
        ]

        result = rrf_fusion(vector_results, keyword_results)
        scores = [s for _, s in result]
        assert scores == sorted(scores, reverse=True)
