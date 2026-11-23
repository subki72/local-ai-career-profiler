"""Offline unit tests for JobSchema Pydantic validation rules."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from src.recommenders.job_schema import JobSchema


def test_job_schema_accepts_valid_payload() -> None:
    """Verify a valid JobSchema instance trims inputs and serializes cleanly."""
    # Arrange & Act
    job = JobSchema(
        job_id=" TECH-001 ",
        job_title=" AI Engineer ",
        required_skills=[" Python ", "LangChain", "RAG"],
        min_experience_years=2,
        short_description=" Build production RAG pipelines. ",
    )

    # Assert
    assert job.job_id == "TECH-001"
    assert job.job_title == "AI Engineer"
    assert job.required_skills == ["Python", "LangChain", "RAG"]
    assert job.min_experience_years == 2
    assert job.short_description == "Build production RAG pipelines."
    assert '"job_id":"TECH-001"' in job.model_dump_json()


def test_job_schema_accepts_zero_years_for_entry_level() -> None:
    """Verify fresh graduate roles with 0 years minimum experience are valid."""
    # Act
    job = JobSchema(
        job_id="J-ENTRY",
        job_title="Junior ML Engineer",
        required_skills=["Python"],
        min_experience_years=0,
        short_description="Assist with model evaluation.",
    )

    # Assert
    assert job.min_experience_years == 0


def test_job_schema_rejects_negative_experience() -> None:
    """Reject negative minimum experience years."""
    # Act & Assert
    with pytest.raises(ValidationError):
        JobSchema(
            job_id="J001",
            job_title="Data Scientist",
            required_skills=["Python"],
            min_experience_years=-1,
            short_description="Analyze data.",
        )


@pytest.mark.parametrize(
    "field_name,invalid_value",
    [
        ("job_id", "   "),
        ("job_title", ""),
        ("short_description", "   "),
        ("required_skills", []),
        ("required_skills", [" ", ""]),
    ],
)
def test_job_schema_rejects_blank_or_empty_fields(
    field_name: str,
    invalid_value: object,
) -> None:
    """Reject blank required text fields and empty skill lists."""
    # Arrange
    payload: dict[str, object] = {
        "job_id": "J002",
        "job_title": "Data Engineer",
        "required_skills": ["Python", "SQL"],
        "min_experience_years": 2,
        "short_description": "Maintain ETL pipelines.",
    }
    payload[field_name] = invalid_value

    # Act & Assert
    with pytest.raises(ValidationError):
        JobSchema(**payload)


def test_job_schema_rejects_missing_required_fields() -> None:
    """Reject incomplete dictionaries missing mandatory schema attributes."""
    # Act & Assert
    with pytest.raises(ValidationError):
        JobSchema(job_id="J003", job_title="Analyst")  # type: ignore[call-arg]
