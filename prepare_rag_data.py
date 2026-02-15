"""
RAG Data Preparation Pipeline for Mysoft Heaven Chatbot
This script prepares Excel data for vector database ingestion
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict
import re

class RAGDataPreprocessor:
    """
    Prepares company data for RAG knowledge base
    
    Your current data structure:
    - 114 rows of company information
    - Columns: url, path, content
    - Content: HTML-embedded text with company details
    """
    
    def __init__(self, xlsx_path: str):
        self.df = pd.read_excel(xlsx_path, sheet_name=0)
        self.processed_docs = []
    
    # ============================================================================
    # STEP 1: COLUMN SELECTION & CLEANUP
    # ============================================================================
    
    def analyze_columns(self):
        """Analyze which columns to keep and which to drop"""
        print("COLUMN ANALYSIS FOR RAG:")
        print("-" * 80)
        
        analysis = {
            "url": {
                "keep": False,
                "reason": "Index/reference only - not needed for embedding",
                "usage": "Can store as metadata for source tracking"
            },
            "path": {
                "keep": True,
                "reason": "Useful for categorizing content (e.g., /service/... vs /about/...)",
                "usage": "Store as metadata: page category, page type"
            },
            "content": {
                "keep": True,
                "reason": "PRIMARY field - actual company information to embed",
                "usage": "Main text for vector embedding - clean and chunk this"
            }
        }
        
        print("\nKEEP Columns:")
        for col, info in analysis.items():
            if info["keep"]:
                print(f"  ✓ {col}: {info['reason']}")
                print(f"    └─ Usage: {info['usage']}")
        
        print("\nDROP Columns:")
        for col, info in analysis.items():
            if not info["keep"]:
                print(f"  ✗ {col}: {info['reason']}")
        
        return analysis
    
    # ============================================================================
    # STEP 2: TEXT CLEANING
    # ============================================================================
    
    def clean_content(self, text: str) -> str:
        """
        Clean HTML and unwanted artifacts from content
        
        Issues to handle:
        - HTML tags and entities
        - Duplicate spaces/newlines
        - Navigation menu text
        - Footer/header noise
        - Copyright info duplication
        """
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove HTML entities
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
        text = text.replace('&amp;', '&').replace('&lt;', '<')
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove copyright/footer noise
        text = re.sub(r'Copyright.*?\d{4}.*?Ltd\.', '', text, flags=re.IGNORECASE)
        text = re.sub(r'All rights reserved.*', '', text, flags=re.IGNORECASE)
        
        # Remove repeated words (common in nav)
        text = re.sub(r'(\w+\s+){2,}', lambda m: m.group(0)[:m.end()-len(m.group(1))], text)
        
        return text.strip()
    
    # ============================================================================
    # STEP 3: METADATA EXTRACTION
    # ============================================================================
    
    def extract_metadata(self, row_idx: int, path: str) -> Dict:
        """
        Extract and structure metadata for RAG retrieval
        
        Metadata helps filter searches and provide context
        """
        
        # Categorize by path
        if 'service' in path:
            category = 'Service'
        elif 'product' in path:
            category = 'Product'
        elif 'client' in path:
            category = 'Client'
        elif 'portfolio' in path:
            category = 'Portfolio'
        elif 'about' in path or 'company' in path:
            category = 'About Company'
        else:
            category = 'General'
        
        metadata = {
            'source_path': path,
            'category': category,
            'row_index': row_idx,
            'data_type': 'company_info'
        }
        
        return metadata
    
    # ============================================================================
    # STEP 4: CHUNKING STRATEGY (CRITICAL FOR RAG!)
    # ============================================================================
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """
        Split long content into smaller chunks for better embeddings
        
        WHY CHUNKING IS IMPORTANT:
        - Vector DBs work better with focused, contextual chunks (~300-500 tokens)
        - Too long: loses relevance, wastes compute
        - Too short: loses context
        - Overlap: maintains continuity between chunks
        
        RECOMMENDED SETTINGS:
        - chunk_size: 400-600 characters (~100-150 tokens)
        - overlap: 100-150 characters (20-25% of chunk)
        """
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sent_len = len(sentence)
            
            if current_length + sent_len > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                # Start new chunk with overlap
                overlap_text = ' '.join(current_chunk[-2:]) if len(current_chunk) > 1 else ''
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_length = len(overlap_text) + sent_len
            else:
                current_chunk.append(sentence)
                current_length += sent_len + 1
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return [c.strip() for c in chunks if c.strip()]
    
    # ============================================================================
    # STEP 5: FORMAT CONVERSION
    # ============================================================================
    
    def convert_to_json_format(self) -> List[Dict]:
        """
        Convert XLSX to JSON format optimized for vector DB ingestion
        
        RECOMMENDED FORMAT FOR CHROMA/PINECONE:
        {
            "id": "unique_identifier",
            "text": "chunk content",
            "metadata": {
                "source": "company info",
                "category": "Service",
                "page_path": "/service/...",
                "chunk_index": 0
            }
        }
        """
        
        documents = []
        doc_id = 0
        
        for idx, row in self.df.iterrows():
            path = row['path']
            raw_content = row['content']
            url = row['url']
            
            # Step 1: Clean
            cleaned_content = self.clean_content(raw_content)
            
            # Step 2: Skip if too short
            if len(cleaned_content) < 50:
                continue
            
            # Step 3: Extract metadata
            metadata = self.extract_metadata(idx, path)
            
            # Step 4: Chunk
            chunks = self.chunk_text(cleaned_content)
            
            # Step 5: Create documents
            for chunk_idx, chunk in enumerate(chunks):
                doc = {
                    "id": f"mysoftheaven_doc_{doc_id}",
                    "text": chunk,
                    "metadata": {
                        **metadata,
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks),
                        "url": url[:100]  # First 100 chars of URL
                    }
                }
                documents.append(doc)
                doc_id += 1
        
        return documents
    
    # ============================================================================
    # STEP 6: QUALITY ASSURANCE
    # ============================================================================
    
    def quality_check(self, documents: List[Dict]) -> Dict:
        """Validate prepared data"""
        
        analysis = {
            "total_documents": len(documents),
            "avg_text_length": sum(len(d["text"]) for d in documents) / len(documents) if documents else 0,
            "min_text_length": min(len(d["text"]) for d in documents) if documents else 0,
            "max_text_length": max(len(d["text"]) for d in documents) if documents else 0,
            "categories": {}
        }
        
        for doc in documents:
            cat = doc["metadata"]["category"]
            analysis["categories"][cat] = analysis["categories"].get(cat, 0) + 1
        
        return analysis
    
    # ============================================================================
    # STEP 7: SAVE FOR VECTOR DB
    # ============================================================================
    
    def save_for_vectordb(self, documents: List[Dict], output_path: str = "data/rag_documents.json"):
        """Save in optimal format for vector database ingestion"""
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {len(documents)} documents to {output_file}")
        return output_file
    
    # Main execution
    def process(self):
        """Run full pipeline"""
        
        print("\n" + "="*80)
        print("RAG DATA PREPARATION PIPELINE")
        print("="*80 + "\n")
        
        # Step 1: Analyze
        self.analyze_columns()
        
        print("\n" + "-"*80)
        print("STEP 2: Converting to JSON format with chunking...")
        print("-"*80 + "\n")
        
        documents = self.convert_to_json_format()
        
        # Step 2: Quality check
        print("\nQUALITY ANALYSIS:")
        print("-"*80)
        analysis = self.quality_check(documents)
        print(f"✓ Total documents: {analysis['total_documents']}")
        print(f"✓ Avg text length: {analysis['avg_text_length']:.0f} chars")
        print(f"✓ Min: {analysis['min_text_length']}, Max: {analysis['max_text_length']}")
        print(f"✓ By category: {analysis['categories']}")
        
        # Step 3: Save
        print("\n" + "-"*80)
        self.save_for_vectordb(documents)
        
        return documents


# ============================================================================
# RECOMMENDED NEXT STEPS
# ============================================================================
"""
AFTER PREPARING DATA:

