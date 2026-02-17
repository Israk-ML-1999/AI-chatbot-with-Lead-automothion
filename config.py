import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PROJECT_NAME = "Mysoft AI Chatbot"
    DATABASE_PATH = "data/chroma_db"
    EXCEL_DATA_PATH = "data/mysoftheaven data.xlsx"
    CHAT_HISTORY_PATH = "app/database/chat_data.json"
    
    # Embedding Settings
    EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # LLM Settings (Using a free model or OpenAI if key is present)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    
    CHUNK_SIZE = 400
    CHUNK_OVERLAP = 100

config = Config()
