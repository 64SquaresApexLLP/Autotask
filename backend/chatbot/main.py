"""Main FastAPI application for the Technician Chatbot."""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db, init_database, TechnicianDummyData
from app.auth import authenticate_technician, create_access_token, get_current_technician, verify_token
from app.models import (
    LoginRequest, TokenResponse, ChatMessage, ChatResponse,
    TicketResponse, TicketSummaryRequest, TicketSummaryResponse, KnowledgeBaseResponse
)
from app.services.ticket_service import TicketService
from app.services.chatbot_service import ConversationalChatbotService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.llm_service import LLMService
# Removed unused services - using only existing tables

# Global LLM service instance - initialized once at startup
global_llm_service = None

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app will be created below with lifespan context manager

# Security
security = HTTPBearer()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.technician_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, technician_id: int):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.technician_connections[technician_id] = websocket
        logger.info(f"Technician {technician_id} connected to WebSocket")
    
    def disconnect(self, websocket: WebSocket, technician_id: int):
        self.active_connections.remove(websocket)
        if technician_id in self.technician_connections:
            del self.technician_connections[technician_id]
        logger.info(f"Technician {technician_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: str, technician_id: int):
        if technician_id in self.technician_connections:
            websocket = self.technician_connections[technician_id]
            await websocket.send_text(message)

manager = ConnectionManager()


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global global_llm_service

    # Startup
    try:
        # Initialize database
        init_database()

        # Initialize LLM service ONCE at startup (with graceful fallback)
        try:
            global_llm_service = LLMService()
            logger.info(f"LLM service initialized - Cortex available: {global_llm_service.cortex_available}")
        except Exception as llm_error:
            logger.warning(f"LLM service initialization failed, creating fallback service: {llm_error}")
            # Create a minimal LLM service that will use fallbacks
            global_llm_service = LLMService()

        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        # Don't raise - allow app to start even if some services fail
        logger.warning("Application starting with limited functionality")

    yield  # Application runs here

    # Shutdown
    try:
        if global_llm_service:
            global_llm_service.close_connection()
            logger.info("LLM service connections closed")
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Update the FastAPI app initialization
app = FastAPI(
    title="Technician Chatbot API",
    description="AI-powered chatbot for IT technicians",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint to verify application status."""
    try:
        # Check if LLM service is available
        llm_status = "available" if global_llm_service and global_llm_service.cortex_available else "fallback"

        # Check database connectivity by trying to create a session
        db_status = "connected"
        try:
            # Try to create a database session to test connectivity
            from app.database import SessionLocal
            test_db = SessionLocal()
            test_db.execute("SELECT 1")
            test_db.close()
        except Exception as db_error:
            logger.warning(f"Database health check failed: {db_error}")
            if "temporarily locked" in str(db_error).lower() or "250001" in str(db_error):
                db_status = "locked"
            else:
                db_status = "disconnected"

        overall_status = "healthy" if db_status == "connected" else "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "llm_service": llm_status,
                "database": db_status,
                "chatbot": "ready"
            },
            "features": {
                "conversational_chat": True,
                "ticket_caching": True,
                "similar_tickets": True,
                "ai_resolutions": llm_status == "available"
            },
            "message": "Snowflake account is temporarily locked" if db_status == "locked" else None
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "llm_service": "unknown",
                "database": "error",
                "chatbot": "degraded"
            }
        }


@app.post("/auth/login", response_model=TokenResponse)
async def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate technician and return access token."""
    try:
        technician = authenticate_technician(db, login_request.username, login_request.password)
        if not technician:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login
        try:
            technician.last_login = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to update last login time: {e}")
            # Continue with login even if we can't update last login

        # Create access token
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": technician.email, "technician_id": technician.technician_id}, expires_delta=access_token_expires
        )

        logger.info(f"Technician {technician.username} logged in successfully")

        return TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 401 Unauthorized)
        raise
    except Exception as e:
        logger.error(f"Database connection error during login: {e}")
        # Check if it's a Snowflake account lock error
        if "temporarily locked" in str(e).lower() or "250001" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is temporarily unavailable. The Snowflake account appears to be locked. Please contact your administrator or try again later.",
                headers={"Retry-After": "300"}  # Suggest retry after 5 minutes
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection error. Please try again later or contact support."
            )


