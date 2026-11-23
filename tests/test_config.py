"""Offline unit tests for environment configuration and Settings validation."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from src.config import Settings, get_settings, parse_allowed_origins


def test_settings_defaults_from_clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify safe local defaults when no environment overrides are set."""
    # Arrange
    for var in (
        "ALLOWED_ORIGINS",
        "MAX_UPLOAD_SIZE_MB",
        "UPLOAD_DIR",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "CHROMA_DB_DIR",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(var, raising=False)

    # Act
    settings = Settings.from_env()

    # Assert
    assert settings.allowed_origins == ["http://localhost:8501", "http://localhost:3000"]
    assert settings.max_upload_size_mb == 10
    assert settings.max_upload_size_bytes == 10 * 1024 * 1024
    assert settings.upload_dir == "data/processed"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.chroma_db_dir == "data/chroma_db"
    assert settings.log_level == "INFO"


def test_settings_from_env_parses_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify comma-separated ALLOWED_ORIGINS and custom environment overrides."""
    # Arrange
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com, http://127.0.0.1:8501 ")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "5")
    monkeypatch.setenv("UPLOAD_DIR", "tmp/uploads")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/")
    monkeypatch.setenv("CHROMA_DB_DIR", "tmp/chroma")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    # Act
    settings = Settings.from_env()

    # Assert
    assert settings.allowed_origins == ["https://app.example.com", "http://127.0.0.1:8501"]
    assert settings.max_upload_size_mb == 5
    assert settings.max_upload_size_bytes == 5 * 1024 * 1024
    assert settings.upload_dir == "tmp/uploads"
    assert settings.ollama_base_url == "http://ollama:11434"
    assert settings.chroma_db_dir == "tmp/chroma"
    assert settings.log_level == "DEBUG"


def test_parse_allowed_origins_supports_json_array() -> None:
    """Verify JSON-formatted origin arrays are parsed accurately."""
    # Arrange
    raw = '["http://localhost:8501", "https://career.local"]'

    # Act
    origins = parse_allowed_origins(raw)

    # Assert
    assert origins == ["http://localhost:8501", "https://career.local"]


@pytest.mark.parametrize(
    "invalid_origins",
    [
        ["*"],
        ["http://localhost:8501", "*"],
        [],
        ["ftp://invalid.local"],
    ],
)
def test_settings_rejects_invalid_allowed_origins(invalid_origins: list[str]) -> None:
    """Reject wildcard, empty, or non-HTTP CORS origins."""
    # Act & Assert
    with pytest.raises(ValidationError):
        Settings(allowed_origins=invalid_origins)


@pytest.mark.parametrize("invalid_size", [0, -3, 101])
def test_settings_rejects_out_of_range_upload_limit(invalid_size: int) -> None:
    """Reject non-positive or excessively large upload size limits."""
    # Act & Assert
    with pytest.raises(ValidationError):
        Settings(max_upload_size_mb=invalid_size)


def test_settings_rejects_invalid_log_level_and_url() -> None:
    """Reject unsupported logging levels and malformed service URLs."""
    # Act & Assert
    with pytest.raises(ValidationError):
        Settings(log_level="VERBOSE")

    with pytest.raises(ValidationError):
        Settings(ollama_base_url="localhost:11434")


def test_get_settings_cache_can_be_cleared(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify lru_cache returns updated Settings after cache_clear."""
    # Arrange
    get_settings.cache_clear()
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    # Act
    loaded = get_settings()

    # Assert
    assert loaded.log_level == "WARNING"
    get_settings.cache_clear()
