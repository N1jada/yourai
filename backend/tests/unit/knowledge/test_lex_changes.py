"""Unit tests for the Lex change detection module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from yourai.knowledge.lex_changes import LexChange, LexChangeDetector
from yourai.knowledge.lex_rest import LexRestClient


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "lex_snapshots"


@pytest.fixture
def detector(data_dir: Path) -> LexChangeDetector:
    return LexChangeDetector(data_dir)


# ---------------------------------------------------------------------------
# Snapshot management
# ---------------------------------------------------------------------------


class TestSnapshots:
    async def test_download_snapshot_creates_file(
        self, detector: LexChangeDetector, data_dir: Path
    ) -> None:
        mock_client = AsyncMock(spec=LexRestClient)
        mock_client.get_stats = AsyncMock(return_value={"legislation": 5000, "amendments": 12000})

        path = await detector.download_snapshot(mock_client)

        assert path.exists()
        assert path.parent == data_dir
        data = json.loads(path.read_text())
        assert data["legislation"] == 5000

    def test_load_snapshot(self, detector: LexChangeDetector, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "test_snapshot.json"
        path.write_text(json.dumps({"legislation": 100}))

        result = detector.load_snapshot(path)
        assert result["legislation"] == 100


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------


class TestDetectChanges:
    def test_no_changes(self, detector: LexChangeDetector) -> None:
        prev = {"legislation": 5000, "amendments": 12000}
        curr = {"legislation": 5000, "amendments": 12000}
        changes = detector.detect_changes(prev, curr)
        assert changes == []

    def test_count_increase(self, detector: LexChangeDetector) -> None:
        prev = {"legislation": 5000}
        curr = {"legislation": 5010}
        changes = detector.detect_changes(prev, curr)
        assert len(changes) == 1
        assert changes[0].change_type == "new"
        assert "10 new item(s)" in changes[0].detail

    def test_count_decrease(self, detector: LexChangeDetector) -> None:
        prev = {"legislation": 5000}
        curr = {"legislation": 4990}
        changes = detector.detect_changes(prev, curr)
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert "10 item(s) removed" in changes[0].detail

    def test_new_collection(self, detector: LexChangeDetector) -> None:
        prev = {"legislation": 5000}
        curr = {"legislation": 5000, "case_law": 3000}
        changes = detector.detect_changes(prev, curr)
        assert len(changes) == 1
        assert changes[0].change_type == "new"
        assert changes[0].collection == "case_law"

    def test_removed_collection(self, detector: LexChangeDetector) -> None:
        prev = {"legislation": 5000, "case_law": 3000}
        curr = {"legislation": 5000}
        changes = detector.detect_changes(prev, curr)
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].collection == "case_law"

    def test_nested_dict_changes(self, detector: LexChangeDetector) -> None:
        prev = {"collections": {"legislation": 5000, "amendments": 12000}}
        curr = {"collections": {"legislation": 5050, "amendments": 12000}}
        changes = detector.detect_changes(prev, curr)
        assert len(changes) == 1
        assert changes[0].collection == "collections.legislation"
        assert changes[0].change_type == "new"

    def test_value_type_change(self, detector: LexChangeDetector) -> None:
        prev = {"version": "1.0"}
        curr = {"version": "2.0"}
        changes = detector.detect_changes(prev, curr)
        assert len(changes) == 1
        assert changes[0].change_type == "amended"

    def test_multiple_changes(self, detector: LexChangeDetector) -> None:
        prev = {"legislation": 5000, "amendments": 12000}
        curr = {"legislation": 5010, "amendments": 11990, "case_law": 3000}
        changes = detector.detect_changes(prev, curr)
        # Should find: legislation +10, amendments -10, case_law new
        assert len(changes) == 3
        types = {c.change_type for c in changes}
        assert "new" in types
        assert "removed" in types


# ---------------------------------------------------------------------------
# Weekly check pipeline
# ---------------------------------------------------------------------------


class TestWeeklyCheck:
    async def test_first_run_returns_empty(self, detector: LexChangeDetector) -> None:
        """First run (no previous snapshot) returns empty list."""
        mock_client = AsyncMock(spec=LexRestClient)
        mock_client.get_stats = AsyncMock(return_value={"legislation": 5000})

        tenant_id = UUID("12345678-1234-1234-1234-123456789abc")
        changes = await detector.run_weekly_check(mock_client, tenant_id)
        assert changes == []

    async def test_second_run_detects_changes(
        self, detector: LexChangeDetector, data_dir: Path
    ) -> None:
        """Second run compares with previous snapshot."""
        # Create a "previous" snapshot manually
        data_dir.mkdir(parents=True, exist_ok=True)
        prev_path = data_dir / "lex_stats_20250101T000000Z.json"
        prev_path.write_text(json.dumps({"legislation": 5000}))

        mock_client = AsyncMock(spec=LexRestClient)
        mock_client.get_stats = AsyncMock(return_value={"legislation": 5010})

        tenant_id = UUID("12345678-1234-1234-1234-123456789abc")
        changes = await detector.run_weekly_check(mock_client, tenant_id)
        assert len(changes) == 1
        assert changes[0].change_type == "new"


# ---------------------------------------------------------------------------
# LexChange dataclass
# ---------------------------------------------------------------------------


class TestLexChange:
    def test_frozen(self) -> None:
        change = LexChange(change_type="new", collection="legislation", detail="test")
        with pytest.raises(AttributeError):
            change.change_type = "amended"  # type: ignore[misc]

    def test_detected_at_auto_set(self) -> None:
        change = LexChange(change_type="new", collection="test", detail="test")
        assert change.detected_at is not None
