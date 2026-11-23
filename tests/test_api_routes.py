"""FastAPI integration tests for health probe, CORS, upload security, and CV routes."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from main import app, create_app
from src.analyzers.cv_parser import CandidateProfile
from src.api import routes
from src.api.routes import (
    GENERIC_PROCESSING_ERROR,
    get_app_settings,
    get_matchmaker,
)
from src.config import Settings

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


class _StubMatchmaker:
    """Offline stand-in for AIJobMatchmaker used via FastAPI dependency overrides."""

    def __init__(self, fail_with: Exception | None = None) -> None:
        self._fail_with = fail_with
        self.matched_profiles: list[CandidateProfile] = []
        self.profiled_candidates: list[CandidateProfile] = []

    def find_best_match_and_reason(self, candidate: CandidateProfile) -> str:
        if self._fail_with is not None:
            raise self._fail_with
        self.matched_profiles.append(candidate)
        return f"RECOMMENDED ROLE: AI Engineer\n\nREASONING:\nGreat fit for {candidate.name}."

    def open_market_profiling(self, candidate: CandidateProfile) -> str:
        if self._fail_with is not None:
            raise self._fail_with
        self.profiled_candidates.append(candidate)
        return f"Open market profile for {candidate.name}: AI Engineer, ML Engineer, Data Scientist."


def _sample_profile() -> CandidateProfile:
    """Return a deterministic parsed CandidateProfile for mocked API flows."""
    return CandidateProfile(
        name="Dina Kusuma",
        key_skills=["Python", "FastAPI", "LLM"],
        years_of_experience=3,
        summary="AI engineer building privacy-first NLP microservices.",
    )


@pytest.fixture()
def api_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, _StubMatchmaker, Path], None, None]:
    """Provide a TestClient with isolated upload directory and mocked AI dependencies."""
    upload_dir = tmp_path / "uploads"
    test_settings = Settings(
        allowed_origins=["http://localhost:8501"],
        max_upload_size_mb=1,
        upload_dir=str(upload_dir),
    )
    stub_matchmaker = _StubMatchmaker()

    app.dependency_overrides[get_matchmaker] = lambda: stub_matchmaker
    app.dependency_overrides[get_app_settings] = lambda: test_settings
    monkeypatch.setattr(routes, "extract_pdf_text", lambda path: "Extracted CV text")
    monkeypatch.setattr(routes, "parse_cv_with_local_ai", lambda text: _sample_profile())

    try:
        yield TestClient(app), stub_matchmaker, upload_dir
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_returns_healthy_and_security_headers(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
) -> None:
    """Verify GET /health responds with 200 OK and baseline HTTP security headers."""
    # Arrange
    client, _, _ = api_context

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "cv-nexus-api",
        "version": "1.0.0",
    }
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_cors_allows_configured_origin_and_blocks_untrusted_origin() -> None:
    """Verify CORS allowlist restricts browser access to configured origins only."""
    # Arrange
    isolated_app = create_app(Settings(allowed_origins=["http://localhost:8501"]))
    client = TestClient(isolated_app)

    # Act
    allowed_resp = client.get("/health", headers={"Origin": "http://localhost:8501"})
    blocked_resp = client.get("/health", headers={"Origin": "https://untrusted.example.com"})

    # Assert
    assert allowed_resp.headers.get("access-control-allow-origin") == "http://localhost:8501"
    assert allowed_resp.headers.get("access-control-allow-credentials") == "true"
    assert "access-control-allow-origin" not in blocked_resp.headers


def test_match_cv_processes_valid_pdf_and_cleans_up_temp_file(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
) -> None:
    """Verify POST /api/v1/match-cv returns ATS recommendation and removes temp files."""
    # Arrange
    client, stub_matchmaker, upload_dir = api_context
    files = {"file": ("candidate.pdf", VALID_PDF_BYTES, "application/pdf")}

    # Act
    response = client.post("/api/v1/match-cv", files=files)

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "candidate.pdf"
    assert "RECOMMENDED ROLE: AI Engineer" in body["recommendation_result"]
    assert len(stub_matchmaker.matched_profiles) == 1
    assert upload_dir.exists()
    assert list(upload_dir.iterdir()) == []


def test_profile_cv_processes_valid_pdf_and_cleans_up_temp_file(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
) -> None:
    """Verify POST /api/v1/profile-cv returns open-market profile and cleans temp files."""
    # Arrange
    client, stub_matchmaker, upload_dir = api_context
    files = {"file": ("resume.pdf", VALID_PDF_BYTES, "application/pdf")}

    # Act
    response = client.post("/api/v1/profile-cv", files=files)

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "resume.pdf"
    assert "Open market profile for Dina Kusuma" in body["recommendation_result"]
    assert len(stub_matchmaker.profiled_candidates) == 1
    assert list(upload_dir.iterdir()) == []


def test_match_cv_rejects_non_pdf_extension(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
) -> None:
    """Reject non-PDF file uploads with HTTP 400."""
    # Arrange
    client, _, _ = api_context
    files = {"file": ("notes.txt", b"plain text resume", "text/plain")}

    # Act
    response = client.post("/api/v1/match-cv", files=files)

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed."


def test_match_cv_rejects_invalid_pdf_magic_header(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
) -> None:
    """Reject spoofed .pdf uploads whose bytes lack the %PDF- magic header."""
    # Arrange
    client, _, _ = api_context
    files = {"file": ("spoofed.pdf", b"<html>not a pdf</html>", "application/pdf")}

    # Act
    response = client.post("/api/v1/match-cv", files=files)

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid PDF file content."


@pytest.mark.parametrize("malicious_name", ["../../evil.pdf", "..\\..\\evil.pdf"])
def test_match_cv_neutralizes_path_traversal_filename(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
    monkeypatch: pytest.MonkeyPatch,
    malicious_name: str,
) -> None:
    """Strip path traversal sequences and isolate temp file inside upload_dir with UUID prefix."""
    # Arrange
    client, _, upload_dir = api_context
    observed_paths: list[Path] = []

    def _capture_path(path: Path) -> str:
        observed_paths.append(Path(path))
        return "Safe extracted text"

    monkeypatch.setattr(routes, "extract_pdf_text", _capture_path)
    files = {"file": (malicious_name, VALID_PDF_BYTES, "application/pdf")}

    # Act
    response = client.post("/api/v1/match-cv", files=files)

    # Assert
    assert response.status_code == 200
    assert response.json()["filename"] == "evil.pdf"
    assert len(observed_paths) == 1
    written_path = observed_paths[0].resolve()
    assert written_path.parent == upload_dir.resolve()
    assert written_path.name.endswith("_evil.pdf")
    assert len(written_path.name) > len("_evil.pdf")
    assert not (upload_dir.parent / "evil.pdf").exists()
    assert list(upload_dir.iterdir()) == []


def test_match_cv_rejects_oversized_pdf_with_413(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
) -> None:
    """Enforce MAX_UPLOAD_SIZE_MB limit and return HTTP 413 Payload Too Large."""
    # Arrange
    client, _, _ = api_context
    oversized_payload = VALID_PDF_BYTES + (b"0" * (1024 * 1024 + 128))
    files = {"file": ("huge.pdf", oversized_payload, "application/pdf")}

    # Act
    response = client.post("/api/v1/match-cv", files=files)

    # Assert
    assert response.status_code == 413
    assert "maximum file size" in response.json()["detail"]


def test_match_cv_returns_safe_500_without_leaking_internal_exception(
    api_context: tuple[TestClient, _StubMatchmaker, Path],
) -> None:
    """Mask internal exception text in HTTP 500 responses to prevent information leakage."""
    # Arrange
    client, _, upload_dir = api_context
    sensitive_detail = "sensitive-internal-stack-info-do-not-leak"
    app.dependency_overrides[get_matchmaker] = lambda: _StubMatchmaker(
        fail_with=RuntimeError(sensitive_detail)
    )
    files = {"file": ("candidate.pdf", VALID_PDF_BYTES, "application/pdf")}

    # Act
    response = client.post("/api/v1/match-cv", files=files)

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": GENERIC_PROCESSING_ERROR}
    assert sensitive_detail not in response.text
    assert list(upload_dir.iterdir()) == []


def test_global_exception_handler_masks_unexpected_crash() -> None:
    """Verify the global FastAPI exception handler returns a safe generic 500 payload."""
    # Arrange
    isolated_app = create_app(Settings(allowed_origins=["http://localhost:8501"]))

    @isolated_app.get("/_test-boom")
    async def _boom() -> dict[str, str]:
        raise RuntimeError("secret-crash-context")

    client = TestClient(isolated_app, raise_server_exceptions=False)

    # Act
    response = client.get("/_test-boom")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}
    assert "secret-crash-context" not in response.text
