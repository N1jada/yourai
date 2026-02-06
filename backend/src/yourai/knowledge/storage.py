"""File storage abstraction for document uploads.

Provides a `FileStorage` protocol and a `LocalFileStorage` implementation
that stores files on the local filesystem under `./uploads/{tenant}/{doc}/{file}`.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

import structlog

from yourai.core.config import settings

logger = structlog.get_logger()


class FileStorage(Protocol):
    """Protocol for file storage backends."""

    async def save(self, tenant_id: UUID, document_id: UUID, filename: str, data: bytes) -> str:
        """Save file data and return the storage path."""
        ...

    async def read(self, path: str) -> bytes:
        """Read file data from storage."""
        ...

    async def delete(self, path: str) -> None:
        """Delete a file from storage."""
        ...

    async def file_hash(self, data: bytes) -> str:
        """Compute SHA-256 hash of file data."""
        ...


class LocalFileStorage:
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.upload_dir)

    async def save(self, tenant_id: UUID, document_id: UUID, filename: str, data: bytes) -> str:
        """Save file to local filesystem."""
        dir_path = self.base_dir / str(tenant_id) / str(document_id)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / filename
        file_path.write_bytes(data)
        logger.info(
            "file_saved",
            tenant_id=str(tenant_id),
            document_id=str(document_id),
            path=str(file_path),
            size=len(data),
        )
        return str(file_path)

    async def read(self, path: str) -> bytes:
        """Read file from local filesystem."""
        return Path(path).read_bytes()

    async def delete(self, path: str) -> None:
        """Delete file and parent directory if empty."""
        file_path = Path(path)
        if file_path.exists():
            parent = file_path.parent
            file_path.unlink()
            # Clean up empty directories
            if parent.exists() and not any(parent.iterdir()):
                shutil.rmtree(parent, ignore_errors=True)
            logger.info("file_deleted", path=path)

    async def file_hash(self, data: bytes) -> str:
        """Compute SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()
