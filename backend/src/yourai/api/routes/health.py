"""Health check route at /api/v1/health for frontend compatibility."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """Simple health check — no auth required."""
    return {"status": "ok"}
