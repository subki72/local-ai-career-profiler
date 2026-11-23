# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this repository:

1. **Do NOT open a public GitHub issue** for undisclosed vulnerabilities.
2. Submit a private report via GitHub Security Advisories (`Security -> Advisories -> Report a vulnerability`).
3. Include affected file paths, line numbers, reproduction steps, and estimated severity.
4. Initial acknowledgement will be provided within **48 hours**.

## Security Controls

- **100% Local Privacy Boundary**: Resume parsing, embeddings, and vector search run exclusively against local Ollama, HuggingFace, and ChromaDB instances with zero external LLM API calls.
- **Upload Hardening**: FastAPI endpoints strip directory traversal segments via `Path(...).name`, assign UUID-prefixed temporary filenames inside `UPLOAD_DIR`, validate `.pdf` extensions and `%PDF-` magic headers, enforce `MAX_UPLOAD_SIZE_MB` streaming byte limits (HTTP 413), and unconditionally clean up temporary files.
- **CORS & HTTP Headers**: Wildcard `*` origins are rejected at configuration validation time; explicit `ALLOWED_ORIGINS` and baseline headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) are enforced on every response.
- **Safe Error Handling**: Internal exceptions are logged server-side with full tracebacks while HTTP clients receive sanitized generic 500 JSON responses.
- **Secret Hygiene & Automated Scans**: `.env` and key files are excluded via `.gitignore`; CI executes Semgrep SAST, Trivy container scans, and weekly Dependabot updates (`semver-major` ignored for build stability).
- **Container Hardening**: Multi-stage non-root Docker builds (`USER appuser`) with liveness `HEALTHCHECK`.
