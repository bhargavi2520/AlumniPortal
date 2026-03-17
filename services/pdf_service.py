import os
import fitz  # PyMuPDF

MAX_PAGES_TO_EXTRACT = 5
MAX_FILE_SIZE_MB = 5

def extract_text_safely(pdf_path: str) -> str:
    """
    Safely extracts text from a PDF, enforcing size and page limits to
    protect against malformed/massive files.
    Returns empty string on failure.
    """
    if not os.path.exists(pdf_path):
        return ""

    try:
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return ""

        text = ""
        # fitz handles encrypted/corrupted files reasonably well with exceptions
        with fitz.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                if i >= MAX_PAGES_TO_EXTRACT:
                    break
                
                # Simple text extraction
                page_text = page.get_text()
                if page_text:
                    text += page_text + "\n"

        return text.strip()

    except Exception as e:
        # In a real system, print/log this exception
        print(f"[pdf_service] Failed to extract text from {pdf_path}: {e}")
        return ""
