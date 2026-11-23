"""Database seeding utility for populating ChromaDB with default tech job openings."""

from __future__ import annotations

import logging

from src.config import configure_logging
from src.recommenders.job_matcher import AIJobMatchmaker
from src.recommenders.job_schema import JobSchema

logger = logging.getLogger(__name__)


def get_default_jobs() -> list[JobSchema]:
    """Return the curated baseline list of sample job openings."""
    return [
        JobSchema(
            job_id="J001",
            job_title="Frontend Developer",
            required_skills=["React", "CSS", "HTML", "TypeScript"],
            min_experience_years=1,
            short_description="Build UI for web apps.",
        ),
        JobSchema(
            job_id="J002",
            job_title="Data Scientist",
            required_skills=[
                "Python",
                "SQL",
                "Machine Learning",
                "Data Visualization",
                "Pandas",
            ],
            min_experience_years=1,
            short_description=(
                "Analyze business data, build predictive models, and create dashboards."
            ),
        ),
        JobSchema(
            job_id="J003",
            job_title="AI & Machine Learning Engineer",
            required_skills=["Python", "PyTorch", "TensorFlow", "RAG", "LLM", "AWS"],
            min_experience_years=0,
            short_description=(
                "Architect Generative AI systems, deploy ML models via FastAPI, "
                "and build NLP/Vision pipelines."
            ),
        ),
        JobSchema(
            job_id="J004",
            job_title="Cybersecurity Analyst",
            required_skills=[
                "Network Security",
                "Penetration Testing",
                "Security Fundamentals",
            ],
            min_experience_years=1,
            short_description=(
                "Protect company infrastructure and analyze system vulnerabilities."
            ),
        ),
        JobSchema(
            job_id="J005",
            job_title="Data Engineer",
            required_skills=["Python", "SQL", "ETL", "PostgreSQL", "Data Pipelines"],
            min_experience_years=2,
            short_description=(
                "Build and maintain robust data architecture and vector databases."
            ),
        ),
    ]


def seed_database(matchmaker: AIJobMatchmaker | None = None) -> int:
    """Populate the persistent vector database with baseline job records.

    Args:
        matchmaker: Optional AIJobMatchmaker instance for dependency injection.

    Returns:
        Number of jobs indexed into the vector database.
    """
    logger.info("Connecting to persistent vector database for job seeding.")
    active_matchmaker = matchmaker if matchmaker is not None else AIJobMatchmaker()
    jobs_to_insert = get_default_jobs()

    logger.info("Injecting %d default job(s) into ChromaDB.", len(jobs_to_insert))
    inserted_count = active_matchmaker.populate_job_database(jobs_to_insert)
    logger.info("Database seeding complete (%d job(s) persisted).", inserted_count)
    return inserted_count


if __name__ == "__main__":
    configure_logging()
    seed_database()
