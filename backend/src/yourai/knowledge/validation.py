"""Upload validation: size, MIME type, encrypted PDF detection."""

from __future__ import annotations

import structlog

from yourai.core.config import settings
from yourai.core.exceptions import ValidationError

logger = structlog.get_logger()

# Magic bytes for supported file types
_MAGIC_BYTES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        b"PK\x03\x04",
    ],
    "text/plain": [],  # Fallback — no specific magic bytes
}

ALLOWED_MIME_TYPES = set(_MAGIC_BYTES.keys())


def detect_mime_type(data: bytes, filename: str) -> str:
    """Detect MIME type from magic bytes, falling back to file extension."""
    for mime, signatures in _MAGIC_BYTES.items():
        for sig in signatures:
            if data[: len(sig)] == sig:
                # Distinguish DOCX from other ZIP-based formats
                if (
                    mime
                    == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    and b"word/" not in data[:2000]
                ):
                    continue
                return mime

    # Fallback to extension
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if lower.endswith(".txt"):
        return "text/plain"

    return "application/octet-stream"


def _is_encrypted_pdf(data: bytes) -> bool:
    """Check if a PDF is encrypted by looking for /Encrypt in the header area."""
    # Check first 4096 bytes and last 4096 bytes for /Encrypt dictionary
    header = data[:4096]
    trailer = data[-4096:] if len(data) > 4096 else data
    return b"/Encrypt" in header or b"/Encrypt" in trailer


def validate_upload(data: bytes, filename: str, tenant_id: str) -> str:
    """Validate uploaded file. Returns detected MIME type.

    Raises ValidationError if:
    - File exceeds max upload size
    - MIME type is not allowed
    - PDF is encrypted
    """
    # Size check
    if len(data) > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_bytes / (1024 * 1024)
        logger.warning(
            "upload_too_large",
            tenant_id=tenant_id,
            filename=filename,
            size=len(data),
            max_size=settings.max_upload_size_bytes,
        )
        raise ValidationError(
            f"File exceeds maximum upload size of {max_mb:.0f} MB.",
            detail={"size": len(data), "max_size": settings.max_upload_size_bytes},
        )

    # MIME type detection
    mime_type = detect_mime_type(data, filename)
    if mime_type not in ALLOWED_MIME_TYPES:
        logger.warning(
            "upload_invalid_type",
            tenant_id=tenant_id,
            filename=filename,
            mime_type=mime_type,
        )
        raise ValidationError(
            f"File type '{mime_type}' is not supported. Supported types: PDF, DOCX, TXT.",
            detail={"mime_type": mime_type},
        )

    # Encrypted PDF check
    if mime_type == "application/pdf" and _is_encrypted_pdf(data):
        logger.warning(
            "upload_encrypted_pdf",
            tenant_id=tenant_id,
            filename=filename,
        )
        raise ValidationError(
            "Encrypted PDFs are not supported. Please upload an unencrypted version.",
        )

    return mime_type
