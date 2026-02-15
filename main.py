from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.chatbot_logic.router import router as chat_router
import uvicorn
import os

app = FastAPI(title="Mysoft AI Chatbot")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Chat Router
app.include_router(chat_router, prefix="/api")

# Serve static files for UI
# Ensure the templates directory exists
os.makedirs("templates", exist_ok=True)
app.mount("/", StaticFiles(directory="templates", html=True), name="templates")

if __name__ == "__main__":
    uvicorn.run("main.py:app", host="0.0.0.0", port=8000, reload=True)
