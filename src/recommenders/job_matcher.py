import sys
import os
import json
from typing import List, Dict

# LangChain & AI tools
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

# Ensure Python can find our previous modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.analyzers.cv_parser import CandidateProfile, parse_cv_with_local_ai
from src.extractors.pdf_reader import extract_pdf_text
from src.recommenders.job_schema import JobSchema

class AIJobMatchmaker:
    def __init__(self):
        """
        Initializes the Matchmaker with a local embedding model, 
        a persistent vector database (Chroma), and our local LLM (Llama 3).
        """
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Define the path where the real database will be physically stored
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/chroma_db'))
        
        # Setup the Vector Database to PERSIST data to the hard drive
        self.vector_db = Chroma(
            embedding_function=self.embeddings,
            persist_directory=db_path
        )
        
        self.llm = OllamaLLM(model="llama3", temperature=0.2)
        
    def populate_job_database(self, jobs: List[JobSchema]):
        """
        Fills the Vector DB with available jobs.
        """
        texts = []
        metadatas = []
        
        for job in jobs:
            # Combine title, skills, and description into one searchable paragraph
            searchable_text = f"Title: {job.job_title}. Skills: {', '.join(job.required_skills)}. Desc: {job.short_description}"
            texts.append(searchable_text)
            metadatas.append({"job_id": job.job_id, "job_title": job.job_title})
            
        # Add everything to ChromaDB
        self.vector_db.add_texts(texts=texts, metadatas=metadatas)
        print(f"[SYSTEM] Successfully loaded {len(jobs)} jobs into the Vector Database.")

    def find_best_match_and_reason(self, candidate: CandidateProfile) -> str:
        """
        Searches the DB for the best job fit, then asks the LLM to explain WHY.
        """
        # 1. Convert candidate profile into a search query
        search_query = f"Skills: {', '.join(candidate.key_skills)}. Summary: {candidate.summary}"
        
        # 2. Search the DB for the top 1 closest coordinate (Best Job Match)
        results = self.vector_db.similarity_search(search_query, k=1)
        
        if not results:
            return "No suitable jobs found in the database."
            
        best_job_text = results[0].page_content
        best_job_title = results[0].metadata["job_title"]
        
        # 3. Ask Llama 3 to explain the reasoning
        prompt_template = """
        You are an expert Career Advisor. Analyze the candidate and the matched job.
        Write a short, professional paragraph explaining exactly WHY this candidate is a great fit for this job based on their skills.
        
        CANDIDATE PROFILE:
        Name: {name}
        Skills: {skills}
        Experience: {experience} years
        Summary: {summary}
        
        MATCHED JOB:
        {job_data}
        
        Provide the reasoning clearly and concisely.
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["name", "skills", "experience", "summary", "job_data"]
        )
        
        chain = prompt | self.llm
        
        print(f"\n[SYSTEM] Found best match: {best_job_title}. Generating reasoning...")
        reasoning = chain.invoke({
            "name": candidate.name,
            "skills": ", ".join(candidate.key_skills),
            "experience": candidate.years_of_experience,
            "summary": candidate.summary,
            "job_data": best_job_text
        })
        
        return f"RECOMMENDED ROLE: {best_job_title}\n\nREASONING:\n{reasoning}"

    def open_market_profiling(self, candidate: CandidateProfile) -> str:
        """
        Bypasses the vector database and asks the LLM to freely profile the candidate
        and suggest the top 3 ideal roles in the current tech market.
        """
        prompt_template = """
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
        """
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["name", "skills", "experience", "summary"]
        )
        chain = prompt | self.llm
        
        print(f"\n[SYSTEM] Generating Open Market Profile for {candidate.name}...")
        profiling_result = chain.invoke({
            "name": candidate.name,
            "skills": ", ".join(candidate.key_skills),
            "experience": candidate.years_of_experience,
            "summary": candidate.summary
        })
        return profiling_result

# === Testing Area ===
if __name__ == "__main__":
    job_1 = JobSchema(
        job_id="J001", job_title="AI Engineer", required_skills=["Python", "LangChain"],
        min_experience_years=0, short_description="Build AI systems."
    )
    matchmaker = AIJobMatchmaker()
    matchmaker.populate_job_database([job_1])
    print("[SYSTEM] Matchmaker engine is ready.")