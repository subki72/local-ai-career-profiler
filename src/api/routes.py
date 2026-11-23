"""Hardened FastAPI routes for CV upload, ATS matching, and open-market profiling."""

from __future__ import annotations

import logging
from pathlib import Path
import re
import threading
from typing import Final
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.analyzers.cv_parser import CandidateProfile, parse_cv_with_local_ai
from src.config import Settings, get_settings
from src.extractors.pdf_reader import extract_pdf_text
from src.recommenders.job_matcher import AIJobMatchmaker

logger = logging.getLogger(__name__)

PDF_MAGIC_HEADER: Final[bytes] = b"%PDF-"
UPLOAD_CHUNK_SIZE_BYTES: Final[int] = 64 * 1024
GENERIC_PROCESSING_ERROR: Final[str] = "Internal error while processing the uploaded CV."

router = APIRouter()

_matchmaker_lock = threading.Lock()
_matchmaker_instance: AIJobMatchmaker | None = None


class MatchResponse(BaseModel):
    """Response contract returned by CV matching and profiling endpoints."""

    filename: str
    recommendation_result: str


def get_app_settings() -> Settings:
    """FastAPI dependency returning validated runtime configuration."""
    return get_settings()


def get_matchmaker() -> AIJobMatchmaker:
    """Lazily initialize and return the process-wide AIJobMatchmaker singleton.

    Lazy initialization prevents module import side effects so tests and tooling
    can import the FastAPI app without a running Ollama or ChromaDB service.
    """
    global _matchmaker_instance
    if _matchmaker_instance is not None:
        return _matchmaker_instance

    with _matchmaker_lock:
        if _matchmaker_instance is None:
            logger.info("Lazily initializing AIJobMatchmaker for API routes.")
            _matchmaker_instance = AIJobMatchmaker()
    return _matchmaker_instance


def _sanitize_pdf_filename(filename: str | None) -> str:
    """Strip directory traversal components and validate the PDF extension."""
    if not filename or not filename.strip():
        raise HTTPException(status_code=400, detail="A PDF filename is required.")

    # Normalize backslashes first so Windows traversal payloads are neutralized on Linux too.
    normalized = filename.replace("\\", "/")
    base_name = Path(normalized).name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", base_name).lstrip(".")

    if not safe_name.lower().endswith(".pdf") or safe_name.lower() == ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    return safe_name


async def _read_and_validate_pdf_bytes(file: UploadFile, max_bytes: int) -> bytes:
    """Read uploaded bytes within size limits and verify the PDF magic header."""
    chunks: list[bytes] = []
    total_read = 0

    while True:
        chunk = await file.read(UPLOAD_CHUNK_SIZE_BYTES)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_bytes:
            raise HTTPException(
                status_code=413,
                detail="Uploaded PDF exceeds the configured maximum file size.",
            )
        chunks.append(chunk)

    payload = b"".join(chunks)
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded PDF file is empty.")
    if not payload.startswith(PDF_MAGIC_HEADER):
        raise HTTPException(status_code=400, detail="Invalid PDF file content.")
    return payload


def _build_safe_temp_path(upload_dir: str, safe_name: str) -> Path:
    """Construct a UUID-prefixed temporary path strictly contained in upload_dir."""
    upload_root = Path(upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    temp_path = (upload_root / f"{uuid.uuid4().hex}_{safe_name}").resolve()
    if upload_root not in temp_path.parents:
        raise HTTPException(status_code=400, detail="Invalid upload path.")
    return temp_path


async def _process_uploaded_cv(
    file: UploadFile,
    settings: Settings,
) -> tuple[str, CandidateProfile]:
    """Validate, temporarily persist, extract, parse, and clean up an uploaded PDF."""
    safe_name = _sanitize_pdf_filename(file.filename)
    pdf_bytes = await _read_and_validate_pdf_bytes(file, settings.max_upload_size_bytes)
    temp_path = _build_safe_temp_path(settings.upload_dir, safe_name)

    try:
        temp_path.write_bytes(pdf_bytes)
        clean_text = extract_pdf_text(temp_path)
        candidate_profile = parse_cv_with_local_ai(clean_text)
        return safe_name, candidate_profile
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed during CV extraction or parsing for '%s'.", safe_name)
        raise HTTPException(status_code=500, detail=GENERIC_PROCESSING_ERROR) from exc
    finally:
        temp_path.unlink(missing_ok=True)


@router.post("/match-cv", response_model=MatchResponse)
async def upload_and_match_cv(
    file: UploadFile = File(...),
    matchmaker: AIJobMatchmaker = Depends(get_matchmaker),
    settings: Settings = Depends(get_app_settings),
) -> MatchResponse:
    """Match an uploaded PDF resume against the internal ChromaDB job database."""
    safe_name, candidate_profile = await _process_uploaded_cv(file, settings)

    try:
        final_recommendation = matchmaker.find_best_match_and_reason(candidate_profile)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Job matching failed for '%s'.", safe_name)
        raise HTTPException(status_code=500, detail=GENERIC_PROCESSING_ERROR) from exc

    return MatchResponse(
        filename=safe_name,
        recommendation_result=final_recommendation,
    )


@router.post("/profile-cv", response_model=MatchResponse)
async def upload_and_profile_cv(
    file: UploadFile = File(...),
    matchmaker: AIJobMatchmaker = Depends(get_matchmaker),
    settings: Settings = Depends(get_app_settings),
) -> MatchResponse:
    """Generate an open-market career profile directly from an uploaded PDF resume."""
    safe_name, candidate_profile = await _process_uploaded_cv(file, settings)

    try:
        profiling_result = matchmaker.open_market_profiling(candidate_profile)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Open-market profiling failed for '%s'.", safe_name)
        raise HTTPException(status_code=500, detail=GENERIC_PROCESSING_ERROR) from exc

    return MatchResponse(
        filename=safe_name,
        recommendation_result=profiling_result,
    )
