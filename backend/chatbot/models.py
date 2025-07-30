"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class TechnicianBase(BaseModel):
    username: str
    email: str
    full_name: str
    department: Optional[str] = None
    role: str = "technician"


class TechnicianCreate(TechnicianBase):
    password: str


class TechnicianResponse(TechnicianBase):
    id: int
    is_active: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class TicketBase(BaseModel):
    title: str
    description: str
    status: str = "open"
    priority: str = "medium"
    category: Optional[str] = None


class TicketCreate(TicketBase):
    pass


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    resolution_notes: Optional[str] = None
    customer_satisfaction: Optional[int] = Field(None, ge=1, le=5)


class TicketResponse(BaseModel):
    ticketnumber: str  # Changed to match your TICKETS table
    title: str
    description: Optional[str] = None
    tickettype: Optional[str] = None
    ticketcategory: Optional[str] = None
    issuetype: Optional[str] = None
    subissuetype: Optional[str] = None
    duedatetime: Optional[str] = None  # Changed to string to match database format
    resolution: Optional[str] = None
    userid: Optional[str] = None
    useremail: Optional[str] = None
    technicianemail: Optional[str] = None  # Changed to match your data
    phonenumber: Optional[str] = None

    @validator('duedatetime', pre=True)
    def parse_duedatetime(cls, v):
        """Parse duedatetime string to datetime if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            # Try different date formats
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                try:
                    return datetime.strptime(v, fmt).isoformat()
                except ValueError:
                    continue
            # If no format matches, return as is
            return v
        return v

    class Config:
        from_attributes = True


class KnowledgeBaseResponse(BaseModel):
    id: int
    title: str
    content: str
    category: Optional[str]
    tags: Optional[str]
    created_at: Optional[datetime]
    view_count: int
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    message_type: str = "bot"
    timestamp: datetime
    session_id: str
    related_tickets: Optional[List[TicketResponse]] = None
    knowledge_base_articles: Optional[List[KnowledgeBaseResponse]] = None


class TicketSummaryRequest(BaseModel):
    ticket_id: int


class TicketSummaryResponse(BaseModel):
    ticket_id: int
    summary: str
    key_points: List[str]
    suggested_actions: List[str]
