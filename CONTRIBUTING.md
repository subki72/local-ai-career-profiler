# Contributing to CV Nexus

Thank you for contributing to `local-ai-career-profiler`. Follow these guidelines to keep the codebase maintainable, secure, and production-ready.

## Development Setup

1. Clone the repository and create a Python 3.10+ virtual environment:
   ```bash
   git clone https://github.com/subki72/local-ai-career-profiler.git
   cd local-ai-career-profiler
   python -m venv .venv
   ```
2. Install runtime and QA dependencies:
   ```bash
   make install-dev
   ```
3. Copy the environment template if customizing local endpoints:
   ```bash
   cp .env.example .env
   ```
4. Install optional pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Engineering Standards

- **Lint & Format**: Run `make lint` (`flake8 --max-line-length=120 .`) and ensure zero warnings before committing.
- **Offline Tests**: Run `make test` (`python -m pytest -v`) and ensure 100% of unit and API integration tests pass without requiring a live Ollama or ChromaDB server.
- **Type Safety & Docstrings**: Annotate all function signatures and add Google-style docstrings to public modules, classes, and functions.
- **Observability**: Use `logging.getLogger(__name__)` (`logger.info`, `logger.warning`, `logger.error`, `logger.exception`) instead of raw stdout printing.
- **Security**: Never commit `.env` files, credentials, or raw candidate resumes beyond the tracked demo fixture. Validate external inputs and never expose internal tracebacks in HTTP responses.

## Commit & Pull Request Workflow

1. Create a feature branch from `main` (`git checkout -b feat/short-description`).
2. Write atomic commits using [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `build:`, `ci:`, `chore:`).
3. Verify `make lint` and `make test` succeed locally.
4. Open a Pull Request describing the motivation, architectural impact, and verification evidence.
