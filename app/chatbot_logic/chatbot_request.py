from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str
    history: Optional[List[dict]] = None
