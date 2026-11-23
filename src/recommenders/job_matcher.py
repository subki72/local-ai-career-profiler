"""Dual-engine AI job matchmaker using ChromaDB RAG and local Ollama reasoning."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.prompts import PromptTemplate

from src.analyzers.cv_parser import CandidateProfile
from src.config import Settings, configure_logging, get_settings
from src.recommenders.job_schema import JobSchema

logger = logging.getLogger(__name__)

ATS_REASONING_TEMPLATE = """
You are an expert Career Advisor. Analyze the candidate and the matched job.
Write a short, professional paragraph explaining why this candidate fits this job based on their skills.

CANDIDATE PROFILE:
Name: {name}
Skills: {skills}
Experience: {experience} years
Summary: {summary}

MATCHED JOB:
{job_data}

Provide the reasoning clearly and concisely.
""".strip()

OPEN_MARKET_PROFILING_TEMPLATE = """
You are an elite Tech Career Consultant. Analyze the following candidate profile.
Provide a comprehensive career profiling, including:
1. Core Strengths & Market Value
2. Potential Weaknesses or Areas for Growth
3. Top 3 Ideal Job Titles in the current open market, with a brief reason for each.

CANDIDATE PROFILE:
Name: {name}
Skills: {skills}
Experience: {experience} years
Summary: {summary}

Provide the output in a clean, professional format. Do not invent any skills.
""".strip()


class AIJobMatchmaker:
    """Matches candidates to internal roles via ChromaDB or generates open-market advice."""

    def __init__(
        self,
        settings: Settings | None = None,
        embeddings: Any | None = None,
        vector_db: Any | None = None,
        llm: Any | None = None,
    ) -> None:
        """Initialize the matchmaker with injectable components or local defaults.

        Args:
            settings: Optional Settings override for model and storage paths.
            embeddings: Optional embedding model instance for dependency injection.
            vector_db: Optional vector database instance for dependency injection.
            llm: Optional LLM instance exposing an ``invoke(prompt)`` method.
        """
        self.settings = settings or get_settings()
        self.embeddings = embeddings
        self.vector_db = (
            vector_db if vector_db is not None else self._build_default_vector_db()
        )
        self.llm = llm if llm is not None else self._build_default_llm()

    def _build_default_vector_db(self) -> Any:
        """Lazily initialize HuggingFace embeddings and persistent ChromaDB storage."""
        try:
            from langchain_chroma import Chroma
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError as exc:
            raise RuntimeError(
                "langchain-chroma and langchain-huggingface are required for live vector matching."
            ) from exc

        if self.embeddings is None:
            self.embeddings = HuggingFaceEmbeddings(model_name=self.settings.embedding_model)

        db_path = Path(self.settings.chroma_db_dir).resolve()
        db_path.mkdir(parents=True, exist_ok=True)
        logger.info("Connecting to persistent ChromaDB at '%s'.", db_path)
        return Chroma(
            embedding_function=self.embeddings,
            persist_directory=str(db_path),
        )

    def _build_default_llm(self) -> Any:
        """Lazily initialize the local Ollama model for career reasoning."""
        try:
            from langchain_ollama import OllamaLLM
        except ImportError as exc:
            raise RuntimeError(
                "langchain-ollama is required for live career reasoning."
            ) from exc

        return OllamaLLM(
            model=self.settings.ollama_model,
            base_url=self.settings.ollama_base_url,
            temperature=0.2,
        )

    def populate_job_database(self, jobs: list[JobSchema]) -> int:
        """Index validated JobSchema records into the vector database.

        Args:
            jobs: List of validated job openings to store.

        Returns:
            Number of job records inserted.
        """
        if not jobs:
            logger.warning("No jobs supplied to populate_job_database; skipping insert.")
            return 0

        texts: list[str] = []
        metadatas: list[dict[str, str]] = []
        for job in jobs:
            searchable_text = (
                f"Title: {job.job_title}. "
                f"Skills: {', '.join(job.required_skills)}. "
                f"Desc: {job.short_description}"
            )
            texts.append(searchable_text)
            metadatas.append({"job_id": job.job_id, "job_title": job.job_title})

        self.vector_db.add_texts(texts=texts, metadatas=metadatas)
        logger.info("Successfully loaded %d job(s) into the vector database.", len(jobs))
        return len(jobs)

    def find_best_match_and_reason(self, candidate: CandidateProfile) -> str:
        """Search ChromaDB for the closest job role and explain candidate fit.

        Args:
            candidate: Structured candidate profile extracted from a CV.

        Returns:
            Formatted recommendation containing role title and LLM reasoning.
        """
        search_query = f"Skills: {', '.join(candidate.key_skills)}. Summary: {candidate.summary}"
        results = self.vector_db.similarity_search(search_query, k=1)
        if not results:
            logger.warning("Vector search returned no job matches.")
            return "No suitable jobs found in the database."

        best_job_text = results[0].page_content
        best_job_title = results[0].metadata.get("job_title", "Unknown Role")

        prompt = PromptTemplate(
            template=ATS_REASONING_TEMPLATE,
            input_variables=["name", "skills", "experience", "summary", "job_data"],
        )
        formatted_prompt = prompt.format(
            name=candidate.name,
            skills=", ".join(candidate.key_skills),
            experience=candidate.years_of_experience,
            summary=candidate.summary,
            job_data=best_job_text,
        )

        logger.info("Found best job match '%s'; generating LLM reasoning.", best_job_title)
        reasoning = self.llm.invoke(formatted_prompt)
        return f"RECOMMENDED ROLE: {best_job_title}\n\nREASONING:\n{reasoning}"

    def open_market_profiling(self, candidate: CandidateProfile) -> str:
        """Profile a candidate directly with the LLM without querying the internal DB.

        Args:
            candidate: Structured candidate profile extracted from a CV.

        Returns:
            Comprehensive open-market career analysis text.
        """
        prompt = PromptTemplate(
            template=OPEN_MARKET_PROFILING_TEMPLATE,
            input_variables=["name", "skills", "experience", "summary"],
        )
        formatted_prompt = prompt.format(
            name=candidate.name,
            skills=", ".join(candidate.key_skills),
            experience=candidate.years_of_experience,
            summary=candidate.summary,
        )

        logger.info("Generating open-market career profile via local LLM.")
        return str(self.llm.invoke(formatted_prompt))


if __name__ == "__main__":
    configure_logging()
    demo_job = JobSchema(
        job_id="J001",
        job_title="AI Engineer",
        required_skills=["Python", "LangChain"],
        min_experience_years=0,
        short_description="Build AI systems.",
    )
    matchmaker = AIJobMatchmaker()
    matchmaker.populate_job_database([demo_job])
    logger.info("Matchmaker engine is ready.")
