"""Text extraction from PDF, DOCX, and TXT files.

Uses PyMuPDF for PDFs (with heading detection via font-size heuristics),
python-docx for DOCX (paragraph styles), and plain read for TXT.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class Section:
    """A section of extracted text with optional heading."""

    heading: str | None = None
    content: str = ""
    level: int = 0  # Heading level (1 = top-level)


@dataclass
class ExtractionResult:
    """Result of text extraction from a document."""

    text: str
    strategy: str
    sections: list[Section] = field(default_factory=list)


def extract_text(data: bytes, mime_type: str, filename: str) -> ExtractionResult:
    """Extract text from a document based on its MIME type."""
    if mime_type == "application/pdf":
        return _extract_pdf(data)
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(data)
    if mime_type == "text/plain":
        return _extract_txt(data)

    raise ValueError(f"Unsupported MIME type: {mime_type}")


def _extract_pdf(data: bytes) -> ExtractionResult:
    """Extract text from PDF using PyMuPDF with heading detection via font-size heuristics."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        all_text_parts: list[str] = []
        sections: list[Section] = []
        current_section: Section | None = None

        # First pass: determine median font size for heading detection
        font_sizes: list[float] = []
        for page in doc:
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            font_sizes.append(span["size"])

        if not font_sizes:
            return ExtractionResult(text="", strategy="pdf_pymupdf")

        font_sizes.sort()
        median_size = font_sizes[len(font_sizes) // 2]
        heading_threshold = median_size * 1.2  # 20% larger than median = heading

        # Second pass: extract text with section detection
        for page in doc:
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    line_text = ""
                    is_heading = False
                    for span in line["spans"]:
                        text = span["text"]
                        line_text += text
                        if span["size"] >= heading_threshold and text.strip():
                            is_heading = True

                    line_text = line_text.strip()
                    if not line_text:
                        continue

                    all_text_parts.append(line_text)

                    if is_heading:
                        level = (
                            1 if font_sizes and line["spans"][0]["size"] >= median_size * 1.5 else 2
                        )
                        current_section = Section(heading=line_text, content="", level=level)
                        sections.append(current_section)
                    elif current_section is not None:
                        current_section.content += line_text + "\n"
                    else:
                        current_section = Section(heading=None, content=line_text + "\n", level=0)
                        sections.append(current_section)

        full_text = "\n".join(all_text_parts)
        # Clean up trailing whitespace in sections
        for section in sections:
            section.content = section.content.rstrip()

        return ExtractionResult(text=full_text, strategy="pdf_pymupdf", sections=sections)
    finally:
        doc.close()


def _extract_docx(data: bytes) -> ExtractionResult:
    """Extract text from DOCX using python-docx with paragraph style detection."""
    import io

    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(data))
    all_text_parts: list[str] = []
    sections: list[Section] = []
    current_section: Section | None = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        all_text_parts.append(text)
        style_name = (para.style.name or "").lower() if para.style else ""

        is_heading = "heading" in style_name
        if is_heading:
            # Extract heading level from style name (e.g. "Heading 1" -> 1)
            level = 1
            parts = style_name.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                level = int(parts[-1])
            current_section = Section(heading=text, content="", level=level)
            sections.append(current_section)
        elif current_section is not None:
            current_section.content += text + "\n"
        else:
            current_section = Section(heading=None, content=text + "\n", level=0)
            sections.append(current_section)

    full_text = "\n".join(all_text_parts)
    for section in sections:
        section.content = section.content.rstrip()

    return ExtractionResult(text=full_text, strategy="docx_python_docx", sections=sections)


def _extract_txt(data: bytes) -> ExtractionResult:
    """Extract text from plain text file with charset detection."""
    # Try UTF-8 first, then latin-1 as fallback
    for encoding in ("utf-8", "latin-1"):
        try:
            text = data.decode(encoding)
            return ExtractionResult(
                text=text,
                strategy=f"txt_{encoding}",
                sections=[Section(heading=None, content=text, level=0)],
            )
        except UnicodeDecodeError:
            continue

    # Final fallback with replacement characters
    text = data.decode("utf-8", errors="replace")
    return ExtractionResult(
        text=text,
        strategy="txt_utf8_replace",
        sections=[Section(heading=None, content=text, level=0)],
    )
