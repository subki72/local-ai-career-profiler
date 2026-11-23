"""FastMCP server exposing CV Nexus analysis tools over stdio transport."""

from __future__ import annotations

import logging
from pathlib import Path
import threading
from typing import Final

from mcp.server.fastmcp import FastMCP

from src.analyzers.cv_parser import parse_cv_with_local_ai
from src.config import configure_logging
from src.extractors.pdf_reader import extract_pdf_text
from src.recommenders.job_matcher import AIJobMatchmaker
from src.recommenders.job_schema import JobSchema

logger = logging.getLogger(__name__)

mcp = FastMCP("CV_Nexus_Engine")

DEFAULT_MCP_JOBS: Final[tuple[JobSchema, ...]] = (
    JobSchema(
        job_id="J001",
        job_title="Frontend Developer",
        required_skills=["React", "CSS", "HTML"],
        min_experience_years=1,
        short_description="Build UI for web apps.",
    ),
    JobSchema(
        job_id="J002",
        job_title="Data Scientist",
        required_skills=["Python", "SQL", "Machine Learning", "Power BI"],
        min_experience_years=0,
        short_description="Analyze data, build predictive models, and create dashboards.",
    ),
)

_mcp_lock = threading.Lock()
_mcp_matchmaker: AIJobMatchmaker | None = None


def get_mcp_matchmaker() -> AIJobMatchmaker:
    """Lazily initialize and seed the matchmaker used by MCP tool invocations."""
    global _mcp_matchmaker
    if _mcp_matchmaker is not None:
        return _mcp_matchmaker

    with _mcp_lock:
        if _mcp_matchmaker is None:
            logger.info("Initializing AIJobMatchmaker for CV Nexus MCP server.")
            instance = AIJobMatchmaker()
            instance.populate_job_database(list(DEFAULT_MCP_JOBS))
            _mcp_matchmaker = instance
    return _mcp_matchmaker


def _validate_pdf_path(pdf_file_path: str) -> Path:
    """Validate that the requested MCP input path refers to an existing PDF file."""
    if not pdf_file_path or not pdf_file_path.strip():
        raise ValueError("PDF file path must not be empty.")

    resolved = Path(pdf_file_path).resolve()
    if resolved.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")
    if not resolved.is_file():
        raise FileNotFoundError(f"PDF file does not exist: {resolved.name}")
    return resolved


@mcp.tool()
def process_and_match_cv(pdf_file_path: str) -> str:
    """Read a candidate CV PDF, parse their profile with local AI, and recommend a job fit.

    Args:
        pdf_file_path: Absolute or relative path to the candidate PDF file.

    Returns:
        Formatted job recommendation with reasoning, or a safe error message.
    """
    try:
        validated_path = _validate_pdf_path(pdf_file_path)
        clean_text = extract_pdf_text(validated_path)
        candidate_profile = parse_cv_with_local_ai(clean_text)
        matchmaker = get_mcp_matchmaker()
        return matchmaker.find_best_match_and_reason(candidate_profile)
    except (ValueError, FileNotFoundError) as exc:
        logger.warning("Rejected MCP CV request: %s", exc)
        return f"Invalid CV input: {exc}"
    except Exception:
        logger.exception("Internal error while processing CV via MCP.")
        return "Internal error while processing the requested CV."


if __name__ == "__main__":
    configure_logging()
    logger.info("CV Nexus MCP Server is starting over stdio transport.")
    mcp.run()
