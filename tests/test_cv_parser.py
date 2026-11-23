"""Offline unit tests for CandidateProfile schema and local AI CV parsing."""

from __future__ import annotations

import json

from pydantic import ValidationError
import pytest

from src.analyzers.cv_parser import CandidateProfile, parse_cv_with_local_ai


class _StubLLM:
    """Deterministic LLM stub returning a preconfigured string response."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.last_prompt: str = ""

    def invoke(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._response


def test_candidate_profile_rejects_negative_experience() -> None:
    """Verify CandidateProfile enforces non-negative years of experience."""
    # Act & Assert
    with pytest.raises(ValidationError):
        CandidateProfile(
            name="Alex",
            key_skills=["Python"],
            years_of_experience=-2,
            summary="Backend developer.",
        )


def test_parse_cv_with_local_ai_returns_validated_profile() -> None:
    """Parse structured JSON output from an injected LLM stub into CandidateProfile."""
    # Arrange
    payload = json.dumps(
        {
            "name": "Nadia Pratama",
            "key_skills": ["Python", "FastAPI", "RAG"],
            "years_of_experience": 3,
            "summary": "AI engineer specializing in local LLM microservices.",
        }
    )
    stub_llm = _StubLLM(payload)

    # Act
    profile = parse_cv_with_local_ai("Nadia Pratama - Python & FastAPI engineer", llm=stub_llm)

    # Assert
    assert profile.name == "Nadia Pratama"
    assert profile.key_skills == ["Python", "FastAPI", "RAG"]
    assert profile.years_of_experience == 3
    assert "Nadia Pratama" in stub_llm.last_prompt


def test_parse_cv_with_local_ai_rejects_empty_text() -> None:
    """Raise ValueError upfront when blank CV text is provided."""
    # Arrange
    stub_llm = _StubLLM("{}")

    # Act & Assert
    with pytest.raises(ValueError, match="must not be empty"):
        parse_cv_with_local_ai("   ", llm=stub_llm)


def test_parse_cv_with_local_ai_propagates_invalid_json_error() -> None:
    """Raise an explicit parsing error when the LLM returns malformed output."""
    # Arrange
    stub_llm = _StubLLM("not-valid-json")

    # Act & Assert
    with pytest.raises(Exception):
        parse_cv_with_local_ai("Experienced Python engineer", llm=stub_llm)
