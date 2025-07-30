"""Chatbot API Router for integration with Autotask backend."""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db, init_database, TechnicianDummyData
from .auth import authenticate_technician, create_access_token, get_current_technician, verify_token
from .models import (
    LoginRequest, TokenResponse, ChatMessage, ChatResponse,
    TicketResponse, TicketSummaryRequest, TicketSummaryResponse
)
from .services.ticket_service import TicketService
from .services.chatbot_service import ConversationalChatbotService
from .services.llm_service import LLMService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Global LLM service instance - initialized once at startup
global_llm_service = None

# Initialize database and services
def initialize_chatbot_services():
    """Initialize chatbot services."""
    global global_llm_service
    
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

        logger.info("Chatbot services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize chatbot services: {e}")
        logger.warning("Chatbot starting with limited functionality")

# Initialize services
initialize_chatbot_services()

# Create router
router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint to verify application status."""
    try:
        # Check if LLM service is available
        llm_status = "available" if global_llm_service and global_llm_service.cortex_available else "fallback"

        # Check database connectivity by trying to create a session
        db_status = "connected"
        try:
            # Try to create a database session to test connectivity
            from .database import SessionLocal
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

@router.post("/auth/login", response_model=TokenResponse)
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
            data={"sub": str(technician.id), "username": technician.username},
            expires_delta=access_token_expires
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60  # Convert to seconds
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.get("/tickets/my", response_model=List[TicketResponse])
async def get_my_tickets(
    limit: int = 10,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Get tickets assigned to the current technician."""
    ticket_service = TicketService(db)
    tickets = ticket_service.get_recent_assigned_tickets(current_technician.email, limit=limit)
    return tickets

