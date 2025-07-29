import sys
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

# Add src to sys.path for agent/database imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, 'src')

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from src modules
from src.agents.intake_agent import IntakeClassificationAgent
from src.agents.assignment_agent import AssignmentAgentIntegration
from src.agents.notification_agent import NotificationAgent
from src.database.snowflake_db import SnowflakeConnection
from src.data.data_manager import DataManager

app = FastAPI(title="TeamLogic AutoTask API", description="Backend API for TeamLogic AutoTask System", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
import config

# --- DATABASE CONNECTION ---
snowflake_conn = SnowflakeConnection(
    sf_account=config.SF_ACCOUNT,
    sf_user=config.SF_USER,
    sf_warehouse=config.SF_WAREHOUSE,
    sf_database=config.SF_DATABASE,
    sf_schema=config.SF_SCHEMA,
    sf_role=config.SF_ROLE
)

# --- AGENTS & DATA MANAGER ---
# Fix path for reference data file when running from backend directory
import os
project_root = os.path.dirname(os.path.abspath(__file__))  # backend directory
parent_dir = os.path.dirname(project_root)  # project root directory
reference_data_path = os.path.join(parent_dir, config.DATA_REF_FILE)

data_manager = DataManager(data_ref_file=reference_data_path)
assignment_agent = AssignmentAgentIntegration(db_connection=snowflake_conn)
notification_agent = NotificationAgent()
intake_agent = IntakeClassificationAgent(
    sf_account=config.SF_ACCOUNT,
    sf_user=config.SF_USER,
    sf_warehouse=config.SF_WAREHOUSE,
    sf_database=config.SF_DATABASE,
    sf_schema=config.SF_SCHEMA,
    sf_role=config.SF_ROLE,
    data_ref_file=reference_data_path
)
intake_agent.assignment_agent = assignment_agent
intake_agent.notification_agent = notification_agent
intake_agent.reference_data = data_manager.reference_data

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

# --- API Endpoints ---
@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Specific ticket endpoints (must come before parameterized routes) ---

@app.get("/tickets/count")
def get_tickets_count():
    """Get total count of tickets"""
    try:
        query = "SELECT COUNT(*) as total_tickets FROM TEST_DB.PUBLIC.TICKETS"
        result = snowflake_conn.execute_query(query)
        return {"total_tickets": result[0]["TOTAL_TICKETS"] if result else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tickets count: {str(e)}")

@app.get("/tickets/stats")
def get_tickets_stats():
    """Get ticket statistics by status and priority"""
    try:
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
    results = snowflake_conn.get_all_tickets(limit=limit, offset=offset, status_filter=status, priority_filter=priority)
    return results

@app.get("/tickets/{ticket_number}")
def get_ticket(ticket_number: str):
    ticket = snowflake_conn.get_ticket_by_number(ticket_number)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@app.get("/tickets/{ticket_number}/technician", response_model=TechnicianResponse)
def get_technician(ticket_number: str):
    # Get ticket first to get technician email
    ticket = snowflake_conn.get_ticket_by_number(ticket_number)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    technician_email = ticket.get('TECHNICIANEMAIL')
    if not technician_email:
        raise HTTPException(status_code=404, detail="No technician assigned to this ticket")

    return TechnicianResponse(
        technician_email=technician_email,
        assigned_technician=technician_email,  # Using email as name for now
        ticket_number=ticket_number
    )

@app.post("/tickets", status_code=201, response_model=TicketResponse)
def create_ticket(request: TicketCreateRequest):
    try:
        print(f"🎫 Creating ticket with title: {request.title}")

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

        insert_result = snowflake_conn.execute_query(insert_query, params)
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
        test_query = "SELECT 1 as test"
        db_result = snowflake_conn.execute_query(test_query)
        db_status = "connected" if db_result else "disconnected"

        return {
            "status": "ok",
            "database": db_status,
            "agents": {
                "intake_agent": "initialized" if intake_agent else "not_initialized",
                "assignment_agent": "initialized" if assignment_agent else "not_initialized",
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
        # Check if TICKETS table exists and get its structure
        describe_query = "DESCRIBE TABLE TEST_DB.PUBLIC.TICKETS"
        result = snowflake_conn.execute_query(describe_query)
        return {"table_structure": result}
    except Exception as e:
        # If table doesn't exist, try to create it
        try:
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