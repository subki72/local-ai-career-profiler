# Operations Runbook — CV Nexus (`local-ai-career-profiler`)

This runbook documents startup, monitoring, troubleshooting, backup, and rollback procedures for running CV Nexus in local or containerized production environments.

## 1. Service Topology & Health Probes

| Component | Default Port | Health / Verification Command |
|---|---:|---|
| FastAPI Backend (`main:app`) | `8000` | `curl -f http://localhost:8000/health` |
| Streamlit Frontend (`src/frontend/app.py`) | `8501` | Open `http://localhost:8501` |
| Local Ollama Inference Server | `11434` | `curl -f http://localhost:11434/api/tags` |
| FastMCP Stdio Server (`src.mcp_server.server`) | stdio | Configured in MCP host client |

Expected `GET /health` payload:
```json
{
  "status": "healthy",
  "service": "cv-nexus-api",
  "version": "1.0.0"
}
```

## 2. Standard Startup & Database Seeding

### Local Development (Makefile)
1. Ensure Ollama is running and the configured model (`llama3` by default) is pulled:
   ```bash
   ollama pull llama3
   ```
2. Copy `.env.example` to `.env` and adjust `ALLOWED_ORIGINS`, `MAX_UPLOAD_SIZE_MB`, or `OLLAMA_BASE_URL` if needed.
3. Seed baseline internal jobs into persistent ChromaDB:
   ```bash
   make seed
   ```
4. Launch the API and Streamlit UI in separate shells:
   ```bash
   make run-api
   make run-ui
   ```

### Containerized Stack (Docker Compose)
```bash
make docker-up
```
To seed jobs inside the running container:
```bash
docker compose exec api python seed_db.py
```

## 3. Runtime Configuration Controls

| Environment Variable | Default | Operational Notes |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:8501,http://localhost:3000` | Explicit comma-separated allowlist; `*` is rejected on startup |
| `MAX_UPLOAD_SIZE_MB` | `10` | Enforced via streaming chunk counter (`413` on overflow) |
| `UPLOAD_DIR` | `data/processed` | Ephemeral sanitized PDF staging directory; files deleted in `finally` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Set to `http://host.docker.internal:11434` in Docker Compose |
| `OLLAMA_MODEL` | `llama3` | Deterministic parsing uses `temperature=0.0` |
| `CHROMA_DB_DIR` | `data/chroma_db` | Persistent vector store directory |
| `REQUEST_TIMEOUT_SECONDS` | `120` | Streamlit HTTP timeout for local LLM inference |
| `LOG_LEVEL` | `INFO` | Set to `DEBUG` temporarily during incident triage |

## 4. Incident Triage & Troubleshooting

### Symptom: API returns HTTP `500` (`Internal error while processing the uploaded CV.`)
- **Action**: Inspect API logs (`docker compose logs -f api`). Because internal tracebacks are intentionally masked from HTTP clients, exact failure causes are logged server-side.
- **Common Causes**:
  1. Ollama daemon is down or `OLLAMA_MODEL` is not pulled -> verify `curl http://localhost:11434/api/tags` and run `ollama pull llama3`.
  2. LLM returned non-JSON output -> confirm the selected model supports Ollama `format="json"`.
  3. Disk permissions on `UPLOAD_DIR` or `CHROMA_DB_DIR` -> ensure directories are owned by `appuser` (UID `10001`) in Docker.

### Symptom: Uploads fail with HTTP `400` or `413`
- **`400 Only PDF files are allowed.`**: Verify filename ends with `.pdf`.
- **`400 Invalid PDF file content.`**: File lacks the `%PDF-` magic header (corrupted or renamed non-PDF file).
- **`413 Uploaded PDF exceeds the configured maximum file size.`**: Increase `MAX_UPLOAD_SIZE_MB` (up to `100`) if legitimate large resumes are expected.

### Symptom: Browser CORS errors from frontend
- **Action**: Add the exact frontend scheme + host + port to `ALLOWED_ORIGINS` and restart the API. Wildcard `*` is rejected by `src/config.py`.

### Symptom: ATS Matcher returns `"No suitable jobs found in the database."`
- **Action**: ChromaDB collection is empty. Run `make seed` (or `docker compose exec api python seed_db.py`) and verify `CHROMA_DB_DIR` points to the persisted volume.

## 5. Backup, Recovery & Rollback

- **Vector Store Backup**: Stop writes and archive `data/chroma_db/` (or the `chroma_data` Docker volume). Re-seeding default jobs is idempotent via `python seed_db.py`.
- **Release Rollback**:
  ```bash
  git checkout v1.0.0
  make docker-up
  ```
- **Verification After Recovery**: Confirm `GET /health` returns HTTP 200, run `make test` on a staging checkout, and submit `data/raw_cv/sample_cv.pdf` to `POST /api/v1/match-cv`.