@app.get("/tickets/my", response_model=List[TicketResponse])
async def get_my_tickets(
    limit: int = 10,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Get tickets assigned to the current technician."""
    ticket_service = TicketService(db)
    tickets = ticket_service.get_recent_assigned_tickets(current_technician.email, limit)
    return [TicketResponse.from_orm(ticket) for ticket in tickets]


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific ticket."""
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse.from_orm(ticket)


@app.get("/tickets/search", response_model=List[TicketResponse])
async def search_tickets(
    q: str,
    limit: int = 20,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Search tickets by query string."""
    ticket_service = TicketService(db)
    tickets = ticket_service.search_tickets(q, current_technician.email, limit=limit)
    return [TicketResponse.from_orm(ticket) for ticket in tickets]


# Knowledge Base endpoints for FAQ functionality
@app.get("/knowledge/search", response_model=List[KnowledgeBaseResponse])
async def search_knowledge_base(
    q: str,
    category: Optional[str] = None,
    limit: int = 10,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Search knowledge base articles."""
    kb_service = KnowledgeBaseService(db)
    articles = kb_service.search_articles(q, category=category, limit=limit)
    return [KnowledgeBaseResponse.from_orm(article) for article in articles]


@app.get("/knowledge/categories", response_model=List[str])
async def get_knowledge_categories(
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Get all knowledge base categories."""
    kb_service = KnowledgeBaseService(db)
    return kb_service.get_all_categories()


@app.get("/knowledge/popular", response_model=List[KnowledgeBaseResponse])
async def get_popular_articles(
    limit: int = 10,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Get most popular knowledge base articles."""
    kb_service = KnowledgeBaseService(db)
    articles = kb_service.get_popular_articles(limit)
    return [KnowledgeBaseResponse.from_orm(article) for article in articles]


@app.get("/knowledge/{article_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_article(
    article_id: int,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Get specific knowledge base article."""
    kb_service = KnowledgeBaseService(db)
    article = kb_service.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return KnowledgeBaseResponse.from_orm(article)


@app.post("/chat", response_model=ChatResponse)
async def chat_message(
    message: ChatMessage,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Process chat message and return conversational response with ticket caching."""
    try:
        chatbot_service = ConversationalChatbotService(db, global_llm_service)
        response = chatbot_service.process_message(
            message.message,
            current_technician,
            message.session_id
        )
        return response
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")

        # Check if it's a database connection error
        if "temporarily locked" in str(e).lower() or "250001" in str(e) or "DatabaseError" in str(type(e).__name__):
            error_message = "I'm sorry, the database service is temporarily unavailable. The system appears to be experiencing connectivity issues. Please try again in a few minutes or contact your administrator."
        else:
            error_message = "I'm sorry, I'm experiencing technical difficulties. Please try again later or contact support directly."

        # Return a fallback response
        return ChatResponse(
            response=error_message,
            message_type="error",
            timestamp=datetime.utcnow(),
            session_id=message.session_id or "error_session"
        )


@app.websocket("/ws/{technician_id}")
async def websocket_endpoint(websocket: WebSocket, technician_id: int, token: str):
    """WebSocket endpoint for real-time chat."""
    # Verify token
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Get database session
    db = next(get_db())
    try:
        # Verify technician
        technician = db.query(TechnicianDummyData).filter(
            TechnicianDummyData.technician_id == str(technician_id)
        ).first()
        
        if not technician:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        await manager.connect(websocket, technician_id)
        chatbot_service = ConversationalChatbotService(db, global_llm_service)

        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process message
                response = chatbot_service.process_message(
                    message_data.get("message", ""),
                    technician,
                    message_data.get("session_id")
                )
                
                # Send response
                await websocket.send_text(response.json())
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, technician_id)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        db.close()





# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the modern chat interface."""
    try:
        with open("static/modern_index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Chatbot Interface Not Found</h1><p>Please ensure static files are available.</p>",
            status_code=404
        )




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )
