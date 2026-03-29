import os
import shutil
import sys
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

# Ensure Python can find our core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.extractors.pdf_reader import extract_pdf_text
from src.analyzers.cv_parser import parse_cv_with_local_ai
from src.recommenders.job_matcher import AIJobMatchmaker
from src.recommenders.job_schema import JobSchema

# 1. Initialize the Router (The Receptionist's Desk)
router = APIRouter()

# 2. Initialize AI Models (Booting up the Brain)
print("[API] Booting up AI Matchmaker for API routes...")
matchmaker = AIJobMatchmaker()

# 3. Define the Response Format
class MatchResponse(BaseModel):
    filename: str
    recommendation_result: str

# 4. Create the POST Endpoint for ATS Matching
@router.post("/match-cv", response_model=MatchResponse)
async def upload_and_match_cv(file: UploadFile = File(...)):
    """
    Endpoint to receive a CV (PDF), process it through the local LLM pipeline, 
    and return the best job recommendation from the internal database.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    temp_dir = "data/processed"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        clean_text = extract_pdf_text(temp_path)
        candidate_profile = parse_cv_with_local_ai(clean_text)
        final_recommendation = matchmaker.find_best_match_and_reason(candidate_profile)
        
        return MatchResponse(
            filename=file.filename,
            recommendation_result=final_recommendation
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Processing Error: {str(e)}")
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# 5. Create the NEW POST Endpoint for Open Market Profiling
@router.post("/profile-cv", response_model=MatchResponse)
async def upload_and_profile_cv(file: UploadFile = File(...)):
    """
    Endpoint for Open Market Career Profiling (Bypasses the Vector Database).
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    temp_dir = "data/processed"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        clean_text = extract_pdf_text(temp_path)
        candidate_profile = parse_cv_with_local_ai(clean_text)
        profiling_result = matchmaker.open_market_profiling(candidate_profile)
        
        return MatchResponse(
            filename=file.filename,
            recommendation_result=profiling_result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Processing Error: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)