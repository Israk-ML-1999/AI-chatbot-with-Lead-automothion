from fastapi import APIRouter, HTTPException
from app.chatbot_logic.chatbot_request import ChatRequest, ChatResponse
from app.chatbot_logic.llm_service import LLMService

router = APIRouter()
llm_service = LLMService()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Load history
        history = llm_service.load_history()
        
        # Generate response
        response_text = llm_service.generate_response(request.query, history)
        
        # Save history
        llm_service.save_history(request.query, response_text)
        
        return ChatResponse(
            response=response_text,
            history=llm_service.load_history()[-3:] # Return last 3 for UI if needed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh-data")
async def refresh_data():
    """Manually trigger data re-indexing from Excel."""
    from app.Dtat_scrip.ectraction_service import ExtractionService
    from app.database.database import VectorDBManager
    
    try:
        extractor = ExtractionService()
        docs = extractor.extract_data()
        
        if not docs:
            return {"status": "error", "message": "No data found in Excel file."}
            
        db_manager = VectorDBManager()
        db_manager.initialize_db(docs)
        
        return {"status": "success", "message": f"Successfully indexed {len(docs)} document chunks."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
