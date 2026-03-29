import fitz  # PyMuPDF library
import re    # Regex for advanced text manipulation

def clean_extracted_text(raw_text: str) -> str:
    """
    Cleans raw PDF text by fixing broken lines and normalizing spaces.
    
    Args:
        raw_text (str): The messy text straight from the PDF.
        
    Returns:
        str: Cleaned, continuous text ready for NLP processing.
    """
    # 1. Fix hyphenated words split across lines (e.g., "end-to-\nend" -> "end-to-end")
    text = re.sub(r'-\n+', '-', raw_text)
    
    # 2. Join broken sentences (replace single newlines with a space)
    # We keep double newlines (\n\n) because they usually mean a real new paragraph
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    
    # 3. Remove any excessive multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_pdf_text(file_path: str) -> str:
    """
    Opens a PDF file, extracts raw text, and cleans it.
    """
    full_text = ""
    document = fitz.open(file_path)
    
    for page_num in range(len(document)):
        page = document[page_num]
        full_text += page.get_text()
        
    # Clean the text before sending it out
    return clean_extracted_text(full_text)

# === Testing Area ===
if __name__ == "__main__":
    test_file = "data/raw_cv/sample_cv.pdf" 
    
    try:
        result = extract_pdf_text(test_file)
        print("Success! Cleaned text ready for AI:\n")
        print(result[:500]) 
    except Exception as e:
        print(f"Error occurred: {e}")