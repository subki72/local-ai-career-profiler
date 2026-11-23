"""PDF text extraction and whitespace normalization utilities."""

from __future__ import annotations

import logging
from pathlib import Path
import re

import fitz  # PyMuPDF

from src.config import configure_logging

logger = logging.getLogger(__name__)


def clean_extracted_text(raw_text: str) -> str:
    """Normalize raw PDF text by repairing broken lines and excess whitespace.

    Args:
        raw_text: Raw text extracted directly from PDF pages.

    Returns:
        Cleaned continuous text suitable for downstream LLM parsing.
    """
    if not raw_text:
        return ""

    # Repair hyphenated tokens split across line wraps (e.g., "end-to-\nend").
    text = re.sub(r"-\n+", "-", raw_text)
    # Join mid-paragraph line wraps while preserving paragraph boundaries.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_text(file_path: str | Path) -> str:
    """Open a PDF file, extract text across all pages, and return cleaned text.

    Args:
        file_path: Path to a readable PDF file on disk.

    Returns:
        Cleaned text extracted from every page in the document.

    Raises:
        ValueError: If file_path is empty.
        FileNotFoundError: If the target PDF file does not exist.
    """
    if not file_path or not str(file_path).strip():
        raise ValueError("PDF file path must not be empty.")

    resolved_path = Path(file_path)
    if not resolved_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {resolved_path}")

    page_chunks: list[str] = []
    with fitz.open(str(resolved_path)) as document:
        for page in document:
            page_chunks.append(page.get_text())
        page_count = len(document)

    cleaned = clean_extracted_text("".join(page_chunks))
    logger.info(
        "Extracted %d characters across %d PDF page(s) from '%s'.",
        len(cleaned),
        page_count,
        resolved_path.name,
    )
    return cleaned


if __name__ == "__main__":
    configure_logging()
    sample_file = Path("data/raw_cv/sample_cv.pdf")
    try:
        extracted_text = extract_pdf_text(sample_file)
        logger.info("Sample extraction preview: %s", extracted_text[:200])
    except Exception:
        logger.exception("Failed to extract text from sample PDF '%s'.", sample_file)
