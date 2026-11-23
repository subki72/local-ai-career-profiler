"""Strict Pydantic schema contract for job listings stored in ChromaDB."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, field_validator

from src.config import configure_logging

logger = logging.getLogger(__name__)


class JobSchema(BaseModel):
    """Validated data contract representing an internal job opening."""

    job_id: str = Field(..., min_length=1, description="Unique internal job identifier.")
    job_title: str = Field(..., min_length=1, description="Role title, e.g. 'Data Scientist'.")
    required_skills: list[str] = Field(
        ...,
        min_length=1,
        description="Non-empty list of core skills required for the role.",
    )
    min_experience_years: int = Field(
        ...,
        ge=0,
        description="Minimum years of professional experience required.",
    )
    short_description: str = Field(
        ...,
        min_length=1,
        description="Concise summary of core responsibilities.",
    )

    @field_validator("job_id", "job_title", "short_description")
    @classmethod
    def _validate_non_blank_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Text fields must not be blank.")
        return cleaned

    @field_validator("required_skills")
    @classmethod
    def _validate_required_skills(cls, skills: list[str]) -> list[str]:
        cleaned = [skill.strip() for skill in skills if skill and skill.strip()]
        if not cleaned:
            raise ValueError("required_skills must include at least one non-empty skill.")
        return cleaned


if __name__ == "__main__":
    configure_logging()
    sample_job = JobSchema(
        job_id="TECH-001",
        job_title="AI Engineer",
        required_skills=["Python", "LangChain", "NLP"],
        min_experience_years=2,
        short_description="Build an AI agent for CV analysis.",
    )
    logger.info("Validated JobSchema payload:\n%s", sample_job.model_dump_json(indent=2))