1. VECTOR EMBEDDING (Choose one):
   - OpenAI text-embedding-3-small (BEST: cheap, accurate)
   - Hugging Face all-MiniLM-L6-v2 (FREE: local, fast)
   - Cohere embedding API (good balance)

2. VECTOR DATABASE:
   - **Chroma** (recommended): pip install chromadb
   - **FAISS**: pip install faiss-cpu
   - **Pinecone**: cloud-based, scalable

3. RAG APPLICATION:
   - LangChain for orchestration
   - FastAPI for API
   - Streamlit for UI

CHUNK SIZE GUIDE:
- 300-400 chars: Dense, specific information
- 400-600 chars: General Q&A (RECOMMENDED)
- 600-1000 chars: Document sections
- >1000 chars: Avoid (loses focus in semantic search)
"""


if __name__ == "__main__":
    preprocessor = RAGDataPreprocessor('Rag_data/mysoftheaven data.xlsx')
    documents = preprocessor.process()
    
    # Show sample
    print("\n" + "="*80)
    print("SAMPLE PREPARED DOCUMENT:")
    print("="*80)
    if documents:
        sample = documents[0]
        print(f"\nID: {sample['id']}")
        print(f"\nText Preview:\n{sample['text'][:300]}...")
        print(f"\nMetadata: {json.dumps(sample['metadata'], indent=2)}")
