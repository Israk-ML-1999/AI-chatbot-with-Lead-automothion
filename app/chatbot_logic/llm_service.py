import os
import json
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.database.database import VectorDBManager
from config import config

class LLMService:
    def __init__(self):
        self.db_manager = VectorDBManager()
        self.api_key = config.OPENAI_API_KEY
        
        # Initialize LLM (Fallback to a basic message if no API key)
        if self.api_key:
            self.llm = ChatOpenAI(openai_api_key=self.api_key, model_name="gpt-4-turbo")
        else:
            self.llm = None
            print("Warning: No OpenAI API key found. RAG responses will be simulated or limited.")

    def get_context(self, query: str) -> tuple[str, float]:
        """Retrieve relevant context from vector database with confidence score."""
        results = self.db_manager.search(query, k=3)
        
        if not results:
            return "", 0.0
        
        # Extract documents and scores
        documents = []
        scores = []
        for doc, score in results:
            documents.append(doc.page_content)
            # Convert distance to similarity (ChromaDB returns distance, lower is better)
            similarity = 1.0 - score
            scores.append(similarity)
        
        # Calculate average confidence
        avg_confidence = sum(scores) / len(scores) if scores else 0.0
        context = "\n\n".join(documents)
        
        return context, avg_confidence

    def format_history(self, history: List[Dict]) -> List:
        """Convert JSON history to LangChain message format."""
        messages = []
        # We only need the last 3 pairs (6 messages) as per requirement
        for entry in history[-3:]:
            messages.append(HumanMessage(content=entry.get("user query", "")))
            messages.append(AIMessage(content=entry.get("AI_response", "")))
        return messages
    
    def is_conversational_query(self, query: str) -> tuple[bool, str]:
        """Check if query is a basic conversational question and provide appropriate response."""
        query_lower = query.lower().strip()
        
        # Greetings
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if query_lower in greetings or query_lower.startswith(tuple(greetings)):
            return True, "Hello! I'm the Mysoft Heaven AI Assistant. I can help you with information about Mysoft Heaven (BD) Ltd.'s services, products, government projects, and company details. What would you like to know?"
        
        # Who/What are you questions
        identity_questions = [
            "who are you", "what are you", "are you a bot", "are you ai", "who r u", "what r u"
        ]
        if any(q in query_lower for q in identity_questions):
            return True, "I am an AI assistant specifically designed to help with questions about Mysoft Heaven (BD) Ltd. I can provide information about their services, products, government projects, certifications, and company background. How can I assist you today?"
        
        # How are you
        if "how are you" in query_lower or "how r u" in query_lower:
            return True, "I'm functioning well, thank you! I'm here to help you with any questions about Mysoft Heaven (BD) Ltd. What would you like to know about our company?"
        
        # Thank you
        if query_lower in ["thank you", "thanks", "thank u", "thx"]:
            return True, "You're welcome! Feel free to ask if you have any other questions about Mysoft Heaven (BD) Ltd."
        
        return False, ""

    def generate_response(self, user_query: str, history: List[Dict]) -> str:
        """Generate a response based on retrieved context and history."""
        
        # Check for conversational queries first
        is_conversational, conversational_response = self.is_conversational_query(user_query)
        if is_conversational:
            print(f"\n{'='*60}")
            print(f"QUERY: {user_query}")
            print(f"TYPE: CONVERSATIONAL (no vector search needed)")
            print(f"{'='*60}\n")
            return conversational_response
        
        # Proceed with normal RAG pipeline
        context, confidence = self.get_context(user_query)
        
        # Log similarity score for monitoring (no threshold enforcement)
        print(f"\n{'='*60}")
        print(f"QUERY: {user_query}")
        print(f"SIMILARITY SCORE: {confidence:.2%}")
        print(f"CONTEXT FOUND: {'Yes' if context else 'No'}")
        print(f"{'='*60}\n")
        
        # If no context found at all (empty results)
        if not context:
            print(f"⚠️ No similar documents found in knowledge base")
            return (
                "I'm sorry, I don't have information about that in my knowledge base. "
                "I can only provide answers about Mysoft Heaven (BD) Ltd.'s services, "
                "products, projects, and company information."
            )

        # Always proceed with response generation (no confidence filtering)
        system_prompt = (
            "You are a helpful AI assistant for Mysoft Heaven (BD) Ltd. "
            "You must answer questions strictly based on the provided context."
            "you  frist detect hte language of user query and then answer in that language.You also bangla language assistant.If user ask in bangla then you must answer in bangla otherwise you must answer in english."
            "If the answer is not in the context, politely state that you don't know and "
            "refuse to answer unrelated or out-of-scope questions.aways try to answer in a concise and clear manner and under 200 words. "
            "Do not use external knowledge.\n\n"
            f"Context: {context}"
        )

        langchain_history = self.format_history(history)
        
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(langchain_history)
        messages.append(HumanMessage(content=user_query))

        if self.llm:
            try:
                response = self.llm.invoke(messages)
                return response.content
            except Exception as e:
                return f"Error generating response: {str(e)}"
        else:
            # Fallback for demonstration when no API key
            return f"[Simulated Response based on Context]: {context[:200]}..."

    def save_history(self, user_query: str, ai_response: str):
        """Save chat turn to local JSON file."""
        history_path = config.CHAT_HISTORY_PATH
        history = []
        
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append({
            "user query": user_query,
            "AI_response": ai_response
        })
        
        # Keep only last 10 turns to keep file small
        history = history[-10:]
        
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def load_history(self) -> List[Dict]:
        """Load chat history from local JSON file."""
        history_path = config.CHAT_HISTORY_PATH
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
