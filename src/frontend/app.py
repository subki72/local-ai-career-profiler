"""Streamlit web frontend for CV Nexus dual-engine resume analysis."""

from __future__ import annotations

import logging
from typing import Any, Final

import requests
import streamlit as st

from src.config import Settings, configure_logging, get_settings

logger = logging.getLogger(__name__)

ATS_MODE_LABEL: Final[str] = "ATS Matcher (Find best fit in our internal Job Database)"
OPEN_MARKET_MODE_LABEL: Final[str] = "Open Market Profiler (Pure AI Career Consultant)"


def resolve_backend_endpoint(analysis_mode: str, api_base_url: str) -> str:
    """Resolve the target FastAPI endpoint URL for the selected analysis mode.

    Args:
        analysis_mode: Label selected in the Streamlit mode switcher.
        api_base_url: Base URL of the FastAPI backend.

    Returns:
        Full endpoint URL for CV upload.
    """
    base = api_base_url.rstrip("/")
    if "ATS Matcher" in analysis_mode:
        return f"{base}/api/v1/match-cv"
    return f"{base}/api/v1/profile-cv"


def extract_error_detail(response: requests.Response) -> str:
    """Safely extract an error message from a non-200 HTTP response."""
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("detail"):
            return str(payload["detail"])
    except ValueError:
        logger.warning("Received non-JSON error body with status %d.", response.status_code)
    return f"HTTP {response.status_code}"


def submit_cv_for_analysis(
    endpoint_url: str,
    filename: str,
    pdf_bytes: bytes,
    timeout_seconds: int,
) -> requests.Response:
    """Send the uploaded PDF resume to the FastAPI backend with an explicit timeout."""
    files = {"file": (filename, pdf_bytes, "application/pdf")}
    return requests.post(endpoint_url, files=files, timeout=timeout_seconds)


def _display_analysis_result(
    uploaded_file: Any,
    analysis_mode: str,
    settings: Settings,
) -> None:
    """Execute the backend call and render structured status feedback in Streamlit."""
    endpoint_url = resolve_backend_endpoint(analysis_mode, settings.api_base_url)
    try:
        response = submit_cv_for_analysis(
            endpoint_url=endpoint_url,
            filename=uploaded_file.name,
            pdf_bytes=uploaded_file.getvalue(),
            timeout_seconds=settings.request_timeout_seconds,
        )
    except requests.exceptions.Timeout:
        logger.error("Backend request timed out after %ds.", settings.request_timeout_seconds)
        st.error("Request timed out while waiting for local LLM inference. Please retry.")
        return
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to FastAPI backend at %s.", endpoint_url)
        st.error("Connection failed. Make sure the FastAPI backend is running.")
        return
    except requests.exceptions.RequestException:
        logger.exception("Unexpected HTTP client failure calling %s.", endpoint_url)
        st.error("An unexpected communication error occurred.")
        return

    if response.status_code == 200:
        data = response.json()
        mode_name = analysis_mode.split(" ")[0]
        st.success(f"Analysis Complete! (Mode: {mode_name})")
        st.subheader("AI Results")
        st.info(data["recommendation_result"])
        return

    detail = extract_error_detail(response)
    logger.warning("Backend rejected upload (%d): %s", response.status_code, detail)
    st.error(f"Backend Error: {detail}")


def render_app() -> None:
    """Configure and render the CV Nexus Streamlit user interface."""
    settings = get_settings()
    configure_logging(settings.log_level)

    st.set_page_config(page_title="CV Nexus AI", page_icon="CV", layout="centered")
    st.title("CV Nexus: Dual-Engine AI Profiler")
    st.markdown(
        "Upload your resume (PDF) and choose how our local AI analyzes your career path."
    )

    analysis_mode = st.radio(
        "Select AI Analysis Mode:",
        options=[ATS_MODE_LABEL, OPEN_MARKET_MODE_LABEL],
    )
    st.divider()

    uploaded_file = st.file_uploader("Upload your CV (PDF format only)", type=["pdf"])
    if uploaded_file is None:
        return

    if st.button("Analyze My CV", type="primary", use_container_width=True):
        with st.spinner("Local AI is analyzing your resume... Please wait."):
            _display_analysis_result(uploaded_file, analysis_mode, settings)


if __name__ == "__main__":
    render_app()
