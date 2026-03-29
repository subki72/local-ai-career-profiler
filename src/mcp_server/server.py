import sys
import os
from mcp.server.fastmcp import FastMCP

# Ensure Python can find our core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.extractors.pdf_reader import extract_pdf_text
from src.analyzers.cv_parser import parse_cv_with_local_ai
from src.recommenders.job_matcher import AIJobMatchmaker
from src.recommenders.job_schema import JobSchema

# 1. Initialize the MCP Server (The Universal Hub)
# This name will appear when other AI agents connect to your tool
mcp = FastMCP("CV_Nexus_Engine")

# 2. Prepare the AI Matchmaker in the background
print("[SYSTEM] Booting up MCP Server and initializing AI models...")
matchmaker = AIJobMatchmaker()

# Pre-load our dummy job database (In production, this connects to a real DB like PostgreSQL)
job_1 = JobSchema(
    job_id="J001", job_title="Frontend Developer", required_skills=["React", "CSS", "HTML"],
    min_experience_years=1, short_description="Build UI for web apps."
)
job_2 = JobSchema(
    job_id="J002", job_title="Data Scientist", required_skills=["Python", "SQL", "Machine Learning", "Power BI"],
    min_experience_years=0, short_description="Analyze data, build predictive models, and create dashboards."
)
matchmaker.populate_job_database([job_1, job_2])

# 3. Define the Tool (This is what exposes your Python code to the outside world)
@mcp.tool()
def process_and_match_cv(pdf_file_path: str) -> str:
    """
    Reads a candidate's CV (PDF), extracts their technical profile using Local AI, 
    and recommends the best job fit from the database with detailed reasoning.
    
    Args:
        pdf_file_path: The absolute or relative path to the PDF file.
        
    Returns:
        A formatted string containing the AI's recommendation and reasoning.
    """
    try:
        # Step A: Extract
        clean_text = extract_pdf_text(pdf_file_path)
        
        # Step B: Parse
        candidate_profile = parse_cv_with_local_ai(clean_text)
        
        # Step C: Match & Reason
        final_recommendation = matchmaker.find_best_match_and_reason(candidate_profile)
        
        return final_recommendation
        
    except Exception as e:
        return f"Error processing CV at {pdf_file_path}: {str(e)}"

# === Server Execution ===
if __name__ == "__main__":
    print("[SYSTEM] CV Nexus MCP Server is running! Ready to accept connections.")
    # Run the server using Standard Input/Output (stdio) which is the standard for MCP
    mcp.run()