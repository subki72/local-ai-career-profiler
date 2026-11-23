"""Local LLM-powered CV parser enforcing structured Pydantic output."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from src.config import Settings, configure_logging, get_settings
from src.extractors.pdf_reader import extract_pdf_text

logger = logging.getLogger(__name__)

CV_EXTRACTION_TEMPLATE = """
You are an expert HR AI Assistant. Extract the candidate's profile strictly based on the provided CV text.
Do not invent, hallucinate, or guess information. Output ONLY a valid JSON object.

FORMAT INSTRUCTIONS:
{format_instructions}

RAW CV TEXT:
{cv_text}
""".strip()


class CandidateProfile(BaseModel):
    """Structured candidate summary extracted from a raw CV."""

    name: str = Field(
        description="Full name of the candidate. If not found, return 'Unknown'."
    )
    key_skills: list[str] = Field(
        description="List of core technical and soft skills extracted from the CV."
    )
    years_of_experience: int = Field(
        ge=0,
        description=(
            "Total years of professional experience. Put 0 if fresh graduate. "
            "If not explicitly stated, infer from work history dates."
        ),
    )
    summary: str = Field(
        description="A brief 1-2 sentence summary of the candidate's core strengths."
    )


def _create_default_parser_llm(settings: Settings) -> Any:
    """Lazily instantiate a deterministic local Ollama JSON model."""
    try:
        from langchain_ollama import OllamaLLM
    except ImportError as exc:
        raise RuntimeError(
            "langchain-ollama is required for live LLM parsing. "
            "Install dependencies via 'pip install -r requirements.txt'."
        ) from exc

    # temperature=0.0 and format="json" maximize schema adherence during extraction.
    return OllamaLLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.0,
        format="json",
    )


def parse_cv_with_local_ai(
    clean_cv_text: str,
    llm: Any | None = None,
    settings: Settings | None = None,
) -> CandidateProfile:
    """Extract a validated CandidateProfile from cleaned CV text using local AI.

    Args:
        clean_cv_text: Cleaned CV text produced by the PDF extractor.
        llm: Optional injected LLM client exposing an ``invoke(prompt)`` method.
        settings: Optional runtime configuration override.

    Returns:
        Structured CandidateProfile validated against Pydantic constraints.

    Raises:
        ValueError: If clean_cv_text is empty or whitespace only.
        RuntimeError: If the Ollama dependency is missing when no llm is injected.
    """
    if not clean_cv_text or not clean_cv_text.strip():
        raise ValueError("Cleaned CV text must not be empty.")

    active_settings = settings or get_settings()
    active_llm = llm if llm is not None else _create_default_parser_llm(active_settings)
    parser = PydanticOutputParser(pydantic_object=CandidateProfile)

    prompt = PromptTemplate(
        template=CV_EXTRACTION_TEMPLATE,
        input_variables=["cv_text"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    formatted_prompt = prompt.format(cv_text=clean_cv_text)
    logger.info("Sending CV text (%d chars) to local LLM for profile extraction.", len(clean_cv_text))
    raw_response = active_llm.invoke(formatted_prompt)

    try:
        parsed_data = parser.parse(raw_response)
    except Exception:
        logger.error("Failed to parse LLM output into CandidateProfile schema.")
        raise

    logger.info("Successfully extracted CandidateProfile with %d skill(s).", len(parsed_data.key_skills))
    return parsed_data


if __name__ == "__main__":
    configure_logging()
    sample_file = Path("data/raw_cv/sample_cv.pdf")
    try:
        clean_text = extract_pdf_text(sample_file)
        profile = parse_cv_with_local_ai(clean_text)
        logger.info("Extracted CandidateProfile:\n%s", profile.model_dump_json(indent=2))
    except Exception:
        logger.exception("Failed to parse sample CV '%s'.", sample_file)
