from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import os
import shutil
import sys

# Add the project root to sys.path for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import config

class VectorDBManager:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL_NAME)
        self.persist_directory = config.DATABASE_PATH
        self.vector_db = None

    def initialize_db(self, documents=None):
        """Create or load the vector database."""
        if documents:
            # If we have documents, we recreate the DB
            if os.path.exists(self.persist_directory):
                try:
                    shutil.rmtree(self.persist_directory)
                except Exception as e:
                    print(f"Warning: Could not delete existing DB directory: {e}")
            
            texts = [doc["text"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]
            
            self.vector_db = Chroma.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas,
                persist_directory=self.persist_directory
            )
            print(f"Database created with {len(texts)} chunks.")
        else:
            # Load existing DB
            if os.path.exists(self.persist_directory):
                self.vector_db = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
                print("Existing database loaded.")
            else:
                print("No existing database found.")

    def search(self, query: str, k: int = 3):
        """Search for relevant documents with similarity scores."""
        if not self.vector_db:
            self.initialize_db()
        
        if self.vector_db:
            # Get results with similarity scores (no filtering)
            results = self.vector_db.similarity_search_with_score(query, k=k)
            return results
        return []

if __name__ == "__main__":
    from app.Dtat_scrip.ectraction_service import ExtractionService
    
    # Simple test
    extractor = ExtractionService()
    docs = extractor.extract_data()
    
    if docs:
        db_manager = VectorDBManager()
        db_manager.initialize_db(docs)
        print("Vector DB initialized.")
        
        # Test search (now returns tuples of (doc, score))
        results = db_manager.search("What services does Mysoft Heaven provide?")
        for doc, score in results:
            print(f"- {doc.page_content[:100]}...")
    else:
        print("No documents found to initialize DB.")

