"""Lightweight client for querying the self-hosted Lex Qdrant instance.

Queries the Qdrant REST API directly (not via qdrant-client) for collection
stats and health.  Used by the legislation admin service to show self-hosted
instance status in the admin UI.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

# Known Lex collections (from infrastructure/lex settings)
LEX_COLLECTIONS = [
    "legislation",
    "legislation_section",
    "caselaw",
    "caselaw_section",
    "caselaw_summary",
    "explanatory_note",
    "amendment",
]


class CollectionInfo(BaseModel):
    """Summary info for a Qdrant collection."""

    name: str
    points_count: int = 0
    status: str = "unknown"


class CollectionDetail(BaseModel):
    """Detailed stats for a single Qdrant collection."""

    name: str
    points_count: int = 0
    vectors_count: int = 0
    indexed_vectors_count: int = 0
    status: str = "unknown"
    disk_data_size: int = 0
    ram_data_size: int = 0


class LexQdrantStatusClient:
    """Async client for Lex's Qdrant REST API."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    async def is_healthy(self) -> bool:
        """Check if the Qdrant instance is reachable."""
        try:
            resp = await self._client.get("/healthz")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_collections(self) -> list[CollectionInfo]:
        """List all collections with point counts."""
        try:
            resp = await self._client.get("/collections")
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("lex_qdrant_list_collections_failed", error=str(exc))
            raise

        collections: list[CollectionInfo] = []
        for col in data.get("result", {}).get("collections", []):
            name = col.get("name", "")
            # Fetch point count per collection
            try:
                detail = await self.get_collection_detail(name)
                collections.append(
                    CollectionInfo(
                        name=name,
                        points_count=detail.points_count,
                        status=detail.status,
                    )
                )
            except httpx.HTTPError:
                collections.append(CollectionInfo(name=name))

        return collections

    async def get_collection_detail(self, name: str) -> CollectionDetail:
        """Get detailed stats for a single collection."""
        try:
            resp = await self._client.get(f"/collections/{name}")
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("lex_qdrant_collection_detail_failed", collection=name, error=str(exc))
            raise

        result: dict[str, Any] = data.get("result", {})
        config = result.get("config", {})
        optimizer_status = result.get("optimizer_status", {})
        status_str = optimizer_status.get("status", result.get("status", "unknown"))

        return CollectionDetail(
            name=name,
            points_count=result.get("points_count", 0),
            vectors_count=result.get("vectors_count", 0),
            indexed_vectors_count=result.get("indexed_vectors_count", 0),
            status=str(status_str),
            disk_data_size=config.get("disk_data_size", 0),
            ram_data_size=config.get("ram_data_size", 0),
        )

    async def scroll_legislation(
        self,
        collection: str = "legislation",
        type_filter: str | None = None,
        year_filter: int | None = None,
        limit: int = 20,
        offset_id: str | None = None,
    ) -> dict[str, Any]:
        """Scroll through legislation points with optional filters.

        Returns ``{"items": [...], "next_offset": "..." | None}``.
        """
        must: list[dict[str, Any]] = []
        if type_filter:
            must.append({"key": "type", "match": {"value": type_filter}})
        if year_filter is not None:
            must.append({"key": "year", "match": {"value": year_filter}})

        body: dict[str, Any] = {
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        }
        if must:
            body["filter"] = {"must": must}
        if offset_id:
            body["offset"] = offset_id

        resp = await self._client.post(f"/collections/{collection}/points/scroll", json=body)
        resp.raise_for_status()
        data = resp.json().get("result", {})

        points = data.get("points", [])
        next_offset = data.get("next_page_offset")

        items = []
        for pt in points:
            payload = pt.get("payload", {})
            items.append(
                {
                    "qdrant_point_id": str(pt.get("id", "")),
                    **payload,
                }
            )

        return {"items": items, "next_offset": str(next_offset) if next_offset else None}

    async def count_by_filter(
        self,
        collection: str,
        filter_conditions: list[dict[str, Any]],
    ) -> int:
        """Count points matching the given filter conditions."""
        body: dict[str, Any] = {"exact": True}
        if filter_conditions:
            body["filter"] = {"must": filter_conditions}

        resp = await self._client.post(f"/collections/{collection}/points/count", json=body)
        resp.raise_for_status()
        return int(resp.json().get("result", {}).get("count", 0))

    async def delete_by_filter(
        self,
        collection: str,
        filter_conditions: list[dict[str, Any]],
    ) -> bool:
        """Delete points matching the given filter conditions.

        Returns True on success.
        """
        body: dict[str, Any] = {
            "filter": {"must": filter_conditions},
        }

        resp = await self._client.post(f"/collections/{collection}/points/delete", json=body)
        resp.raise_for_status()
        return True

    async def count_sections_for_legislation(
        self,
        legislation_id: str,
        collection: str = "legislation_section",
    ) -> int:
        """Count sections for a specific legislation item."""
        return await self.count_by_filter(
            collection,
            [{"key": "legislation_id", "match": {"value": legislation_id}}],
        )

    async def delete_legislation_by_id(
        self,
        legislation_id: str,
        legislation_collection: str = "legislation",
        section_collection: str = "legislation_section",
    ) -> dict[str, bool]:
        """Delete a legislation item and its sections from Qdrant.

        Returns ``{"legislation": True/False, "sections": True/False}``.
        """
        results: dict[str, bool] = {}

        # Delete from main legislation collection by id payload field
        try:
            results["legislation"] = await self.delete_by_filter(
                legislation_collection,
                [{"key": "id", "match": {"value": legislation_id}}],
            )
        except Exception:
            results["legislation"] = False
            logger.warning("lex_qdrant_delete_legislation_failed", legislation_id=legislation_id)

        # Delete sections
        try:
            results["sections"] = await self.delete_by_filter(
                section_collection,
                [{"key": "legislation_id", "match": {"value": legislation_id}}],
            )
        except Exception:
            results["sections"] = False
            logger.warning("lex_qdrant_delete_sections_failed", legislation_id=legislation_id)

        return results

    async def aclose(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()
