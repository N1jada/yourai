"""Regulatory change detection via Lex dataset snapshot comparison.

Compares successive ``/api/stats`` snapshots to detect when legislation
collections have grown (new items) or shrunk (repeals / removals).
Full Parquet-based diffing will be enabled when the self-hosted Lex
instance provides bulk data files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

    from yourai.knowledge.lex_rest import LexRestClient

logger = structlog.get_logger()


@dataclass(frozen=True)
class LexChange:
    """A single detected change in the Lex dataset."""

    change_type: str  # "new" | "amended" | "removed"
    collection: str  # e.g. "legislation", "amendments"
    detail: str  # human-readable description
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class LexChangeDetector:
    """Detect changes in the Lex dataset by comparing stats snapshots.

    Snapshots are persisted as JSON files so they survive process restarts.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log = logger.bind(component="lex_change_detector")

    # ------------------------------------------------------------------
    # Snapshot management
    # ------------------------------------------------------------------

    async def download_snapshot(self, client: LexRestClient) -> Path:
        """Download current ``/api/stats`` and persist to disk.

        Returns the path to the saved snapshot file.
        """
        stats = await client.get_stats()
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = self._data_dir / f"lex_stats_{timestamp}.json"
        path.write_text(json.dumps(stats, indent=2, default=str))
        self._log.info("lex_snapshot_saved", path=str(path))
        return path

    def load_snapshot(self, path: Path) -> dict[str, Any]:
        """Load a previously saved snapshot from disk."""
        data: dict[str, Any] = json.loads(path.read_text())
        return data

    # ------------------------------------------------------------------
    # Change detection
    # ------------------------------------------------------------------

    def detect_changes(
        self,
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> list[LexChange]:
        """Compare two stats snapshots and return detected changes.

        Looks for:
        - New collections (present in current but not previous)
        - Removed collections (present in previous but not current)
        - Count increases (new items added)
        - Count decreases (items removed)
        """
        changes: list[LexChange] = []
        now = datetime.now(UTC)

        prev_collections = set(previous.keys())
        curr_collections = set(current.keys())

        # New collections
        for name in curr_collections - prev_collections:
            changes.append(
                LexChange(
                    change_type="new",
                    collection=name,
                    detail=f"New collection '{name}' appeared with data: {current[name]}",
                    detected_at=now,
                )
            )

        # Removed collections
        for name in prev_collections - curr_collections:
            changes.append(
                LexChange(
                    change_type="removed",
                    collection=name,
                    detail=f"Collection '{name}' no longer present",
                    detected_at=now,
                )
            )

        # Compare shared collections
        for name in prev_collections & curr_collections:
            prev_val = previous[name]
            curr_val = current[name]

            # If the values are numeric counts, compare directly
            if isinstance(prev_val, int | float) and isinstance(curr_val, int | float):
                diff = curr_val - prev_val
                if diff > 0:
                    changes.append(
                        LexChange(
                            change_type="new",
                            collection=name,
                            detail=f"{diff} new item(s) in '{name}' ({prev_val} -> {curr_val})",
                            detected_at=now,
                        )
                    )
                elif diff < 0:
                    changes.append(
                        LexChange(
                            change_type="removed",
                            collection=name,
                            detail=(
                                f"{abs(diff)} item(s) removed from '{name}' "
                                f"({prev_val} -> {curr_val})"
                            ),
                            detected_at=now,
                        )
                    )
            # If the values are dicts, compare recursively for nested counts
            elif isinstance(prev_val, dict) and isinstance(curr_val, dict):
                changes.extend(self._compare_nested(name, prev_val, curr_val, now))
            # Otherwise just flag if they differ
            elif prev_val != curr_val:
                changes.append(
                    LexChange(
                        change_type="amended",
                        collection=name,
                        detail=f"'{name}' changed from {prev_val!r} to {curr_val!r}",
                        detected_at=now,
                    )
                )

        return changes

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    async def run_weekly_check(
        self,
        client: LexRestClient,
        tenant_id: UUID,
    ) -> list[LexChange]:
        """Download a fresh snapshot and compare with the most recent previous one.

        Args:
            client: A :class:`LexRestClient` to fetch stats from.
            tenant_id: The tenant triggering this check (for logging).

        Returns:
            List of detected changes (empty if no previous snapshot exists).
        """
        log = self._log.bind(tenant_id=str(tenant_id))
        current_path = await self.download_snapshot(client)
        current = self.load_snapshot(current_path)

        # Find the most recent previous snapshot
        previous_path = self._find_previous_snapshot(current_path)
        if previous_path is None:
            log.info("lex_weekly_check_first_run", snapshot=str(current_path))
            return []

        previous = self.load_snapshot(previous_path)
        changes = self.detect_changes(previous, current)
        log.info(
            "lex_weekly_check_complete",
            changes_found=len(changes),
            previous=str(previous_path),
            current=str(current_path),
        )
        return changes

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_previous_snapshot(self, exclude: Path) -> Path | None:
        """Find the most recent snapshot file that isn't *exclude*."""
        snapshots = sorted(self._data_dir.glob("lex_stats_*.json"), reverse=True)
        for snap in snapshots:
            if snap != exclude:
                return snap
        return None

    def _compare_nested(
        self,
        parent_key: str,
        prev: dict[str, Any],
        curr: dict[str, Any],
        now: datetime,
    ) -> list[LexChange]:
        """Recursively compare nested dict values for count changes."""
        changes: list[LexChange] = []
        all_keys = set(prev.keys()) | set(curr.keys())

        for key in all_keys:
            full_key = f"{parent_key}.{key}"
            prev_val = prev.get(key)
            curr_val = curr.get(key)

            if prev_val is None and curr_val is not None:
                changes.append(
                    LexChange(
                        change_type="new",
                        collection=full_key,
                        detail=f"New entry '{full_key}' = {curr_val}",
                        detected_at=now,
                    )
                )
            elif prev_val is not None and curr_val is None:
                changes.append(
                    LexChange(
                        change_type="removed",
                        collection=full_key,
                        detail=f"Entry '{full_key}' removed (was {prev_val})",
                        detected_at=now,
                    )
                )
            elif isinstance(prev_val, int | float) and isinstance(curr_val, int | float):
                diff = curr_val - prev_val
                if diff > 0:
                    changes.append(
                        LexChange(
                            change_type="new",
                            collection=full_key,
                            detail=(
                                f"{diff} new item(s) in '{full_key}' ({prev_val} -> {curr_val})"
                            ),
                            detected_at=now,
                        )
                    )
                elif diff < 0:
                    changes.append(
                        LexChange(
                            change_type="removed",
                            collection=full_key,
                            detail=(
                                f"{abs(diff)} item(s) removed from '{full_key}' "
                                f"({prev_val} -> {curr_val})"
                            ),
                            detected_at=now,
                        )
                    )

        return changes
