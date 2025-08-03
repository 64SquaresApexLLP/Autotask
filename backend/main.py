import sys
import os
from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import hashlib
import hmac
import json
import requests
from datetime import datetime, timedelta
import asyncio
# Email processing imports removed

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

# --- Pydantic Models ---
class TicketCreateRequest(BaseModel):
    title: str
    description: str
    due_date: str
    user_email: Optional[str] = None
    priority: Optional[str] = None
    requester_name: Optional[str] = None

class TicketResponse(BaseModel):
    ticket_number: str
    status: str
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    assigned_technician: Optional[str] = None
    technician_email: Optional[str] = None

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
            TECHNICIANEMAIL, USEREMAIL, USERID, PHONENUMBER, CLOSED_AT, ORIGINAL_CREATED_AT
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
                "user_email": row[12],
                "user_id": row[13],
                "phone_number": row[14],
                "closed_at": str(row[15]) if row[15] else None,
                "original_created_at": str(row[16]) if row[16] else None
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
def get_all_tickets(limit: int = Query(50, le=100), offset: int = 0, status: Optional[str] = None, priority: Optional[str] = None):
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
                TECHNICIANEMAIL, USEREMAIL, USERID, PHONENUMBER, ORIGINAL_CREATED_AT
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """

            # Use updated values or original values
            final_priority = update_request.priority or ticket_dict.get('PRIORITY')
            final_status = update_request.status or ticket_dict.get('STATUS')

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
                ticket_dict.get('USEREMAIL'),
                ticket_dict.get('USERID'),
                ticket_dict.get('PHONENUMBER')
            ))

            # Delete ticket from TICKETS table
            delete_ticket_query = "DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s"
            cursor.execute(delete_ticket_query, (ticket_number,))

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
            user_email=request.user_email
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
                TECHNICIANEMAIL, USEREMAIL, USERID, PHONENUMBER
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            request.user_email or "",
            request.requester_name or "Anonymous",
            None  # PHONENUMBER
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
            technician_email=assignment.get("technician_email", "")
        )

    except Exception as e:
        print(f"❌ Error creating ticket: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}")

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

            # Save ticket to Snowflake database
            try:
                print(f"💾 Saving ticket to Snowflake database...")
                ticket_db.insert_ticket(result)
                print(f"✅ Ticket saved to database: {result.get('ticket_number', 'Unknown')}")
                result['database_saved'] = True
            except Exception as db_error:
                print(f"❌ Failed to save ticket to database: {db_error}")
                result['database_saved'] = False
                result['database_error'] = str(db_error)

            return result
        else:
            return None

    except Exception as e:
        print(f"❌ Error processing email through intake: {e}")
        return None


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


@app.post("/webhooks/gmail/simple")
async def simple_gmail_webhook(request: Request):
    """
    Simple webhook endpoint for Gmail integration using token.json
    Receives email data and processes through intake workflow
    """
    try:
        # Get the email data
        body = await request.body()
        email_data = json.loads(body.decode('utf-8'))

        print(f"\n📧 Simple Gmail webhook received:")
        print(f"   Subject: {email_data.get('subject', 'No subject')}")
        print(f"   From: {email_data.get('from_email', 'Unknown sender')}")

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

