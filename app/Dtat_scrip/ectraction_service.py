import pandas as pd
import re
from typing import List, Dict
import sys
import os

# Add the project root to sys.path for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import config

class ExtractionService:
    def __init__(self, xlsx_path: str = config.EXCEL_DATA_PATH):
        self.xlsx_path = xlsx_path

    def clean_text(self, text: str) -> str:
        """Clean HTML tags, entities, and excessive whitespace."""
        if not isinstance(text, str):
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove HTML entities
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
        text = text.replace('&amp;', '&').replace('&lt;', '<')
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove copyright/footer noise
        text = re.sub(r'Copyright.*?\d{4}.*?Ltd\.', '', text, flags=re.IGNORECASE)
        text = re.sub(r'All rights reserved.*', '', text, flags=re.IGNORECASE)
        
        return text

    def chunk_text(self, text: str, chunk_size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP) -> List[str]:
        """Split text into smaller chunks."""
        if not text:
            return []
            
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sent_len = len(sentence)
            if current_length + sent_len > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Overlap logic: keep some previous content
                current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
                current_chunk.append(sentence)
                current_length = sum(len(s) for s in current_chunk) + len(current_chunk) - 1
            else:
                current_chunk.append(sentence)
                current_length += sent_len + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return [c.strip() for c in chunks if c.strip()]

    def extract_data(self) -> List[Dict]:
        """Load Excel and return cleaned, chunked data with metadata."""
        try:
            # Check if file exists
            if not os.path.exists(self.xlsx_path):
                print(f"Error: Excel file not found at {self.xlsx_path}")
                return []
                
            df = pd.read_excel(self.xlsx_path)
            documents = []
            
            for _, row in df.iterrows():
                url = row.get('url', '')
                path_val = row.get('Path', '') # User's file has 'Path' with capital P
                content = row.get('content', '')
                
                cleaned_content = self.clean_text(str(content))
                if len(cleaned_content) < 50:
                    continue
                    
                chunks = self.chunk_text(cleaned_content)
                
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "text": chunk,
                        "metadata": {
                            "source": str(url),
                            "path": str(path_val),
                            "chunk_index": i
                        }
                    })
            return documents
        except Exception as e:
            print(f"Error extracting data: {e}")
            return []

if __name__ == "__main__":
    service = ExtractionService()
    docs = service.extract_data()
    print(f"Extracted {len(docs)} chunks.")
    if docs:
        print(f"Sample chunk: {docs[0]['text'][:100]}...")
