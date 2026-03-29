import sys
import os

# Ensure Python can find our core modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from src.recommenders.job_matcher import AIJobMatchmaker
from src.recommenders.job_schema import JobSchema

def seed_database():
    """
    This script acts as the HR Admin panel. 
    It injects jobs directly into the persistent Vector Database.
    Run this only when you want to add new jobs to the system.
    """
    print("[ADMIN] Connecting to Persistent Database...")
    matchmaker = AIJobMatchmaker()
    
    # 1. Prepare the Data
    jobs_to_insert = [
        JobSchema(
            job_id="J001", job_title="Frontend Developer", required_skills=["React", "CSS", "HTML", "TypeScript"],
            min_experience_years=1, short_description="Build UI for web apps."
        ),
        JobSchema(
            job_id="J002", job_title="Data Scientist", required_skills=["Python", "SQL", "Machine Learning", "Data Visualization", "Pandas"],
            min_experience_years=1, short_description="Analyze business data, build predictive models, and create dashboards."
        ),
        JobSchema(
            job_id="J003", job_title="AI & Machine Learning Engineer", required_skills=["Python", "PyTorch", "TensorFlow", "RAG", "LLM", "AWS"],
            min_experience_years=0, short_description="Architect Generative AI systems, deploy ML models via FastAPI, and build NLP/Vision pipelines."
        ),
        JobSchema(
            job_id="J004", job_title="Cybersecurity Analyst", required_skills=["Network Security", "Penetration Testing", "Security Fundamentals"],
            min_experience_years=1, short_description="Protect company infrastructure and analyze system vulnerabilities."
        ),
        JobSchema(
            job_id="J005", job_title="Data Engineer", required_skills=["Python", "SQL", "ETL", "PostgreSQL", "Data Pipelines"],
            min_experience_years=2, short_description="Build and maintain robust data architecture and vector databases."
        )
    ]
    
    # 2. Inject into the Database
    print(f"[ADMIN] Injecting {len(jobs_to_insert)} jobs into the system...")
    matchmaker.populate_job_database(jobs_to_insert)
    print("[ADMIN] Database Seeding Complete! The data is now permanently saved to disk.")

if __name__ == "__main__":
    seed_database()