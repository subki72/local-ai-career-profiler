from pydantic import BaseModel
from typing import List

# This represents the strict contract for a Job requirement
class JobSchema(BaseModel):
    job_id: str
    job_title: str                  # e.g., "Data Scientist"
    required_skills: List[str]      # e.g., ["Python", "SQL", "Machine Learning"]
    min_experience_years: int
    short_description: str

# === Testing Area ===
if __name__ == "__main__":
    # A valid job entry adhering to the schema contract
    job_1 = JobSchema(
        job_id="TECH-001",
        job_title="AI Engineer",
        required_skills=["Python", "LangChain", "NLP"],
        min_experience_years=2,
        short_description="Build an AI agent for CV analysis."
    )
    
    print("Job data is valid and ready for the database!")
    print(job_1.model_dump_json(indent=2))