@router.get("/tickets/search", response_model=List[TicketResponse])
async def search_tickets(
    q: str,
    limit: int = 20,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Search tickets by query string."""
    ticket_service = TicketService(db)
    # Search tickets assigned to the current technician first, then broader search if needed
    tickets = ticket_service.search_tickets(q, technician_email=current_technician.email, limit=limit)
    return tickets

@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Get a specific ticket by ID."""
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.get("/tickets/debug/search")
async def debug_search(
    q: str = "email",
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Debug endpoint to see what tickets contain the search term."""
    ticket_service = TicketService(db)
    ticket_service.debug_search_sample(q)
    return {"message": f"Debug search completed for '{q}'. Check server logs for details."}

@router.get("/tickets/debug/similar/{ticket_number}")
async def debug_similar_search(
    ticket_number: str,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Debug endpoint to see what happens during similar ticket search."""
    try:
        ticket_service = TicketService(db)
        
        # First, find the ticket by ticket number
        original_ticket = ticket_service.get_ticket_by_number(ticket_number)
        if not original_ticket:
            return {"error": f"Ticket {ticket_number} not found"}
        
        # Show ticket details
        ticket_info = {
            "ticket_number": original_ticket.ticketnumber,
            "title": original_ticket.title,
            "description": original_ticket.description,
            "issue_type": original_ticket.issuetype,
            "sub_issue_type": original_ticket.subissuetype,
            "category": original_ticket.ticketcategory
        }
        
        # Extract the issue description
        issue_description = original_ticket.description or original_ticket.title or original_ticket.issuetype or ""
        
        # Test the search
        similar_tickets = ticket_service.find_similar_tickets_by_issue(issue_description, limit=5)
        
        return {
            "original_ticket": ticket_info,
            "issue_description": issue_description,
            "similar_tickets_found": len(similar_tickets),
            "similar_tickets": [
                {
                    "ticket_number": ticket.ticketnumber,
                    "title": ticket.title,
                    "issue_type": ticket.issuetype
                } for ticket in similar_tickets
            ]
        }
        
    except Exception as e:
        return {"error": f"Debug error: {str(e)}"}

@router.get("/tickets/similar/{ticket_number}")
async def find_similar_tickets_by_number(
    ticket_number: str,
    limit: int = 10,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Find similar tickets based on a ticket number."""
    try:
        ticket_service = TicketService(db)
        
        # First, find the ticket by ticket number
        original_ticket = ticket_service.get_ticket_by_number(ticket_number)
        if not original_ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_number} not found")
        
        # Extract the issue description from the original ticket
        issue_description = original_ticket.description or original_ticket.title or original_ticket.issuetype or ""
        
        if not issue_description.strip():
            raise HTTPException(
                status_code=400, 
                detail=f"Ticket {ticket_number} has no description to search for similar tickets"
            )
        
        logger.info(f"Searching for similar tickets based on: {issue_description}")
        
        # Find similar tickets based on the issue description
        similar_tickets = ticket_service.find_similar_tickets_by_issue(issue_description, limit=limit)
        
        # Remove the original ticket from the results if it's included
        similar_tickets = [ticket for ticket in similar_tickets if ticket.ticketnumber != ticket_number]
        
        logger.info(f"Found {len(similar_tickets)} similar tickets for ticket {ticket_number}")
        
        # If no similar tickets found, try a broader search
        if len(similar_tickets) == 0:
            logger.info("No similar tickets found, trying broader search...")
            # Try searching with just the issue type
            if original_ticket.issuetype:
                similar_tickets = ticket_service.find_similar_tickets_by_issue(original_ticket.issuetype, limit=limit)
                similar_tickets = [ticket for ticket in similar_tickets if ticket.ticketnumber != ticket_number]
                logger.info(f"Broader search found {len(similar_tickets)} tickets using issue type: {original_ticket.issuetype}")
        
        return {
            "original_ticket": {
                "ticket_number": original_ticket.ticketnumber,
                "title": original_ticket.title,
                "description": original_ticket.description,
                "issue_type": original_ticket.issuetype
            },
            "similar_tickets": similar_tickets,
            "search_based_on": issue_description[:100] + "..." if len(issue_description) > 100 else issue_description,
            "total_found": len(similar_tickets)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar tickets for {ticket_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error finding similar tickets"
        )



@router.post("/chat", response_model=ChatResponse)
async def chat_message(
    message: ChatMessage,
    current_technician: TechnicianDummyData = Depends(get_current_technician),
    db: Session = Depends(get_db)
):
    """Process a chat message and return AI response."""
    try:
        chatbot_service = ConversationalChatbotService(
            db=db,
            llm_service=global_llm_service
        )
        
        response = chatbot_service.process_message(
            message.message,
            current_technician,
            message.session_id or ""
        )
        
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat message"
        )

@router.websocket("/ws/{technician_id}")
async def websocket_endpoint(websocket: WebSocket, technician_id: int, token: str):
    """WebSocket endpoint for real-time chat."""
    try:
        # Verify token
        if not verify_token(token):
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        await manager.connect(websocket, technician_id)
        
        try:
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process message through chatbot
                if global_llm_service:
                    # For WebSocket, we need to get the technician from the database
                    from .database import SessionLocal
                    ws_db = SessionLocal()
                    try:
                        technician = ws_db.query(TechnicianDummyData).filter(
                            TechnicianDummyData.technician_id == str(technician_id)
                        ).first()
                        
                        if technician:
                            chatbot_service = ConversationalChatbotService(
                                db=ws_db,
                                llm_service=global_llm_service
                            )
                            
                            response = chatbot_service.process_message(
                                message_data.get("message", ""),
                                technician,
                                message_data.get("session_id", "")
                            )
                        else:
                            response = "Technician not found"
                    finally:
                        ws_db.close()
                    
                    # Send response back
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "chat_response",
                            "message": response,
                            "timestamp": datetime.utcnow().isoformat()
                        }),
                        technician_id
                    )
                else:
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error",
                            "message": "Chatbot service unavailable"
                        }),
                        technician_id
                    )
                    
        except WebSocketDisconnect:
            manager.disconnect(websocket, technician_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket, technician_id)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=4000, reason="Connection error")

@router.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main chatbot interface."""
    try:
        with open("backend/chatbot/static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Chatbot Interface</h1><p>Static files not found.</p>")
    except Exception as e:
        logger.error(f"Error serving static files: {e}")
        return HTMLResponse(content="<h1>Chatbot Interface</h1><p>Error loading interface.</p>") 