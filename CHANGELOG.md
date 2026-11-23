# Changelog

All notable changes to **CV Nexus (`local-ai-career-profiler`)** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-23

### Added
- Typed environment configuration module (`src/config.py`) backed by Pydantic `Settings` with explicit startup validation for `ALLOWED_ORIGINS`, `MAX_UPLOAD_SIZE_MB`, `UPLOAD_DIR`, `OLLAMA_BASE_URL`, `CHROMA_DB_DIR`, and `LOG_LEVEL`.
- Liveness health check endpoint (`GET /health`), centralized unhandled exception handler, and baseline HTTP security headers in `main.py`.
- Offline automated test suite under `tests/` (`test_api_routes.py`, `test_config.py`, `test_job_schema.py`, `test_pdf_reader.py`, `test_cv_parser.py`, `test_job_matcher.py`) verified with `pytest`.
- Multi-stage non-root `Dockerfile` (`USER appuser`, `HEALTHCHECK`), `docker-compose.yml`, `.dockerignore`, and `Makefile`.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running Flake8, Ruff, Pytest with coverage gate, Semgrep SAST, Docker build, and Trivy container scans.
- Dependency governance and security documentation: `requirements-lock.txt`, `uv.lock`, `pyproject.toml`, `.flake8`, `.pre-commit-config.yaml`, `.github/dependabot.yml`, `SECURITY.md`, `LICENSE`, `CONTRIBUTING.md`, and `docs/RUNBOOK.md`.

### Changed
- Replaced eager module-level `AIJobMatchmaker()` initialization in API routes and MCP server with thread-safe lazy singletons and FastAPI `Depends(get_matchmaker)` dependency injection.
- Replaced all raw `print()` statements across `main.py`, `seed_db.py`, and `src/` with structured leveled logging (`logging.getLogger(__name__)`).
- Extracted shared CV upload, validation, parsing, and cleanup pipeline into `_process_uploaded_cv()` in `src/api/routes.py`.
- Added explicit HTTP client timeout handling to `src/frontend/app.py` and resolved all 131 Flake8 style/lint issues.

### Security
- Neutralized path traversal in CV upload endpoints by normalizing filenames via `Path(...).name`, generating UUID-prefixed temp paths inside `UPLOAD_DIR`, validating `.pdf` extensions and `%PDF-` magic headers, and enforcing streaming `MAX_UPLOAD_SIZE_MB` limits (HTTP 413).
- Replaced wildcard CORS (`allow_origins=["*"]` with credentials) with validated `ALLOWED_ORIGINS`.
- Masked internal server exception details in HTTP 500 JSON responses while preserving full tracebacks in server-side logs.

## [0.1.0] - 2026-03-29

### Added
- Initial proof-of-concept release of CV Nexus Dual-Engine AI Career Profiler (FastAPI backend, Streamlit frontend, ChromaDB ATS matcher, Ollama Llama 3 parser, and FastMCP stdio server).
