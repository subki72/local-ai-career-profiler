"""Offline unit tests for PDF text extraction and text cleaning utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.extractors import pdf_reader
from src.extractors.pdf_reader import clean_extracted_text, extract_pdf_text


class _FakePage:
    """Lightweight stub mimicking a PyMuPDF page object."""

    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self) -> str:
        return self._text


class _FakeDocument:
    """Context-manager stub mimicking a PyMuPDF Document."""

    def __init__(self, pages: list[_FakePage]) -> None:
        self._pages = pages
        self.closed = False

    def __enter__(self) -> _FakeDocument:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.closed = True

    def __iter__(self) -> Any:
        return iter(self._pages)

    def __len__(self) -> int:
        return len(self._pages)


def test_clean_extracted_text_normalizes_hyphens_and_spaces() -> None:
    """Repair hyphenated line wraps and collapse irregular whitespace."""
    # Arrange
    raw = "Built end-to-\nend ML\npipelines   with\tPython.\n\nDeployed   APIs."

    # Act
    cleaned = clean_extracted_text(raw)

    # Assert
    assert cleaned == "Built end-to-end ML pipelines with Python. Deployed APIs."


def test_clean_extracted_text_handles_empty_input() -> None:
    """Return an empty string for empty input without error."""
    # Act & Assert
    assert clean_extracted_text("") == ""


def test_extract_pdf_text_reads_sample_cv() -> None:
    """Extract readable resume text from the tracked sample_cv.pdf fixture."""
    # Arrange
    sample_pdf = Path("data/raw_cv/sample_cv.pdf")
    assert sample_pdf.is_file()

    # Act
    extracted = extract_pdf_text(sample_pdf)

    # Assert
    assert len(extracted) > 100
    assert "Data Scientist" in extracted


def test_extract_pdf_text_raises_for_missing_file(tmp_path: Path) -> None:
    """Raise FileNotFoundError when the requested PDF path does not exist."""
    # Arrange
    missing_pdf = tmp_path / "does_not_exist.pdf"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        extract_pdf_text(missing_pdf)


def test_extract_pdf_text_rejects_blank_path() -> None:
    """Raise ValueError when an empty file path string is supplied."""
    # Act & Assert
    with pytest.raises(ValueError):
        extract_pdf_text("   ")


def test_extract_pdf_text_closes_document_context_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify multi-page mocked PyMuPDF documents are concatenated and closed."""
    # Arrange
    pdf_file = tmp_path / "mock_resume.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 mock content")
    fake_doc = _FakeDocument(
        [_FakePage("Page one\nhyphen-\nated "), _FakePage("and page two.")]
    )
    monkeypatch.setattr(pdf_reader.fitz, "open", lambda path: fake_doc)

    # Act
    result = extract_pdf_text(pdf_file)

    # Assert
    assert result == "Page one hyphen-ated and page two."
    assert fake_doc.closed is True
