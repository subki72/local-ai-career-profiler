"""Offline unit tests for AIJobMatchmaker and database seeding logic."""

from __future__ import annotations

from dataclasses import dataclass

from seed_db import get_default_jobs, seed_database
from src.analyzers.cv_parser import CandidateProfile
from src.recommenders.job_matcher import AIJobMatchmaker
from src.recommenders.job_schema import JobSchema


@dataclass
class _FakeDocument:
    """Stub mimicking a LangChain Document returned by Chroma similarity search."""

    page_content: str
    metadata: dict[str, str]


class _FakeVectorDB:
    """In-memory stub replacing ChromaDB for fast offline unit testing."""

    def __init__(self, search_results: list[_FakeDocument] | None = None) -> None:
        self.added_texts: list[str] = []
        self.added_metadatas: list[dict[str, str]] = []
        self.search_results = search_results or []
        self.last_query: str = ""

    def add_texts(self, texts: list[str], metadatas: list[dict[str, str]]) -> None:
        self.added_texts.extend(texts)
        self.added_metadatas.extend(metadatas)

    def similarity_search(self, query: str, k: int = 1) -> list[_FakeDocument]:
        self.last_query = query
        return self.search_results[:k]


class _FakeLLM:
    """Stub replacing OllamaLLM for deterministic reasoning tests."""

    def __init__(self, output: str) -> None:
        self._output = output
        self.last_prompt: str = ""

    def invoke(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._output


def _sample_candidate() -> CandidateProfile:
    """Construct a reusable CandidateProfile fixture."""
    return CandidateProfile(
        name="Raka Wijaya",
        key_skills=["Python", "PyTorch", "FastAPI", "RAG"],
        years_of_experience=2,
        summary="Machine learning engineer focused on local RAG deployments.",
    )


def test_populate_job_database_indexes_formatted_records() -> None:
    """Verify job records are formatted into searchable text and metadata."""
    # Arrange
    fake_db = _FakeVectorDB()
    matchmaker = AIJobMatchmaker(vector_db=fake_db, llm=_FakeLLM("ok"))
    jobs = [
        JobSchema(
            job_id="J100",
            job_title="ML Engineer",
            required_skills=["Python", "PyTorch"],
            min_experience_years=1,
            short_description="Deploy ML pipelines.",
        )
    ]

    # Act
    inserted = matchmaker.populate_job_database(jobs)

    # Assert
    assert inserted == 1
    assert len(fake_db.added_texts) == 1
    assert "ML Engineer" in fake_db.added_texts[0]
    assert fake_db.added_metadatas == [{"job_id": "J100", "job_title": "ML Engineer"}]


def test_populate_job_database_handles_empty_list() -> None:
    """Return 0 without mutating the vector store when no jobs are provided."""
    # Arrange
    fake_db = _FakeVectorDB()
    matchmaker = AIJobMatchmaker(vector_db=fake_db, llm=_FakeLLM("ok"))

    # Act
    inserted = matchmaker.populate_job_database([])

    # Assert
    assert inserted == 0
    assert fake_db.added_texts == []


def test_find_best_match_and_reason_returns_formatted_recommendation() -> None:
    """Verify ATS matching formats the matched role and LLM reasoning cleanly."""
    # Arrange
    fake_doc = _FakeDocument(
        page_content="Title: AI Engineer. Skills: Python, RAG.",
        metadata={"job_id": "J003", "job_title": "AI Engineer"},
    )
    fake_db = _FakeVectorDB(search_results=[fake_doc])
    fake_llm = _FakeLLM("Strong alignment in Python and RAG architecture.")
    matchmaker = AIJobMatchmaker(vector_db=fake_db, llm=fake_llm)

    # Act
    output = matchmaker.find_best_match_and_reason(_sample_candidate())

    # Assert
    assert "RECOMMENDED ROLE: AI Engineer" in output
    assert "Strong alignment in Python and RAG architecture." in output
    assert "Python" in fake_db.last_query
    assert "Raka Wijaya" in fake_llm.last_prompt


def test_find_best_match_and_reason_handles_empty_database() -> None:
    """Return a clear message when vector similarity search yields no results."""
    # Arrange
    matchmaker = AIJobMatchmaker(vector_db=_FakeVectorDB([]), llm=_FakeLLM("unused"))

    # Act
    output = matchmaker.find_best_match_and_reason(_sample_candidate())

    # Assert
    assert output == "No suitable jobs found in the database."


def test_open_market_profiling_bypasses_vector_db() -> None:
    """Verify open-market profiling queries the LLM directly without DB lookup."""
    # Arrange
    fake_db = _FakeVectorDB()
    fake_llm = _FakeLLM("Top 3 roles: AI Engineer, MLOps Engineer, Backend Engineer.")
    matchmaker = AIJobMatchmaker(vector_db=fake_db, llm=fake_llm)

    # Act
    output = matchmaker.open_market_profiling(_sample_candidate())

    # Assert
    assert "AI Engineer" in output
    assert fake_db.last_query == ""
    assert "Raka Wijaya" in fake_llm.last_prompt


def test_seed_database_loads_all_default_jobs() -> None:
    """Verify seed_database injects all curated baseline jobs via injected matchmaker."""
    # Arrange
    fake_db = _FakeVectorDB()
    matchmaker = AIJobMatchmaker(vector_db=fake_db, llm=_FakeLLM("unused"))

    # Act
    count = seed_database(matchmaker=matchmaker)

    # Assert
    assert count == len(get_default_jobs()) == 5
    assert len(fake_db.added_texts) == 5
