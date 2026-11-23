"""Application configuration loaded from environment variables with validation."""

from __future__ import annotations

from functools import lru_cache
import json
import logging
import os
from typing import Final

from pydantic import BaseModel, Field, field_validator

DEFAULT_ALLOWED_ORIGINS: Final[tuple[str, ...]] = (
    "http://localhost:8501",
    "http://localhost:3000",
)
VALID_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
)
BYTES_PER_MEGABYTE: Final[int] = 1024 * 1024


def parse_allowed_origins(raw_value: str | list[str] | None) -> list[str]:
    """Parse ALLOWED_ORIGINS from a comma-separated string, JSON list, or list.

    Args:
        raw_value: Environment value or list of allowed origin URLs.

    Returns:
        Normalized list of stripped origin strings.
    """
    if raw_value is None:
        return list(DEFAULT_ALLOWED_ORIGINS)
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]

    text = raw_value.strip()
    if not text:
        return []
    if text.startswith("["):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("ALLOWED_ORIGINS JSON value must be a list of strings.")
        return [str(item).strip() for item in parsed if str(item).strip()]

    return [origin.strip() for origin in text.split(",") if origin.strip()]


def _validate_http_url(url: str, field_name: str) -> str:
    """Ensure a configured service URL uses an explicit HTTP(S) scheme."""
    cleaned = url.strip().rstrip("/")
    if not cleaned.startswith(("http://", "https://")):
        raise ValueError(f"{field_name} must start with 'http://' or 'https://'.")
    return cleaned


class Settings(BaseModel):
    """Typed runtime configuration for the CV Nexus backend, UI, and MCP server."""

    allowed_origins: list[str] = Field(
        default_factory=lambda: list(DEFAULT_ALLOWED_ORIGINS),
        description="Explicit CORS origin allowlist for browser clients.",
    )
    max_upload_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum allowed uploaded PDF size in megabytes.",
    )
    upload_dir: str = Field(
        default="data/processed",
        min_length=1,
        description="Temporary directory for sanitized uploaded CV files.",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local Ollama inference server.",
    )
    ollama_model: str = Field(
        default="llama3",
        min_length=1,
        description="Local Ollama model identifier used for parsing and reasoning.",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        min_length=1,
        description="HuggingFace sentence-transformer model for job embeddings.",
    )
    chroma_db_dir: str = Field(
        default="data/chroma_db",
        min_length=1,
        description="Persistent directory for ChromaDB vector storage.",
    )
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="FastAPI backend base URL used by the Streamlit frontend.",
    )
    request_timeout_seconds: int = Field(
        default=120,
        ge=5,
        le=600,
        description="HTTP client timeout in seconds for backend requests.",
    )
    log_level: str = Field(
        default="INFO",
        description="Python logging severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _coerce_origins(cls, value: str | list[str] | None) -> list[str]:
        return parse_allowed_origins(value)

    @field_validator("allowed_origins")
    @classmethod
    def _validate_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one explicit origin.")
        for origin in origins:
            # Wildcard origins combined with allow_credentials=True weaken browser isolation.
            if origin == "*":
                raise ValueError("Wildcard '*' is not permitted in ALLOWED_ORIGINS.")
            _validate_http_url(origin, "ALLOWED_ORIGINS entry")
        return origins

    @field_validator("ollama_base_url")
    @classmethod
    def _validate_ollama_url(cls, value: str) -> str:
        return _validate_http_url(value, "OLLAMA_BASE_URL")

    @field_validator("api_base_url")
    @classmethod
    def _validate_api_url(cls, value: str) -> str:
        return _validate_http_url(value, "API_BASE_URL")

    @field_validator("upload_dir", "chroma_db_dir", "ollama_model", "embedding_model")
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Configuration string values cannot be blank.")
        return cleaned

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in VALID_LOG_LEVELS:
            allowed = ", ".join(sorted(VALID_LOG_LEVELS))
            raise ValueError(f"LOG_LEVEL must be one of: {allowed}.")
        return normalized

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the maximum upload size limit converted to bytes."""
        return self.max_upload_size_mb * BYTES_PER_MEGABYTE

    def validate_runtime(self) -> Settings:
        """Re-run explicit validation checks on the current settings instance.

        Returns:
            Validated Settings instance.
        """
        return Settings.model_validate(self.model_dump())

    @classmethod
    def from_env(cls) -> Settings:
        """Construct and validate Settings directly from process environment variables.

        Returns:
            Validated Settings populated from environment overrides and safe defaults.
        """
        raw_max_mb = os.getenv("MAX_UPLOAD_SIZE_MB", "10")
        raw_timeout = os.getenv("REQUEST_TIMEOUT_SECONDS", "120")

        settings = cls(
            allowed_origins=parse_allowed_origins(os.getenv("ALLOWED_ORIGINS")),
            max_upload_size_mb=int(raw_max_mb),
            upload_dir=os.getenv("UPLOAD_DIR", "data/processed"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            chroma_db_dir=os.getenv("CHROMA_DB_DIR", "data/chroma_db"),
            api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
            request_timeout_seconds=int(raw_timeout),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
        return settings.validate_runtime()


def configure_logging(level: str = "INFO") -> None:
    """Configure root structured logging for CV Nexus services.

    Args:
        level: Standard Python logging level name.
    """
    normalized = level.strip().upper()
    numeric_level = getattr(logging, normalized, logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, validated Settings instance loaded from environment variables."""
    return Settings.from_env()
