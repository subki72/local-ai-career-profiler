import sys
import os
from pydantic import BaseModel, Field
from typing import List
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import PydanticOutputParser

# Ensure Python can find our extractors module when run from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.extractors.pdf_reader import extract_pdf_text

# 1. The Blank Form (Strict Contract)
class CandidateProfile(BaseModel):
    name: str = Field(
        description="Full name of the candidate. If not found, return 'Unknown'"
    )
    key_skills: List[str] = Field(
        description="List of core technical and soft skills extracted from the CV"
    )
    years_of_experience: int = Field(
        description="Total years of professional experience. Put 0 if fresh graduate. If not explicitly stated, infer from work history dates."
    )
    summary: str = Field(
        description="A brief 1-2 sentence summary of the candidate's core strengths"
    )

# 2. The Integration Function
def parse_cv_with_local_ai(clean_cv_text: str) -> CandidateProfile:
    """
    Sends the cleaned CV text to the local LLM (Ollama) to extract structured JSON data.
    """
    # Initialize the local AI model (The Chef)
    # temperature=0.0 makes the AI strict and deterministic (less creative, more accurate)
    # format="json" forces the local model to only output JSON data
    llm = OllamaLLM(model="llama3", temperature=0.0, format="json")
    
    # Set up the strict JSON enforcer
    parser = PydanticOutputParser(pydantic_object=CandidateProfile)
    
    # Write the prompt manual
    template = """
    You are an expert HR AI Assistant. Extract the candidate's profile strictly based on the provided CV text.
    Do not invent, hallucinate, or guess information. Output ONLY a valid JSON object.
    
    FORMAT INSTRUCTIONS:
    {format_instructions}
    
    RAW CV TEXT:
    {cv_text}
    """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["cv_text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # Create the pipeline (Chain): Prompt -> LLM
    chain = prompt | llm
    
    # Execute the chain
    raw_response = chain.invoke({"cv_text": clean_cv_text})
    
    # Parse the raw string response into our Pydantic schema
    try:
        parsed_data = parser.parse(raw_response)
        return parsed_data
    except Exception as e:
        print(f"Failed to parse LLM output. Raw output was: \n{raw_response}")
        raise e

# === Testing Area ===
if __name__ == "__main__":
    # Point this to the exact same file we used in Phase 1 to ensure consistency in testing
    test_file = "data/raw_cv/sample_cv.pdf" 
    
    print("1. Extracting and cleaning text from PDF...")
    try:
        clean_text = extract_pdf_text(test_file)
        print("   -> Extraction successful!")
        
        print("\n2. Sending text to Local AI... (Please wait, Llama 3 is reading...)")
        result = parse_cv_with_local_ai(clean_text)
        
        print("\n========================================")
        print("SUCCESS! AI Extracted Profile (JSON):")
        print("========================================")
        print(result.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"\nSystem Error: {e}")