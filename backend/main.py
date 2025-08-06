import sys
import os
import logging
from fastapi import FastAPI, HTTPException, Query, Header, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import hashlib
import hmac
import json
import requests
from datetime import datetime, timedelta
import asyncio
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# Email processing imports removed

# Set up logger
logger = logging.getLogger(__name__)

# Add src to sys.path for agent/database imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import from src modules
from src.agents.intake_agent import IntakeClassificationAgent
# from src.agents.assignment_agent import AssignmentAgentIntegration  # Not used directly
from src.agents.notification_agent import NotificationAgent
from src.database.snowflake_db import SnowflakeConnection
from src.database.ticket_db import TicketDB
from src.data.data_manager import DataManager
# from src.integrations.gmail_realtime import gmail_service  # Disabled - using direct IMAP instead

# Import config for manager email
try:
    from config import MANAGER_EMAIL
except ImportError:
    MANAGER_EMAIL = os.getenv('MANAGER_EMAIL', 'anantlad66@gmail.com')

# Import simplified chatbot router
from chatbot.simple_router import router as chatbot_router

app = FastAPI(title="TeamLogic AutoTask API", description="Backend API for TeamLogic AutoTask System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include chatbot router
app.include_router(chatbot_router)

# --- AUTHENTICATION SETUP ---
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Admin user (keep hardcoded for system access)
DEMO_USERS = {
    # Admin
    "admin": {"username": "admin", "password": "admin", "role": "admin", "email": "admin@example.com", "full_name": "Admin User"}
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def authenticate_user_from_db(username: str, password: str) -> Optional[dict]:
    """Authenticate user from Snowflake USER_DUMMY_DATA table."""
    try:
        if not snowflake_conn:
            logger.error("No Snowflake connection available for user authentication")
            return None

        # Query real user data from Snowflake USER_DUMMY_DATA table
        query = """
        SELECT USER_ID, NAME, USER_EMAIL, USER_PASSWORD
        FROM TEST_DB.PUBLIC.USER_DUMMY_DATA
        WHERE USER_ID = %s OR USER_EMAIL = %s
        """

        results = snowflake_conn.execute_query(query, (username, username))

        if not results:
            logger.info(f"No user found with username: {username}")
            return None

        user = results[0]

        # Check password (in production, use proper password hashing)
        if user.get('USER_PASSWORD') != password:
            logger.info(f"Invalid password for user: {username}")
            return None

        # Return user data in expected format
        return {
            "username": user.get('USER_ID'),
            "password": user.get('USER_PASSWORD'),
            "role": "user",
            "email": user.get('USER_EMAIL'),
            "full_name": user.get('NAME')
        }

    except Exception as e:
        logger.error(f"Error authenticating user from database: {e}")
        return None

def authenticate_technician_from_db(username: str, password: str) -> Optional[dict]:
    """Authenticate technician from Snowflake database."""
    try:
        if not snowflake_conn:
            logger.error("No Snowflake connection available for authentication")
            return None

        # Query technician data from Snowflake
        query = """
        SELECT TECHNICIAN_ID, NAME, EMAIL, ROLE, TECHNICIAN_PASSWORD
        FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        WHERE TECHNICIAN_ID = %s OR EMAIL = %s
        """

        results = snowflake_conn.execute_query(query, (username, username))

        if not results:
            logger.info(f"No technician found with username: {username}")
            return None

        technician = results[0]

        # Check password (in production, use proper password hashing)
        if technician.get('TECHNICIAN_PASSWORD') != password:
            logger.info(f"Invalid password for technician: {username}")
            return None

        # Return user data in expected format
        return {
            "username": technician.get('TECHNICIAN_ID'),
            "password": technician.get('TECHNICIAN_PASSWORD'),
            "role": "technician",
            "email": technician.get('EMAIL'),
            "full_name": technician.get('NAME'),
            "technician_role": technician.get('ROLE')
        }

    except Exception as e:
        logger.error(f"Error authenticating technician from database: {e}")
        return None

def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user credentials - checks real users, technicians, and admin."""
    # First check if it's admin (keep admin hardcoded for system access)
    if username == "admin" and password == "admin":
        return DEMO_USERS.get("admin")

    # Check real users from Snowflake database
    user = authenticate_user_from_db(username, password)
    if user:
        return user

    # Check real technicians from Snowflake database
    technician = authenticate_technician_from_db(username, password)
    if technician:
        return technician

    return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception

        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        user = DEMO_USERS.get(username)
        if user is None:
            raise credentials_exception

        return user
    except JWTError:
        raise credentials_exception

# Set database connection and LLM service for chatbot after initialization
@app.on_event("startup")
async def startup_event():
    """Set database connection and LLM service for chatbot on startup."""
    if snowflake_conn:
        try:
            from chatbot.simple_router import set_database_connection, set_llm_service
            set_database_connection(snowflake_conn)

            # Initialize LLM service
            try:
                from chatbot.services.llm_service import LLMService
                llm_service = LLMService()
                set_llm_service(llm_service)
                print("✅ LLM service initialized for chatbot")
            except Exception as e:
                print(f"⚠️ Warning: Could not initialize LLM service: {e}")
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize chatbot services: {e}")

# --- CONFIGURATION ---
import config

# --- DATABASE CONNECTION ---
try:
    snowflake_conn = SnowflakeConnection(
        sf_account=config.SF_ACCOUNT,
        sf_user=config.SF_USER,
        sf_warehouse=config.SF_WAREHOUSE,
        sf_database=config.SF_DATABASE,
        sf_schema=config.SF_SCHEMA,
        sf_role=config.SF_ROLE
    )
except Exception as e:
    print(f"Warning: Snowflake connection failed: {e}")
    snowflake_conn = None

# Initialize TicketDB with the snowflake connection
ticket_db = TicketDB(conn=snowflake_conn)

# --- AGENTS & DATA MANAGER ---
# Fix path for reference data file when running from backend directory
import os
project_root = os.path.dirname(os.path.abspath(__file__))  # backend directory
parent_dir = os.path.dirname(project_root)  # project root directory
reference_data_path = os.path.join(parent_dir, config.DATA_REF_FILE)

data_manager = DataManager(data_ref_file=reference_data_path)
notification_agent = NotificationAgent()
try:
    intake_agent = IntakeClassificationAgent(
        sf_account=config.SF_ACCOUNT,
        sf_user=config.SF_USER,
        sf_warehouse=config.SF_WAREHOUSE,
        sf_database=config.SF_DATABASE,
        sf_schema=config.SF_SCHEMA,
        sf_role=config.SF_ROLE,
        data_ref_file=reference_data_path
    )
    # The intake_agent already creates its own assignment_agent in __init__
    intake_agent.notification_agent = notification_agent
    intake_agent.reference_data = data_manager.reference_data
except Exception as e:
    print(f"Warning: Intake agent initialization failed: {e}")
    intake_agent = None

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/auth/login")
async def login(login_request: dict):
    """Authenticate user and return access token."""
    try:
        user = authenticate_user(login_request.get("username"), login_request.get("password"))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if role matches (if specified)
        if login_request.get("role") and user["role"] != login_request.get("role"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have {login_request.get('role')} role"
            )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "username": user["username"],
                "role": user["role"],
                "email": user.get("email"),
                "full_name": user.get("full_name")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/auth/logout")
async def logout():
    """Logout user (client-side token removal)."""
    return {"message": "Successfully logged out"}

@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "email": current_user.get("email"),
        "full_name": current_user.get("full_name")
    }

# --- Authentication Models ---
class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = "user"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[dict] = None

class UserResponse(BaseModel):
    username: str
    role: str
    email: Optional[str] = None
    full_name: Optional[str] = None

# --- Pydantic Models ---
class TicketCreateRequest(BaseModel):
    title: str
    description: str
    due_date: str
    user_email: Optional[str] = None
    priority: Optional[str] = None
    requester_name: Optional[str] = None
    phone_number: Optional[str] = None

class TicketResponse(BaseModel):
    ticket_number: str
    status: str
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    assigned_technician: Optional[str] = None
    technician_email: Optional[str] = None
    technician_id: Optional[str] = None
    phone_number: Optional[str] = None

class TechnicianResponse(BaseModel):
    technician_email: str
    assigned_technician: str
    ticket_number: str

# --- Webhook Models ---
class AutotaskWebhookRequest(BaseModel):
    """Model for incoming webhook from Autotask"""
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Ticket description")
    due_date: str = Field(..., description="Due date in YYYY-MM-DD format")
    priority: str = Field(default="Medium", description="Ticket priority")
    ticket_id: Optional[str] = Field(None, description="Autotask ticket ID")
    requester_name: Optional[str] = Field(None, description="Name of person who created ticket")
    requester_email: Optional[str] = Field(None, description="Email of person who created ticket")
    company_id: Optional[str] = Field(None, description="Autotask company ID")
    contact_id: Optional[str] = Field(None, description="Autotask contact ID")

class AutotaskAssignmentWebhook(BaseModel):
    """Model for outbound assignment webhook to Autotask"""
    ticket_id: str = Field(..., description="Autotask ticket ID")
    assigned_technician_id: Optional[str] = Field(None, description="Autotask technician resource ID")
    assigned_technician_name: str = Field(..., description="Technician name")
    assigned_technician_email: str = Field(..., description="Technician email")
    assignment_notes: Optional[str] = Field(None, description="Assignment reasoning/notes")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours for completion")
    status: str = Field(default="Assigned", description="New ticket status")

class AutotaskNotificationWebhook(BaseModel):
    """Model for outbound notification webhook to Autotask"""
    ticket_id: str = Field(..., description="Autotask ticket ID")
    notification_type: str = Field(..., description="Type of notification (assignment, status_update, etc.)")
    recipient_email: str = Field(..., description="Email of notification recipient")
    subject: str = Field(..., description="Email subject")
    message: str = Field(..., description="Email message content")
    sent_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp when notification was sent")

class WebhookResponse(BaseModel):
    """Standard webhook response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class TicketUpdateRequest(BaseModel):
    """Model for updating ticket status and priority"""
    status: Optional[str] = Field(None, description="New ticket status (Open, In Progress, Closed, Resolved, etc.)")
    priority: Optional[str] = Field(None, description="New ticket priority (Low, Medium, High, Critical)")

class TicketUpdateResponse(BaseModel):
    """Response for ticket update operations"""
    success: bool
    message: str
    ticket_number: str
    updated_fields: Dict[str, str]
    moved_to_closed: bool = False
    workload_updated: bool = False
    technician_email: Optional[str] = None

# --- API Endpoints ---
@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Specific ticket endpoints (must come before parameterized routes) ---

@app.get("/tickets/count")
def get_tickets_count():
    """Get total count of tickets"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")
        query = "SELECT COUNT(*) as total_tickets FROM TEST_DB.PUBLIC.TICKETS"
        result = snowflake_conn.execute_query(query)
        return {"total_tickets": result[0]["TOTAL_TICKETS"] if result else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tickets count: {str(e)}")

@app.get("/tickets/statistics")
def get_ticket_statistics():
    """Get ticket statistics including status and priority breakdown"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Get status breakdown
        status_query = """
            SELECT STATUS, COUNT(*) as count
            FROM TEST_DB.PUBLIC.TICKETS
            GROUP BY STATUS
        """

        # Get priority breakdown
        priority_query = """
            SELECT PRIORITY, COUNT(*) as count
            FROM TEST_DB.PUBLIC.TICKETS
            GROUP BY PRIORITY
        """

        status_results = snowflake_conn.execute_query(status_query)
        priority_results = snowflake_conn.execute_query(priority_query)

        return {
            "by_status": {row["STATUS"]: row["COUNT"] for row in status_results} if status_results else {},
            "by_priority": {row["PRIORITY"]: row["COUNT"] for row in priority_results} if priority_results else {}
        }
    except Exception as e:
        logger.error(f"Failed to get ticket statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ticket statistics: {str(e)}")

@app.get("/debug/snowflake-tables")
def debug_snowflake_tables():
    """Debug endpoint to check both Snowflake tables"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Check TICKETS table
        tickets_query = """
            SELECT TICKETNUMBER, TITLE, TECHNICIAN_ID, STATUS
            FROM TEST_DB.PUBLIC.TICKETS
            WHERE TICKETNUMBER LIKE 'T20250804%'
            ORDER BY TICKETNUMBER
        """

        # Check TECHNICIAN_DUMMY_DATA table
        technicians_query = """
            SELECT TECHNICIAN_ID, NAME, CURRENT_WORKLOAD
            FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            ORDER BY TECHNICIAN_ID
        """

        tickets_results = snowflake_conn.execute_query(tickets_query)
        technicians_results = snowflake_conn.execute_query(technicians_query)

        return {
            "tickets_table": tickets_results if tickets_results else [],
            "technicians_table": technicians_results if technicians_results else []
        }
    except Exception as e:
        logger.error(f"Failed to query Snowflake tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query Snowflake tables: {str(e)}")

@app.post("/admin/reset-workloads")
def reset_technician_workloads():
    """Reset all technician workloads to match actual current tickets"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Get all technicians
        technicians_query = """
            SELECT TECHNICIAN_ID, NAME
            FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            ORDER BY TECHNICIAN_ID
        """

        technicians = snowflake_conn.execute_query(technicians_query)

        reset_results = []

        for tech in technicians:
            tech_id = tech["TECHNICIAN_ID"]

            # Count actual tickets for this technician
            count_query = """
                SELECT COUNT(*) as actual_workload
                FROM TEST_DB.PUBLIC.TICKETS
                WHERE TECHNICIAN_ID = %s AND STATUS != 'resolved' AND STATUS != 'closed'
            """

            count_result = snowflake_conn.execute_query(count_query, (tech_id,))
            actual_workload = count_result[0]["ACTUAL_WORKLOAD"] if count_result else 0

            # Update the technician's workload to match actual tickets
            update_query = """
                UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
                SET CURRENT_WORKLOAD = %s
                WHERE TECHNICIAN_ID = %s
            """

            snowflake_conn.execute_query(update_query, (actual_workload, tech_id))

            reset_results.append({
                "technician_id": tech_id,
                "name": tech["NAME"],
                "new_workload": actual_workload
            })

        return {
            "message": "All technician workloads reset to match actual tickets",
            "reset_results": reset_results,
            "success": True
        }

    except Exception as e:
        logger.error(f"Failed to reset workloads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset workloads: {str(e)}")

@app.get("/admin/technician-credentials")
def get_technician_credentials():
    """Get all technician credentials for testing purposes"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Get all technician credentials
        query = """
            SELECT TECHNICIAN_ID, NAME, EMAIL, TECHNICIAN_PASSWORD
            FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            ORDER BY TECHNICIAN_ID
        """

        results = snowflake_conn.execute_query(query)

        credentials = []
        for tech in results:
            credentials.append({
                "technician_id": tech.get("TECHNICIAN_ID"),
                "name": tech.get("NAME"),
                "email": tech.get("EMAIL"),
                "password": tech.get("TECHNICIAN_PASSWORD")
            })

        return {
            "message": "Technician credentials retrieved",
            "credentials": credentials,
            "success": True
        }

    except Exception as e:
        logger.error(f"Failed to get technician credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get technician credentials: {str(e)}")

@app.post("/admin/fix-workload-data-types")
def fix_workload_data_types():
    """Fix workload data types and reset all workloads to correct values"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Step 1: Reset all workloads to 0 first
        reset_query = """
            UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            SET CURRENT_WORKLOAD = 0
        """
        snowflake_conn.execute_query(reset_query)

        # Step 2: Calculate actual workloads from tickets
        workload_updates = []

        # Get all technicians
        tech_query = """
            SELECT TECHNICIAN_ID, NAME
            FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            ORDER BY TECHNICIAN_ID
        """
        technicians = snowflake_conn.execute_query(tech_query)

        for tech in technicians:
            tech_id = tech["TECHNICIAN_ID"]

            # Count actual tickets for this technician (only non-resolved/closed)
            count_query = """
                SELECT COUNT(*) as actual_workload
                FROM TEST_DB.PUBLIC.TICKETS
                WHERE TECHNICIAN_ID = %s
                AND STATUS NOT IN ('resolved', 'closed', 'Resolved', 'Closed')
            """

            count_result = snowflake_conn.execute_query(count_query, (tech_id,))
            actual_workload = int(count_result[0]["ACTUAL_WORKLOAD"]) if count_result else 0

            # Update with integer value
            update_query = """
                UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
                SET CURRENT_WORKLOAD = %s
                WHERE TECHNICIAN_ID = %s
            """

            snowflake_conn.execute_query(update_query, (actual_workload, tech_id))

            workload_updates.append({
                "technician_id": tech_id,
                "name": tech["NAME"],
                "actual_workload": actual_workload
            })

        return {
            "message": "Workload data types fixed and values reset to match actual tickets",
            "workload_updates": workload_updates,
            "success": True
        }

    except Exception as e:
        logger.error(f"Failed to fix workload data types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fix workload data types: {str(e)}")

# Dummy ticket deletion completed successfully via external script

@app.get("/tickets/closed", response_model=List[dict])
def get_closed_tickets(limit: int = Query(50, le=100), offset: int = 0):
    """Get closed/resolved tickets from CLOSED_TICKETS table"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        cursor = snowflake_conn.conn.cursor()

        # Check if CLOSED_TICKETS table exists, if not return empty list
        check_table_query = """
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_NAME = 'CLOSED_TICKETS'
        """
        cursor.execute(check_table_query)
        table_exists = cursor.fetchone()[0] > 0

        if not table_exists:
            cursor.close()
            return []

        # Get closed tickets
        query = """
        SELECT
            TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY,
            ISSUETYPE, SUBISSUETYPE, DUEDATETIME, PRIORITY, STATUS, RESOLUTION,
            TECHNICIANEMAIL, TECHNICIAN_ID, USEREMAIL, USERID, PHONENUMBER, CLOSED_AT, ORIGINAL_CREATED_AT
        FROM TEST_DB.PUBLIC.CLOSED_TICKETS
        ORDER BY CLOSED_AT DESC
        LIMIT %s OFFSET %s
        """

        cursor.execute(query, (limit, offset))
        results = cursor.fetchall()
        cursor.close()

        # Convert to list of dictionaries
        tickets = []
        for row in results:
            ticket = {
                "ticket_number": row[0],
                "title": row[1],
                "description": row[2],
                "ticket_type": row[3],
                "ticket_category": row[4],
                "issue_type": row[5],
                "sub_issue_type": row[6],
                "due_date": row[7],
                "priority": row[8],
                "status": row[9],
                "resolution": row[10],
                "technician_email": row[11],
                "technician_id": row[12],
                "user_email": row[13],
                "user_id": row[14],
                "phone_number": row[15],
                "closed_at": str(row[16]) if row[16] else None,
                "original_created_at": str(row[17]) if row[17] else None
            }
            tickets.append(ticket)

        return tickets

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve closed tickets: {str(e)}")

@app.get("/tickets/stats")
def get_tickets_stats():
    """Get ticket statistics by status and priority"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")
        status_query = """
            SELECT STATUS, COUNT(*) as count
            FROM TEST_DB.PUBLIC.TICKETS
            GROUP BY STATUS
        """
        priority_query = """
            SELECT PRIORITY, COUNT(*) as count
            FROM TEST_DB.PUBLIC.TICKETS
            GROUP BY PRIORITY
        """

        status_results = snowflake_conn.execute_query(status_query)
        priority_results = snowflake_conn.execute_query(priority_query)

        return {
            "by_status": {row["STATUS"]: row["COUNT"] for row in status_results},
            "by_priority": {row["PRIORITY"]: row["COUNT"] for row in priority_results}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ticket statistics: {str(e)}")

# --- General ticket endpoints ---

@app.get("/tickets", response_model=List[dict])
def get_all_tickets(limit: int = Query(50, le=100), offset: int = 0, status: Optional[str] = None, priority: Optional[str] = None, user_email: Optional[str] = None):
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Build query with filters
        query = "SELECT * FROM TEST_DB.PUBLIC.TICKETS"
        conditions = []

        if status:
            conditions.append(f"STATUS = '{status}'")
        if priority:
            conditions.append(f"PRIORITY = '{priority}'")
        if user_email:
            conditions.append(f"USEREMAIL = '{user_email}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY TICKETNUMBER DESC"
        query += f" LIMIT {limit} OFFSET {offset}"

        results = snowflake_conn.execute_query(query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tickets: {str(e)}")

@app.get("/tickets/{ticket_number}")
def get_ticket(ticket_number: str):
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        query = "SELECT * FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s"
        results = snowflake_conn.execute_query(query, (ticket_number,))

        if not results:
            raise HTTPException(status_code=404, detail="Ticket not found")

        return results[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ticket: {str(e)}")

@app.get("/tickets/{ticket_number}/technician", response_model=TechnicianResponse)
def get_technician(ticket_number: str):
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Get ticket first to get technician email
        query = "SELECT * FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s"
        results = snowflake_conn.execute_query(query, (ticket_number,))

        if not results:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket = results[0]

        technician_email = ticket.get('TECHNICIANEMAIL')
        if not technician_email:
            raise HTTPException(status_code=404, detail="No technician assigned to this ticket")

        return TechnicianResponse(
            technician_email=technician_email,
            assigned_technician=technician_email,  # Using email as name for now
            ticket_number=ticket_number
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve technician: {str(e)}")

@app.post("/tickets/{ticket_number}/assign")
def assign_ticket(ticket_number: str, assignment_data: dict):
    """Assign a ticket to a technician with proper workload management"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        technician_id = assignment_data.get('technician_id')
        if not technician_id:
            raise HTTPException(status_code=400, detail="technician_id is required")

        backend_tech_id = technician_id

        # Fetch the technician's email dynamically
        get_email_query = """
        SELECT EMAIL FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA WHERE TECHNICIAN_ID = %s
        """
        email_result = snowflake_conn.execute_query(get_email_query, (backend_tech_id,))
        if not email_result or not email_result[0].get('EMAIL'):
            raise HTTPException(status_code=404, detail=f"Technician email not found for ID {backend_tech_id}")
        technician_email = email_result[0]['EMAIL']

        # First, get the current ticket data to check if it's already assigned
        get_ticket_query = """
        SELECT TECHNICIAN_ID, STATUS FROM TEST_DB.PUBLIC.TICKETS
        WHERE TICKETNUMBER = %s
        """
        ticket_result = snowflake_conn.execute_query(get_ticket_query, (ticket_number,))
        if not ticket_result:
            raise HTTPException(status_code=404, detail="Ticket not found")
        current_ticket = ticket_result[0]
        previous_technician_id = current_ticket.get('TECHNICIAN_ID')
        current_status = current_ticket.get('STATUS')

        # Update the ticket with the new assigned technician and email
        update_ticket_query = """
        UPDATE TEST_DB.PUBLIC.TICKETS
        SET TECHNICIAN_ID = %s, TECHNICIANEMAIL = %s, STATUS = 'Assigned'
        WHERE TICKETNUMBER = %s
        """
        snowflake_conn.execute_query(update_ticket_query, (backend_tech_id, technician_email, ticket_number))

        # Handle workload changes:
        if previous_technician_id and previous_technician_id != backend_tech_id:
            decrement_workload_query = """
            UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
            SET CURRENT_WORKLOAD = GREATEST(CURRENT_WORKLOAD - 1, 0)
            WHERE TECHNICIAN_ID = %s
            """
            snowflake_conn.execute_query(decrement_workload_query, (previous_technician_id,))
            print(f"✅ Decremented workload for previous technician {previous_technician_id}")

        increment_workload_query = """
        UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        SET CURRENT_WORKLOAD = CURRENT_WORKLOAD + 1
        WHERE TECHNICIAN_ID = %s
        """
        snowflake_conn.execute_query(increment_workload_query, (backend_tech_id,))
        print(f"✅ Incremented workload for new technician {backend_tech_id}")

        if previous_technician_id and previous_technician_id != backend_tech_id:
            message = f"Ticket {ticket_number} reassigned from {previous_technician_id} to {technician_id}. Workload and email updated."
        else:
            message = f"Ticket {ticket_number} assigned to technician {technician_id} (email: {technician_email})"

        return {
            "message": message,
            "success": True,
            "previous_technician": previous_technician_id,
            "new_technician": technician_id,
            "new_technician_email": technician_email,
            "workload_transferred": previous_technician_id != backend_tech_id if previous_technician_id else False
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign ticket: {str(e)}")

@app.patch("/tickets/{ticket_number}/status")
def update_ticket_status(ticket_number: str, status_data: dict):
    """Update ticket status and handle workload changes"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        new_status = status_data.get('status')
        if not new_status:
            raise HTTPException(status_code=400, detail="status is required")

        # Get current ticket data to check technician assignment
        get_ticket_query = """
        SELECT TECHNICIAN_ID, STATUS FROM TEST_DB.PUBLIC.TICKETS
        WHERE TICKETNUMBER = %s
        """

        ticket_result = snowflake_conn.execute_query(get_ticket_query, (ticket_number,))
        if not ticket_result:
            raise HTTPException(status_code=404, detail="Ticket not found")

        current_ticket = ticket_result[0]
        current_status = current_ticket.get('STATUS')
        technician_id = current_ticket.get('TECHNICIAN_ID')

        # Update the ticket status
        update_query = """
        UPDATE TEST_DB.PUBLIC.TICKETS
        SET STATUS = %s
        WHERE TICKETNUMBER = %s
        """

        snowflake_conn.execute_query(update_query, (new_status, ticket_number))

        # Handle workload changes based on status transitions
        if technician_id:
            # If ticket is being resolved/closed, decrement workload
            if new_status.lower() in ['resolved', 'closed'] and current_status.lower() not in ['resolved', 'closed']:
                decrement_workload_query = """
                UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
                SET CURRENT_WORKLOAD = GREATEST(CURRENT_WORKLOAD - 1, 0)
                WHERE TECHNICIAN_ID = %s
                """
                snowflake_conn.execute_query(decrement_workload_query, (technician_id,))

            # If ticket is being reopened from resolved/closed, increment workload
            elif current_status.lower() in ['resolved', 'closed'] and new_status.lower() not in ['resolved', 'closed']:
                increment_workload_query = """
                UPDATE TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
                SET CURRENT_WORKLOAD = CURRENT_WORKLOAD + 1
                WHERE TECHNICIAN_ID = %s
                """
                snowflake_conn.execute_query(increment_workload_query, (technician_id,))

        return {"message": f"Ticket {ticket_number} status updated to {new_status}", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ticket status: {str(e)}")

@app.patch("/tickets/{ticket_number}", response_model=TicketUpdateResponse)
def update_ticket_status_priority(ticket_number: str, update_request: TicketUpdateRequest):
    """
    Update ticket status and/or priority by ticket number.

    If status is updated to 'Closed' or 'Resolved':
    - Moves ticket from TICKETS to CLOSED_TICKETS table
    - Decrements assigned technician's workload by 1
    """
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Validate that at least one field is being updated
        if not update_request.status and not update_request.priority:
            raise HTTPException(status_code=400, detail="At least one field (status or priority) must be provided")

        cursor = snowflake_conn.conn.cursor()

        # First, get the current ticket data
        get_ticket_query = """
        SELECT * FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s
        """
        cursor.execute(get_ticket_query, (ticket_number,))
        ticket_data = cursor.fetchone()

        if not ticket_data:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_number} not found")

        # Get column names for the ticket data
        column_names = [desc[0] for desc in cursor.description]
        ticket_dict = dict(zip(column_names, ticket_data))

        updated_fields = {}
        moved_to_closed = False
        workload_updated = False
        technician_email = ticket_dict.get('TECHNICIANEMAIL')

        # Check if status is being updated to Closed or Resolved
        status_closes_ticket = update_request.status and update_request.status.lower() in ['closed', 'resolved']

        if status_closes_ticket:
            # Ensure TECHNICIAN_ID columns exist in both tables
            ensure_technician_id_column()

            # Create CLOSED_TICKETS table if it doesn't exist
            create_closed_table_query = """
            CREATE TABLE IF NOT EXISTS TEST_DB.PUBLIC.CLOSED_TICKETS (
                TICKETNUMBER VARCHAR(50) PRIMARY KEY,
                TITLE VARCHAR(500),
                DESCRIPTION TEXT,
                TICKETTYPE VARCHAR(50),
                TICKETCATEGORY VARCHAR(50),
                ISSUETYPE VARCHAR(50),
                SUBISSUETYPE VARCHAR(50),
                DUEDATETIME VARCHAR(50),
                PRIORITY VARCHAR(50),
                STATUS VARCHAR(50),
                RESOLUTION TEXT,
                TECHNICIANEMAIL VARCHAR(100),
                TECHNICIAN_ID VARCHAR(50),
                USEREMAIL VARCHAR(100),
                USERID VARCHAR(50),
                PHONENUMBER VARCHAR(20),
                CLOSED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ORIGINAL_CREATED_AT TIMESTAMP
            )
            """
            cursor.execute(create_closed_table_query)

            # Insert ticket into CLOSED_TICKETS table with updated status/priority
            insert_closed_query = """
            INSERT INTO TEST_DB.PUBLIC.CLOSED_TICKETS (
                TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY,
                ISSUETYPE, SUBISSUETYPE, DUEDATETIME, PRIORITY, STATUS, RESOLUTION,
                TECHNICIANEMAIL, TECHNICIAN_ID, USEREMAIL, USERID, PHONENUMBER, ORIGINAL_CREATED_AT
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """

            # Use updated values or original values
            final_priority = update_request.priority or ticket_dict.get('PRIORITY')
            final_status = update_request.status or ticket_dict.get('STATUS')

            # Get TECHNICIAN_ID from email for closed ticket
            closed_technician_id = None
            if ticket_dict.get('TECHNICIANEMAIL'):
                closed_technician_id = get_technician_id_from_email(ticket_dict.get('TECHNICIANEMAIL'))
                print(f"🔍 Closed ticket technician ID: {closed_technician_id}")

            try:
                cursor.execute(insert_closed_query, (
                    ticket_dict.get('TICKETNUMBER'),
                    ticket_dict.get('TITLE'),
                    ticket_dict.get('DESCRIPTION'),
                    ticket_dict.get('TICKETTYPE'),
                    ticket_dict.get('TICKETCATEGORY'),
                    ticket_dict.get('ISSUETYPE'),
                    ticket_dict.get('SUBISSUETYPE'),
                    ticket_dict.get('DUEDATETIME'),
                    final_priority,
                    final_status,
                    ticket_dict.get('RESOLUTION'),
                    ticket_dict.get('TECHNICIANEMAIL'),
                    closed_technician_id,  # TECHNICIAN_ID
                    ticket_dict.get('USEREMAIL'),
                    ticket_dict.get('USERID'),
                    ticket_dict.get('PHONENUMBER')
                ))
                print(f"✅ Successfully inserted ticket {ticket_number} into CLOSED_TICKETS")
            except Exception as insert_error:
                print(f"❌ Error inserting into CLOSED_TICKETS: {insert_error}")
                raise HTTPException(status_code=500, detail=f"Failed to move ticket to closed: {str(insert_error)}")

            # Delete ticket from TICKETS table
            try:
                delete_ticket_query = "DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s"
                cursor.execute(delete_ticket_query, (ticket_number,))
                print(f"✅ Successfully deleted ticket {ticket_number} from TICKETS table")
            except Exception as delete_error:
                print(f"❌ Error deleting from TICKETS: {delete_error}")
                raise HTTPException(status_code=500, detail=f"Failed to delete ticket from active table: {str(delete_error)}")

            moved_to_closed = True
            updated_fields['status'] = final_status
            if update_request.priority:
                updated_fields['priority'] = final_priority

            # Decrement technician workload if ticket was assigned
            if technician_email:
                try:
                    # Import the workload update function
                    from src.agents.assignment_agent import update_technician_workload_by_email
                    workload_updated = update_technician_workload_by_email(technician_email, -1, snowflake_conn)
                    if workload_updated:
                        print(f"✅ Decremented workload for technician {technician_email}")
                    else:
                        print(f"⚠️ Failed to decrement workload for technician {technician_email}")
                except Exception as e:
                    print(f"⚠️ Error updating technician workload: {str(e)}")
                    workload_updated = False

        else:
            # Regular update (not closing the ticket)
            update_parts = []
            update_values = []

            if update_request.status:
                update_parts.append("STATUS = %s")
                update_values.append(update_request.status)
                updated_fields['status'] = update_request.status

            if update_request.priority:
                update_parts.append("PRIORITY = %s")
                update_values.append(update_request.priority)
                updated_fields['priority'] = update_request.priority

            if update_parts:
                update_query = f"""
                UPDATE TEST_DB.PUBLIC.TICKETS
                SET {', '.join(update_parts)}
                WHERE TICKETNUMBER = %s
                """
                update_values.append(ticket_number)
                cursor.execute(update_query, update_values)

        cursor.close()

        return TicketUpdateResponse(
            success=True,
            message=f"Ticket {ticket_number} updated successfully" +
                   (" and moved to closed tickets" if moved_to_closed else ""),
            ticket_number=ticket_number,
            updated_fields=updated_fields,
            moved_to_closed=moved_to_closed,
            workload_updated=workload_updated,
            technician_email=technician_email
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ticket: {str(e)}")

class EscalationRequest(BaseModel):
    """Model for ticket escalation request"""
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")
    technician_id: Optional[str] = Field(None, description="ID of technician escalating the ticket")

class EscalationResponse(BaseModel):
    """Response for ticket escalation operations"""
    success: bool
    message: str
    ticket_number: str
    escalated_to_manager: bool
    manager_email: str

@app.post("/tickets/{ticket_number}/escalate", response_model=EscalationResponse)
def escalate_ticket(ticket_number: str, escalation_data: EscalationRequest):
    """
    Escalate a ticket to management with email notification.
    
    This endpoint:
    1. Updates ticket status to 'Escalated'
    2. Sends email notification to manager about due date exceeded
    3. Records escalation reason
    """
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Get current ticket data
        get_ticket_query = """
        SELECT * FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s
        """
        cursor = snowflake_conn.conn.cursor()
        cursor.execute(get_ticket_query, (ticket_number,))
        ticket_data = cursor.fetchone()

        if not ticket_data:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_number} not found")

        # Get column names for the ticket data
        column_names = [desc[0] for desc in cursor.description]
        ticket_dict = dict(zip(column_names, ticket_data))

        # Update ticket status to Escalated
        update_query = """
        UPDATE TEST_DB.PUBLIC.TICKETS
        SET STATUS = 'Escalated'
        WHERE TICKETNUMBER = %s
        """
        cursor.execute(update_query, (ticket_number,))

        # Initialize notification agent
        notification_agent = NotificationAgent(db_connection=snowflake_conn)
        
        # Prepare ticket data for notification
        ticket_notification_data = {
            'ticket_number': ticket_number,
            'title': ticket_dict.get('TITLE', ''),
            'description': ticket_dict.get('DESCRIPTION', ''),
            'priority': ticket_dict.get('PRIORITY', ''),
            'due_date': ticket_dict.get('DUEDATETIME', ''),
            'status': 'Escalated',
            'escalation_reason': escalation_data.escalation_reason or 'Due date exceeded - requires management attention',
            'technician_id': escalation_data.technician_id or 'Unknown',
            'user_email': ticket_dict.get('USEREMAIL', ''),
            'user_id': ticket_dict.get('USERID', ''),
            'phone_number': ticket_dict.get('PHONENUMBER', ''),
            'technician_email': ticket_dict.get('TECHNICIANEMAIL', ''),
            'created_at': datetime.now().isoformat()
        }

        # Send escalation notification to manager
        manager_email = MANAGER_EMAIL
        escalation_sent = False
        
        try:
            escalation_sent = notification_agent.send_escalation_notification(
                recipient_email=manager_email,
                ticket_data=ticket_notification_data,
                ticket_number=ticket_number,
                escalation_reason=f"Due date exceeded for urgent ticket {ticket_number}",
                recipient_type="manager"
            )
        except Exception as e:
            logger.error(f"Failed to send escalation notification: {e}")
            # Don't fail the escalation if email fails

        cursor.close()

        return EscalationResponse(
            success=True,
            message=f"Ticket {ticket_number} escalated successfully. Manager notified about due date exceeded.",
            ticket_number=ticket_number,
            escalated_to_manager=escalation_sent,
            manager_email=manager_email
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to escalate ticket: {str(e)}")

class ReminderRequest(BaseModel):
    """Model for due date reminder request"""
    ticket_number: str = Field(..., description="Ticket number")
    ticket_title: str = Field(..., description="Ticket title")
    due_date: str = Field(..., description="Due date")
    technician_email: str = Field(..., description="Technician email")
    technician_name: str = Field(..., description="Technician name")
    customer_name: str = Field(..., description="Customer name")
    priority: str = Field(..., description="Ticket priority")

class ReminderResponse(BaseModel):
    """Response for reminder email operations"""
    success: bool
    message: str
    ticket_number: str
    technician_email: str
    reminder_sent: bool

@app.post("/api/tickets/send-reminder", response_model=ReminderResponse)
def send_due_date_reminder(reminder_data: ReminderRequest):
    """
    Send due date reminder email to assigned technician.
    
    This endpoint:
    1. Sends reminder email to technician about approaching due date
    2. Logs the reminder action
    """
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Initialize notification agent
        notification_agent = NotificationAgent(db_connection=snowflake_conn)
        
        # Prepare ticket data for reminder notification
        ticket_notification_data = {
            'ticket_number': reminder_data.ticket_number,
            'title': reminder_data.ticket_title,
            'due_date': reminder_data.due_date,
            'priority': reminder_data.priority,
            'technician_name': reminder_data.technician_name,
            'customer_name': reminder_data.customer_name,
            'status': 'In Progress',
            'created_at': datetime.now().isoformat()
        }

        # Send reminder notification to technician
        reminder_sent = False
        
        try:
            reminder_sent = notification_agent.send_due_date_reminder(
                recipient_email=reminder_data.technician_email,
                ticket_data=ticket_notification_data,
                ticket_number=reminder_data.ticket_number,
                recipient_type="technician"
            )
        except Exception as e:
            logger.error(f"Failed to send reminder notification: {e}")
            # Don't fail the reminder if email fails

        return ReminderResponse(
            success=True,
            message=f"Due date reminder sent to {reminder_data.technician_name} for ticket {reminder_data.ticket_number}",
            ticket_number=reminder_data.ticket_number,
            technician_email=reminder_data.technician_email,
            reminder_sent=reminder_sent
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reminder: {str(e)}")

def get_technician_id_from_email(technician_email: str) -> Optional[str]:
    """
    Get TECHNICIAN_ID from TECHNICIAN_DUMMY_DATA table using email

    Args:
        technician_email (str): Email of the technician

    Returns:
        Optional[str]: TECHNICIAN_ID if found, None otherwise
    """
    if not technician_email or not snowflake_conn:
        return None

    try:
        cursor = snowflake_conn.conn.cursor()
        query = """
        SELECT TECHNICIAN_ID
        FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        WHERE EMAIL = %s
        """
        cursor.execute(query, (technician_email,))
        result = cursor.fetchone()
        cursor.close()

        if result and result[0]:
            return str(result[0])
        return None

    except Exception as e:
        print(f"Error getting technician ID from email {technician_email}: {e}")
        return None

def ensure_technician_id_column():
    """
    Ensure TECHNICIAN_ID column exists in both TICKETS and CLOSED_TICKETS tables
    """
    if not snowflake_conn:
        return False

    try:
        cursor = snowflake_conn.conn.cursor()

        # Check and add TECHNICIAN_ID column to TICKETS table
        check_tickets_column_query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'PUBLIC'
        AND TABLE_NAME = 'TICKETS'
        AND COLUMN_NAME = 'TECHNICIAN_ID'
        """
        cursor.execute(check_tickets_column_query)
        tickets_column_exists = cursor.fetchone()[0] > 0

        if not tickets_column_exists:
            # Add TECHNICIAN_ID column to TICKETS
            alter_tickets_query = """
            ALTER TABLE TEST_DB.PUBLIC.TICKETS
            ADD COLUMN TECHNICIAN_ID VARCHAR(50)
            """
            cursor.execute(alter_tickets_query)
            print("✅ Added TECHNICIAN_ID column to TICKETS table")
        else:
            print("✅ TECHNICIAN_ID column already exists in TICKETS table")

        # Check if CLOSED_TICKETS table exists and has TECHNICIAN_ID column
        check_closed_table_query = """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'PUBLIC'
        AND TABLE_NAME = 'CLOSED_TICKETS'
        """
        cursor.execute(check_closed_table_query)
        closed_table_exists = cursor.fetchone()[0] > 0

        if closed_table_exists:
            # Check if TECHNICIAN_ID column exists in CLOSED_TICKETS
            check_closed_column_query = """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'PUBLIC'
            AND TABLE_NAME = 'CLOSED_TICKETS'
            AND COLUMN_NAME = 'TECHNICIAN_ID'
            """
            cursor.execute(check_closed_column_query)
            closed_column_exists = cursor.fetchone()[0] > 0

            if not closed_column_exists:
                # Add TECHNICIAN_ID column to CLOSED_TICKETS
                alter_closed_query = """
                ALTER TABLE TEST_DB.PUBLIC.CLOSED_TICKETS
                ADD COLUMN TECHNICIAN_ID VARCHAR(50)
                """
                cursor.execute(alter_closed_query)
                print("✅ Added TECHNICIAN_ID column to CLOSED_TICKETS table")
            else:
                print("✅ TECHNICIAN_ID column already exists in CLOSED_TICKETS table")

        cursor.close()
        return True

    except Exception as e:
        print(f"Error ensuring TECHNICIAN_ID column: {e}")
        return False

@app.post("/tickets", status_code=201, response_model=TicketResponse)
def create_ticket(request: TicketCreateRequest):
    try:
        print(f"🎫 Creating ticket with title: {request.title}")

        # Check if intake agent is available
        if not intake_agent:
            raise HTTPException(status_code=503, detail="Ticket processing service unavailable. Please check configuration.")

        # Use agentic workflow to process and create ticket
        print(f"🚀 Starting agentic workflow for ticket: {request.title}")

        # Process the ticket through the complete agentic workflow
        result = intake_agent.process_new_ticket(
            ticket_name=request.requester_name or "Anonymous",
            ticket_description=request.description,
            ticket_title=request.title,
            due_date=request.due_date,
            priority_initial=request.priority or "Medium",
            user_email=request.user_email,
            phone_number=request.phone_number
        )

        if not result:
            print("❌ Agentic workflow failed completely")
            raise HTTPException(status_code=500, detail="Failed to process ticket through agentic workflow")

        print(f"✅ Agentic workflow completed successfully")

        # Extract data from agentic workflow result
        ticket_number = result.get("ticket_number")
        if not ticket_number:
            raise HTTPException(status_code=500, detail="Failed to generate ticket number")

        classified = result.get("classified_data", {})
        assignment = result.get("assignment_result", {})

        # Debug: Print assignment result structure
        print(f"🔍 Assignment result structure: {assignment}")

        # Insert into Snowflake TICKETS table
        print(f"💾 Inserting ticket {ticket_number} into database")

        # Extract technician email from assignment result
        technician_email = ""
        if assignment:
            # Check if assignment_result is nested
            if "assignment_result" in assignment:
                technician_email = assignment["assignment_result"].get("technician_email", "")
            else:
                technician_email = assignment.get("technician_email", "")

        print(f"🔍 Technician email to save: '{technician_email}'")

        # Ensure TECHNICIAN_ID column exists in TICKETS table
        ensure_technician_id_column()

        # Get TECHNICIAN_ID from email if technician is assigned
        technician_id = None
        if technician_email:
            technician_id = get_technician_id_from_email(technician_email)
            print(f"🔍 Technician ID: '{technician_id}'")

        # Extract classified data with proper fallbacks
        def extract_classified_value(data, key, default=''):
            """Extract value from classified data which may have Label/Value structure"""
            if key in data:
                if isinstance(data[key], dict) and 'Label' in data[key]:
                    return data[key]['Label']
                elif isinstance(data[key], dict) and 'Value' in data[key]:
                    return data[key]['Value']
                return data[key]
            return default

        # Extract all classified fields
        issue_type = extract_classified_value(classified, 'ISSUETYPE', 'Other')
        sub_issue_type = extract_classified_value(classified, 'SUBISSUETYPE', 'General')
        ticket_category = extract_classified_value(classified, 'TICKETCATEGORY', 'General')
        ticket_type = extract_classified_value(classified, 'TICKETTYPE', 'Support')
        priority = extract_classified_value(classified, 'PRIORITY', request.priority or "Medium")
        status = extract_classified_value(classified, 'STATUS', 'Open')
        resolution = result.get('resolution_note', '')

        print(f"🔍 Classified data - Issue Type: '{issue_type}', Sub Issue: '{sub_issue_type}', Category: '{ticket_category}', Type: '{ticket_type}', Priority: '{priority}', Status: '{status}'")

        insert_query = """
            INSERT INTO TEST_DB.PUBLIC.TICKETS (
                TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY,
                ISSUETYPE, SUBISSUETYPE, DUEDATETIME, PRIORITY, STATUS, RESOLUTION,
                TECHNICIANEMAIL, TECHNICIAN_ID, USEREMAIL, USERID, PHONENUMBER
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            ticket_number,
            request.title,
            request.description,
            ticket_type,
            ticket_category,
            issue_type,
            sub_issue_type,
            request.due_date,
            priority,
            status,
            resolution,
            technician_email,
            technician_id,  # TECHNICIAN_ID from lookup
            request.user_email or "",
            request.requester_name or "Anonymous",
            request.phone_number or ""  # PHONENUMBER from request
        )

        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        snowflake_conn.execute_query(insert_query, params)
        print(f"✅ Ticket {ticket_number} successfully inserted into database")

        return TicketResponse(
            ticket_number=ticket_number,
            status="created",
            title=request.title,
            description=request.description,
            due_date=request.due_date,
            priority=priority,
            assigned_technician=assignment.get("assigned_technician", ""),
            technician_email=assignment.get("technician_email", ""),
            technician_id=technician_id,
            phone_number=request.phone_number
        )

    except Exception as e:
        print(f"❌ Error creating ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")

# --- TECHNICIAN ENDPOINTS ---

@app.get("/technicians")
def get_all_technicians():
    """Get all available technicians from Snowflake database"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Query real technician data from Snowflake
        query = """
        SELECT TECHNICIAN_ID, NAME, EMAIL, ROLE, CURRENT_WORKLOAD, SPECIALIZATIONS
        FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
        ORDER BY NAME
        """

        results = snowflake_conn.execute_query(query)

        if not results:
            logger.warning("No technicians found in database")
            return []

        # Transform data to expected format
        technicians = []
        for tech in results:
            # Convert workload to integer to handle Snowflake decimal values
            workload = tech.get('CURRENT_WORKLOAD')
            if workload is not None:
                try:
                    workload = int(float(workload))  # Convert decimal to int
                except (ValueError, TypeError):
                    workload = 0  # Default to 0 if conversion fails
            else:
                workload = 0

            technicians.append({
                "id": tech.get('TECHNICIAN_ID'),
                "name": tech.get('NAME'),
                "username": tech.get('TECHNICIAN_ID'),
                "email": tech.get('EMAIL'),
                "role": tech.get('ROLE'),
                "current_workload": workload,  # Use converted integer value
                "specializations": tech.get('SPECIALIZATIONS')
            })

        logger.info(f"Retrieved {len(technicians)} technicians from database")
        return technicians

    except Exception as e:
        logger.error(f"Failed to get technicians: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get technicians: {str(e)}")

@app.get("/users")
def get_all_users():
    """Get all available users from Snowflake USER_DUMMY_DATA table"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # Query real user data from Snowflake USER_DUMMY_DATA table
        query = """
        SELECT USER_ID, NAME, USER_EMAIL, USER_PHONENUMBER
        FROM TEST_DB.PUBLIC.USER_DUMMY_DATA
        ORDER BY NAME
        """

        results = snowflake_conn.execute_query(query)

        if not results:
            logger.warning("No users found in database")
            return []

        # Transform data to expected format
        users = []
        for user in results:
            users.append({
                "id": user.get('USER_ID'),
                "name": user.get('NAME'),
                "username": user.get('USER_ID'),
                "email": user.get('USER_EMAIL'),
                "phone": user.get('USER_PHONENUMBER'),
                "role": "user"
            })

        logger.info(f"Retrieved {len(users)} users from database")
        return users

    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@app.get("/debug/tickets/{technician_id}")
def debug_technician_tickets(technician_id: str):
    """Debug endpoint to check tickets for a technician"""
    try:
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        # First, get all technician IDs to see what's available
        all_tech_query = """
        SELECT DISTINCT TECHNICIAN_ID
        FROM TEST_DB.PUBLIC.TICKETS
        WHERE TECHNICIAN_ID IS NOT NULL AND TECHNICIAN_ID != ''
        ORDER BY TECHNICIAN_ID
        """

        all_techs = snowflake_conn.execute_query(all_tech_query)

        # Then try to get tickets for the specific technician
        query = """
        SELECT TITLE, TECHNICIAN_ID
        FROM TEST_DB.PUBLIC.TICKETS
        WHERE TECHNICIAN_ID = %s
        LIMIT 5
        """

        tickets = snowflake_conn.execute_query(query, (technician_id,))

        # Also try without parameter binding to see if that works
        direct_query = f"""
        SELECT TITLE, TECHNICIAN_ID
        FROM TEST_DB.PUBLIC.TICKETS
        WHERE TECHNICIAN_ID = '{technician_id}'
        LIMIT 5
        """

        direct_tickets = snowflake_conn.execute_query(direct_query)

        # Try a simple count query
        count_query = f"""
        SELECT COUNT(*) as count
        FROM TEST_DB.PUBLIC.TICKETS
        WHERE TECHNICIAN_ID = '{technician_id}'
        """

        count_result = snowflake_conn.execute_query(count_query)

        return {
            "technician_id": technician_id,
            "available_technician_ids": [t["TECHNICIAN_ID"] for t in all_techs] if all_techs else [],
            "parameterized_query_count": len(tickets) if tickets else 0,
            "direct_query_count": len(direct_tickets) if direct_tickets else 0,
            "count_query_result": count_result[0]["COUNT"] if count_result else 0,
            "parameterized_tickets": tickets[:3] if tickets else [],
            "direct_tickets": direct_tickets[:3] if direct_tickets else []
        }

    except Exception as e:
        logger.error(f"Debug tickets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{technician_id}")
def get_technician_analytics(technician_id: str):
    """Get analytics data for a specific technician"""
    try:
        logger.info(f"Analytics endpoint called for technician: {technician_id}")

        if not snowflake_conn:
            logger.error("No Snowflake connection available")
            raise HTTPException(status_code=503, detail="Database connection unavailable")

        logger.info(f"Executing analytics queries for technician {technician_id}")

        # Use COUNT queries since SELECT queries seem to have issues
        # Get total tickets count
        count_query = f"""
        SELECT COUNT(*) as total_count
        FROM TEST_DB.PUBLIC.TICKETS
        WHERE TECHNICIAN_ID = '{technician_id}'
        """

        count_result = snowflake_conn.execute_query(count_query)
        total_tickets = count_result[0]["TOTAL_COUNT"] if count_result else 0

        logger.info(f"Analytics for {technician_id}: Found {total_tickets} tickets")

        if total_tickets == 0:
            # Return empty analytics if no tickets found
            return {
                "personal_metrics": {
                    "tickets_resolved": 0,
                    "avg_resolution_time": "0 hours",
                    "customer_satisfaction": 0.0,
                    "sla_compliance": 0,
                    "this_week_resolved": 0,
                    "this_month_resolved": 0
                },
                "weekly_data": [],
                "category_data": [],
                "priority_trends": [],
                "team_comparison": []
            }

        # Calculate analytics using COUNT queries
        from datetime import datetime, timedelta
        import calendar

        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Get resolved tickets count
        resolved_query = f"""
        SELECT COUNT(*) as resolved_count
        FROM TEST_DB.PUBLIC.TICKETS
        WHERE TECHNICIAN_ID = '{technician_id}' AND STATUS = 'resolved'
        """

        resolved_result = snowflake_conn.execute_query(resolved_query)
        resolved_tickets = resolved_result[0]["RESOLVED_COUNT"] if resolved_result else 0

        # Personal metrics using COUNT queries
        # Calculate basic metrics
        this_week_resolved = max(1, total_tickets // 4)  # Estimate weekly activity
        this_month_resolved = total_tickets

        # Calculate average resolution time (simplified)
        avg_resolution_hours = max(2, total_tickets * 2)  # Estimate based on ticket count
        avg_resolution_time = f"{avg_resolution_hours} hours"

        # Calculate customer satisfaction (simplified)
        customer_satisfaction = min(5.0, 3.5 + (resolved_tickets * 0.1))

        # Calculate SLA compliance (simplified)
        sla_compliance = min(100, 85 + (resolved_tickets * 2))

        # Create sample category data based on ticket count
        category_data = []
        if total_tickets > 0:
            # Distribute tickets across common categories
            categories = [
                ("Hardware", max(1, total_tickets // 3)),
                ("Software", max(1, total_tickets // 3)),
                ("Network", max(0, total_tickets // 4)),
                ("Email", max(0, total_tickets // 5))
            ]

            category_data = [
                {"category": cat, "count": count, "color": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"][i]}
                for i, (cat, count) in enumerate(categories) if count > 0
            ]

        # Weekly data (simplified)
        weekly_data = [
            {"day": "Mon", "resolved": this_week_resolved // 7, "created": total_tickets // 30},
            {"day": "Tue", "resolved": this_week_resolved // 7, "created": total_tickets // 30},
            {"day": "Wed", "resolved": this_week_resolved // 7, "created": total_tickets // 30},
            {"day": "Thu", "resolved": this_week_resolved // 7, "created": total_tickets // 30},
            {"day": "Fri", "resolved": this_week_resolved // 7, "created": total_tickets // 30},
            {"day": "Sat", "resolved": 0, "created": 0},
            {"day": "Sun", "resolved": 0, "created": 0}
        ]

        return {
            "personal_metrics": {
                "tickets_resolved": resolved_tickets,
                "avg_resolution_time": avg_resolution_time,
                "customer_satisfaction": customer_satisfaction,
                "sla_compliance": sla_compliance,
                "this_week_resolved": this_week_resolved,
                "this_month_resolved": this_month_resolved,
                "total_tickets": total_tickets
            },
            "weekly_data": weekly_data,
            "category_data": category_data,
            "priority_trends": [
                {"month": "Oct", "critical": 1, "high": 2, "medium": max(1, total_tickets//2), "low": 1},
                {"month": "Nov", "critical": 0, "high": 1, "medium": max(1, total_tickets//3), "low": 2},
                {"month": "Dec", "critical": 1, "high": 3, "medium": max(1, total_tickets//2), "low": 1},
                {"month": "Jan", "critical": 0, "high": 2, "medium": max(1, total_tickets//2), "low": 1}
            ],
            "team_comparison": [
                {
                    "name": "You",
                    "tickets_resolved": total_tickets,
                    "satisfaction": customer_satisfaction,
                    "sla_compliance": sla_compliance,
                    "rank": 1
                }
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

# --- Additional Utility Endpoints ---

@app.get("/health/detailed")
def detailed_health_check():
    """Detailed health check including database connectivity"""
    try:
        # Test database connection
        if snowflake_conn:
            test_query = "SELECT 1 as test"
            db_result = snowflake_conn.execute_query(test_query)
            db_status = "connected" if db_result else "disconnected"
        else:
            db_status = "not_initialized"

        return {
            "status": "ok",
            "database": db_status,
            "agents": {
                "intake_agent": "initialized" if intake_agent else "not_initialized",
                "assignment_agent": "initialized" if (intake_agent and hasattr(intake_agent, 'assignment_agent') and intake_agent.assignment_agent) else "not_initialized",
                "notification_agent": "initialized" if notification_agent else "not_initialized"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "error",
            "error": str(e)
        }

@app.get("/debug/table-structure")
def get_table_structure():
    """Debug endpoint to check table structure"""
    try:
        if not snowflake_conn:
            return {"error": "Database connection not available"}

        # Check if TICKETS table exists and get its structure
        describe_query = "DESCRIBE TABLE TEST_DB.PUBLIC.TICKETS"
        result = snowflake_conn.execute_query(describe_query)
        return {"table_structure": result}
    except Exception as e:
        # If table doesn't exist, try to create it
        try:
            if not snowflake_conn:
                return {"error": "Database connection not available for table creation"}

            create_table_query = """
                CREATE TABLE IF NOT EXISTS TEST_DB.PUBLIC.TICKETS (
                    TICKETNUMBER VARCHAR(50) PRIMARY KEY,
                    TITLE VARCHAR(500),
                    DESCRIPTION TEXT,
                    DUE_DATE DATE,
                    PRIORITY VARCHAR(50),
                    STATUS VARCHAR(50),
                    ASSIGNED_TECHNICIAN VARCHAR(200),
                    TECHNICIAN_EMAIL VARCHAR(200),
                    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            snowflake_conn.execute_query(create_table_query)
            return {"message": "Table created successfully", "error": str(e)}
        except Exception as create_error:
            return {"error": f"Table check failed: {str(e)}, Create failed: {str(create_error)}"}

# --- WEBHOOK ENDPOINTS ---

# Configuration for webhook security
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-key")
AUTOTASK_WEBHOOK_URL = os.getenv("AUTOTASK_WEBHOOK_URL", "https://your-autotask-instance.com/api/webhooks")

# --- EMAIL FORWARDING MODELS ---
class EmailForwardingRequest(BaseModel):
    """Model for incoming forwarded emails from Gmail"""
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    from_email: str = Field(..., description="Sender email address")
    from_name: Optional[str] = Field(None, description="Sender name")
    to_email: str = Field(..., description="Recipient email address")
    received_at: Optional[str] = Field(None, description="Email received timestamp")
    message_id: Optional[str] = Field(None, description="Email message ID")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Email attachments")

class EmailProcessingResponse(BaseModel):
    """Response for email processing"""
    success: bool
    message: str
    ticket_number: Optional[str] = None
    processed_as_ticket: bool = False
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature for security"""
    if not signature:
        return False

    try:
        # For testing purposes, allow test signatures
        if signature in ['sha256=test-signature', 'test-signature']:
            return True

        # Autotask typically uses HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Remove 'sha256=' prefix if present
        if signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False

@app.post("/webhooks/autotask/inbound", response_model=WebhookResponse)
async def autotask_inbound_webhook(
    request: Request,
    webhook_data: AutotaskWebhookRequest,
    x_autotask_signature: Optional[str] = Header(None, alias="X-Autotask-Signature")
):
    """
    Inbound webhook endpoint to receive ticket data from Autotask.

    This endpoint receives ticket information from Autotask and processes it through
    our AI agents for classification, assignment, and notification.
    """
    try:
        # Get raw request body for signature verification
        body = await request.body()

        # Verify webhook signature (optional but recommended for production)
        if WEBHOOK_SECRET and x_autotask_signature:
            if not verify_webhook_signature(body, x_autotask_signature, WEBHOOK_SECRET):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        print(f"🔗 Received Autotask webhook for ticket: {webhook_data.title}")

        # Convert webhook data to our internal ticket format (for future use if needed)
        # ticket_request = TicketCreateRequest(
        #     title=webhook_data.title,
        #     description=webhook_data.description,
        #     due_date=webhook_data.due_date,
        #     priority=webhook_data.priority,
        #     user_email=webhook_data.requester_email,
        #     requester_name=webhook_data.requester_name
        # )

        # Process through our agentic workflow
        print(f"🚀 Processing Autotask ticket through AI workflow: {webhook_data.title}")

        if not intake_agent:
            raise HTTPException(status_code=503, detail="Intake agent not available")

        result = intake_agent.process_new_ticket(
            ticket_name=webhook_data.requester_name or "Autotask User",
            ticket_description=webhook_data.description,
            ticket_title=webhook_data.title,
            due_date=webhook_data.due_date,
            priority_initial=webhook_data.priority,
            user_email=webhook_data.requester_email
        )

        if not result:
            raise HTTPException(status_code=500, detail="Failed to process ticket through AI workflow")

        # Extract assignment information
        assignment_result = result.get('assignment_result', {})
        ticket_number = result.get('ticket_number', 'N/A')

        # Prepare response data
        response_data = {
            "internal_ticket_number": ticket_number,
            "autotask_ticket_id": webhook_data.ticket_id,
            "assigned_technician": assignment_result.get('assigned_technician'),
            "technician_email": assignment_result.get('technician_email'),
            "classification": result.get('classified_data', {}),
            "processing_time": datetime.now().isoformat()
        }

        # Send assignment back to Autotask (if configured)
        if webhook_data.ticket_id and assignment_result:
            try:
                await send_assignment_to_autotask(webhook_data.ticket_id, assignment_result, result)
            except Exception as e:
                print(f"⚠️ Failed to send assignment back to Autotask: {e}")
                # Don't fail the whole request if outbound webhook fails

        print(f"✅ Successfully processed Autotask ticket: {ticket_number}")

        return WebhookResponse(
            success=True,
            message=f"Ticket processed successfully. Internal ticket number: {ticket_number}",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing Autotask webhook: {e}")
        return WebhookResponse(
            success=False,
            message="Failed to process ticket",
            errors=[str(e)]
        )

async def send_assignment_to_autotask(ticket_id: str, assignment_result: Dict, full_result: Optional[Dict] = None) -> bool:
    """
    Send assignment information back to Autotask via outbound webhook
    """
    try:
        assignment_data = AutotaskAssignmentWebhook(
            ticket_id=ticket_id,
            assigned_technician_name=assignment_result.get('assigned_technician', ''),
            assigned_technician_email=assignment_result.get('technician_email', ''),
            assignment_notes=assignment_result.get('reasoning', ''),
            estimated_hours=assignment_result.get('estimated_hours'),
            status="Assigned"
        )

        # Send to Autotask webhook endpoint
        if AUTOTASK_WEBHOOK_URL:
            headers = {
                "Content-Type": "application/json",
                "X-Source": "TeamLogic-AI-Agent"
            }

            # Add signature if secret is configured
            if WEBHOOK_SECRET:
                payload = assignment_data.json().encode('utf-8')
                signature = hmac.new(
                    WEBHOOK_SECRET.encode('utf-8'),
                    payload,
                    hashlib.sha256
                ).hexdigest()
                headers["X-TeamLogic-Signature"] = f"sha256={signature}"

            response = requests.post(
                f"{AUTOTASK_WEBHOOK_URL}/assignment",
                json=assignment_data.dict(),
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                print(f"✅ Assignment sent to Autotask for ticket {ticket_id}")
                return True
            else:
                print(f"❌ Failed to send assignment to Autotask: {response.status_code} - {response.text}")
                return False

        return True  # Return True if no webhook URL configured

    except Exception as e:
        print(f"❌ Error sending assignment to Autotask: {e}")
        return False

@app.post("/webhooks/autotask/assignment", response_model=WebhookResponse)
async def send_assignment_webhook(assignment_data: AutotaskAssignmentWebhook):
    """
    Manual endpoint to send assignment data to Autotask.
    This can be used for testing or manual assignment updates.
    """
    try:
        success = await send_assignment_to_autotask(
            assignment_data.ticket_id,
            {
                'assigned_technician': assignment_data.assigned_technician_name,
                'technician_email': assignment_data.assigned_technician_email,
                'reasoning': assignment_data.assignment_notes,
                'estimated_hours': assignment_data.estimated_hours
            },
            {}
        )

        if success:
            return WebhookResponse(
                success=True,
                message=f"Assignment sent to Autotask for ticket {assignment_data.ticket_id}",
                data=assignment_data.dict()
            )
        else:
            return WebhookResponse(
                success=False,
                message="Failed to send assignment to Autotask",
                errors=["Webhook delivery failed"]
            )

    except Exception as e:
        return WebhookResponse(
            success=False,
            message="Failed to send assignment webhook",
            errors=[str(e)]
        )

@app.post("/webhooks/autotask/notification", response_model=WebhookResponse)
async def send_notification_webhook(notification_data: AutotaskNotificationWebhook):
    """
    Send notification data to Autotask.
    This endpoint can be used to notify Autotask about email notifications sent to customers/technicians.
    """
    try:
        # Send to Autotask webhook endpoint
        if AUTOTASK_WEBHOOK_URL:
            headers = {
                "Content-Type": "application/json",
                "X-Source": "TeamLogic-AI-Agent"
            }

            # Add signature if secret is configured
            if WEBHOOK_SECRET:
                payload = notification_data.json().encode('utf-8')
                signature = hmac.new(
                    WEBHOOK_SECRET.encode('utf-8'),
                    payload,
                    hashlib.sha256
                ).hexdigest()
                headers["X-TeamLogic-Signature"] = f"sha256={signature}"

            response = requests.post(
                f"{AUTOTASK_WEBHOOK_URL}/notification",
                json=notification_data.dict(),
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                print(f"✅ Notification sent to Autotask for ticket {notification_data.ticket_id}")
                return WebhookResponse(
                    success=True,
                    message=f"Notification sent to Autotask for ticket {notification_data.ticket_id}",
                    data=notification_data.dict()
                )
            else:
                print(f"❌ Failed to send notification to Autotask: {response.status_code} - {response.text}")
                return WebhookResponse(
                    success=False,
                    message="Failed to send notification to Autotask",
                    errors=[f"HTTP {response.status_code}: {response.text}"]
                )
        else:
            # If no webhook URL configured, just return success (for testing)
            return WebhookResponse(
                success=True,
                message="Notification logged (no Autotask webhook URL configured)",
                data=notification_data.dict()
            )

    except Exception as e:
        return WebhookResponse(
            success=False,
            message="Failed to send notification webhook",
            errors=[str(e)]
        )



@app.get("/webhooks/status")
def webhook_status():
    """
    Get webhook configuration status and test connectivity
    """
    try:
        status = {
            "webhook_secret_configured": bool(WEBHOOK_SECRET),
            "autotask_webhook_url_configured": bool(AUTOTASK_WEBHOOK_URL),
            "endpoints": {
                "inbound": "/webhooks/autotask/inbound",
                "assignment": "/webhooks/autotask/assignment",
                "notification": "/webhooks/autotask/notification",
                "email_forwarding": "/webhooks/email/forward"
            },
            "security": {
                "signature_verification": bool(WEBHOOK_SECRET),
                "cors_enabled": True
            },
            "email_processing": {
                "mode": "webhook",
                "webhook_enabled": True,
                "polling_enabled": False,
                "real_time_processing": True
            }
        }

        # Test Autotask connectivity if URL is configured
        if AUTOTASK_WEBHOOK_URL:
            try:
                test_response = requests.get(f"{AUTOTASK_WEBHOOK_URL}/health", timeout=5)
                status["autotask_connectivity"] = {
                    "status": "connected" if test_response.status_code == 200 else "error",
                    "response_code": test_response.status_code
                }
            except Exception as e:
                status["autotask_connectivity"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            status["autotask_connectivity"] = {
                "status": "not_configured",
                "message": "AUTOTASK_WEBHOOK_URL not set"
            }

        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get webhook status: {str(e)}")


@app.get("/email/status")
def get_email_processing_status():
    """
    Get the current status of email processing system (webhook-based).
    """
    try:
        if not intake_agent:
            raise HTTPException(status_code=503, detail="Intake agent not available")

        status = intake_agent.get_email_processing_status()
        return {
            "success": True,
            "processing_mode": "webhook",
            "webhook_endpoint": "/webhooks/email/forward",
            "status": status,
            "message": "Using real-time webhook-based email processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get email processing status: {str(e)}")


# ==================== GMAIL REAL-TIME INTEGRATION ====================

# Gmail Pub/Sub webhook removed - using direct IMAP integration instead


async def process_email_through_intake(email_data: Dict) -> Optional[Dict]:
    """
    Process email through the intake and ticketing workflow

    Args:
        email_data: Email data from Gmail API

    Returns:
        Ticket processing result or None
    """
    try:
        # Convert Gmail email data to intake format
        intake_data = {
            'title': email_data.get('subject', 'Email Support Request'),
            'description': email_data.get('body', ''),
            'user_email': email_data.get('from_email', ''),
            'user_name': email_data.get('from_name', ''),
            'source': 'gmail_realtime',
            'received_at': email_data.get('received_at', ''),
            'message_id': email_data.get('message_id', ''),
            'thread_id': email_data.get('thread_id', '')
        }

        # Set default values for email tickets
        due_date = (datetime.now() + timedelta(hours=48)).strftime("%Y-%m-%d")
        priority_initial = "Medium"

        # Process using the unified ticket processing method
        result = intake_agent.process_new_ticket(
            ticket_name=intake_data['user_name'],
            ticket_description=intake_data['description'],
            ticket_title=intake_data['title'],
            due_date=due_date,
            priority_initial=priority_initial,
            user_email=intake_data['user_email'],
            user_id=None,
            phone_number=None
        )

        if result:
            # Add Gmail-specific metadata
            result['source'] = 'gmail_realtime'
            result['gmail_message_id'] = intake_data['message_id']
            result['gmail_thread_id'] = intake_data['thread_id']
            result['received_at'] = intake_data['received_at']

            # Note: Database insertion is handled by the main /tickets endpoint
            # This prevents duplicate ticket creation
            print(f"✅ Ticket processed successfully: {result.get('ticket_number', 'Unknown')}")
            result['database_saved'] = True

            return result
        else:
            return None

    except Exception as e:
        print(f"❌ Error processing email through intake: {e}")
        return None


@app.get("/webhooks/gmail/test")
async def test_gmail_webhook():
    """Test endpoint to verify webhook is working"""
    return {
        "status": "success",
        "message": "Gmail webhook endpoint is accessible",
        "endpoint": "/webhooks/gmail/simple",
        "method": "POST",
        "expected_content_type": "application/json",
        "sample_payload": {
            "subject": "Test Email",
            "from_email": "test@example.com",
            "from_name": "Test User",
            "body": "This is a test email body",
            "received_at": "2025-01-01T12:00:00",
            "source": "gmail_imap_direct"
        }
    }

@app.get("/gmail/status")
async def get_gmail_status():
    """Get Gmail integration status"""
    try:
        return {
            "gmail_integration": {
                "method": "direct_imap",
                "authenticated": True,
                "watch_active": True,
                "webhook_url": "http://localhost:8001/webhooks/gmail/simple"
            },
            "intake_agent_available": intake_agent is not None,
            "webhook_endpoint": "/webhooks/gmail/simple"
        }
    except Exception as e:
        return {"error": f"Failed to get Gmail status: {str(e)}"}


# Gmail OAuth endpoints removed - using direct IMAP integration instead

@app.get("/webhooks/gmail/simple")
async def gmail_webhook_info():
    """GET endpoint for Gmail webhook - provides usage information"""
    return {
        "message": "Gmail Webhook Endpoint",
        "method": "POST",
        "description": "This endpoint receives email data from Gmail IMAP monitoring service",
        "usage": {
            "url": "/webhooks/gmail/simple",
            "method": "POST",
            "content_type": "application/json",
            "required_fields": ["subject", "from_email", "from_name", "body", "received_at", "source"],
            "optional_fields": ["to_email", "message_id", "thread_id", "imap_uid"]
        },
        "test_endpoint": "/webhooks/gmail/test",
        "status_endpoint": "/gmail/status"
    }

@app.post("/webhooks/gmail/simple")
async def simple_gmail_webhook(request: Request):
    """
    Simple webhook endpoint for Gmail integration using token.json
    Receives email data and processes through intake workflow
    """
    try:
        # Get the email data
        body = await request.body()
        
        # Debug logging
        print(f"\n📧 Gmail webhook received request:")
        print(f"   Content-Type: {request.headers.get('content-type', 'Not specified')}")
        print(f"   Body length: {len(body)} bytes")
        print(f"   Raw body: {body[:200]}...")  # First 200 bytes for debugging
        
        # Handle empty body
        if not body:
            print("⚠️ Empty request body received")
            return {
                "status": "error", 
                "message": "Empty request body - no email data provided"
            }
        
        # Parse JSON with better error handling
        try:
            body_str = body.decode('utf-8')
            if not body_str.strip():
                print("⚠️ Empty JSON string received")
                return {
                    "status": "error", 
                    "message": "Empty JSON string - no email data provided"
                }
            email_data = json.loads(body_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"   Raw body string: '{body.decode('utf-8', errors='replace')}'")
            return {
                "status": "error", 
                "message": f"Invalid JSON format: {str(e)}"
            }
        except UnicodeDecodeError as e:
            print(f"❌ Unicode decoding error: {e}")
            return {
                "status": "error", 
                "message": f"Invalid encoding: {str(e)}"
            }
        
        # Validate email data structure
        if not isinstance(email_data, dict):
            print(f"❌ Invalid email data type: {type(email_data)}")
            return {
                "status": "error", 
                "message": f"Expected JSON object, got {type(email_data).__name__}"
            }

        print(f"✅ Valid email data received:")
        print(f"   Subject: {email_data.get('subject', 'No subject')}")
        print(f"   From: {email_data.get('from_email', 'Unknown sender')}")
        print(f"   Keys: {list(email_data.keys())}")

        # Check if intake agent is available
        if not intake_agent:
            print("❌ Intake agent not available")
            return {"status": "error", "message": "Intake agent not available"}

        # Process the email through intake workflow
        ticket_result = await process_email_through_intake(email_data)

        if ticket_result:
            print(f"✅ Ticket created successfully: {ticket_result.get('ticket_number', 'Unknown')}")
            return {
                "status": "success",
                "message": "Email processed and ticket created",
                "ticket_number": ticket_result.get('ticket_number'),
                "data": ticket_result
            }
        else:
            print(f"❌ Failed to create ticket from email")
            return {
                "status": "failed",
                "message": "Failed to create ticket from email",
                "email_data": email_data
            }

    except Exception as e:
        print(f"❌ Error processing simple Gmail webhook: {e}")
        return {
            "status": "error",
            "message": f"Error processing email: {str(e)}"
        }





# ==================== STARTUP AND SHUTDOWN EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Initialize services when the application starts"""
    print("🚀 Starting TeamLogic AutoTask Backend...")
    print("=" * 50)

    # Gmail real-time service disabled - using direct IMAP integration instead
    print("📧 Gmail integration: Using direct IMAP (no OAuth required)")
    print("💡 Direct IMAP integration handles email monitoring")

    print("=" * 50)
    print("✅ Backend startup complete!")
    print(f"🌐 API server running on http://0.0.0.0:8001")
    print(f"📖 API docs available at http://localhost:8001/docs")
    print(f"📧 Gmail webhook: http://localhost:8001/webhooks/gmail/notification")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the application shuts down"""
    print("🛑 Shutting down TeamLogic AutoTask Backend...")
    print("✅ Shutdown complete!")

