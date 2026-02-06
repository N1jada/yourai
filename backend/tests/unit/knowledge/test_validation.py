"""Tests for upload validation: size limits, MIME detection, encrypted PDF rejection."""

from __future__ import annotations

import pytest

from yourai.core.exceptions import ValidationError
from yourai.knowledge.validation import detect_mime_type, validate_upload


class TestDetectMimeType:
    """Tests for MIME type detection."""

    def test_pdf_magic_bytes(self):
        data = b"%PDF-1.4 some content here"
        assert detect_mime_type(data, "document.pdf") == "application/pdf"

    def test_pdf_by_extension_fallback(self):
        data = b"not a real pdf"
        assert detect_mime_type(data, "document.pdf") == "application/pdf"

    def test_txt_by_extension(self):
        data = b"plain text content"
        assert detect_mime_type(data, "readme.txt") == "text/plain"

    def test_docx_by_extension(self):
        data = b"not a real zip"
        assert detect_mime_type(data, "document.docx") == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_unknown_type(self):
        data = b"\x00\x01\x02"
        assert detect_mime_type(data, "file.xyz") == "application/octet-stream"


class TestValidateUpload:
    """Tests for the validate_upload function."""

    def test_valid_pdf(self):
        data = b"%PDF-1.4 some content here"
        result = validate_upload(data, "test.pdf", "tenant-1")
        assert result == "application/pdf"

    def test_valid_txt(self):
        data = b"Hello, this is plain text."
        result = validate_upload(data, "test.txt", "tenant-1")
        assert result == "text/plain"

    def test_size_limit_exceeded(self):
        # Create data larger than max (50MB default, but we can test with a smaller limit)
        from yourai.core.config import settings

        original = settings.max_upload_size_bytes
        settings.max_upload_size_bytes = 100  # 100 bytes for testing
        try:
            data = b"x" * 200
            with pytest.raises(ValidationError, match="exceeds maximum upload size"):
                validate_upload(data, "test.txt", "tenant-1")
        finally:
            settings.max_upload_size_bytes = original

    def test_unsupported_mime_type(self):
        data = b"\x00\x01\x02\x03"
        with pytest.raises(ValidationError, match="not supported"):
            validate_upload(data, "file.xyz", "tenant-1")

    def test_encrypted_pdf_rejected(self):
        # Simulate an encrypted PDF with /Encrypt in header
        data = b"%PDF-1.4 /Encrypt some encrypted content"
        with pytest.raises(ValidationError, match="Encrypted PDFs"):
            validate_upload(data, "encrypted.pdf", "tenant-1")

    def test_non_encrypted_pdf_accepted(self):
        data = b"%PDF-1.4 regular content without encryption markers"
        result = validate_upload(data, "normal.pdf", "tenant-1")
        assert result == "application/pdf"
