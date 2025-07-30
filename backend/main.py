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
from datetime import datetime
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
from src.database.ticket_db import TicketDB
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

# Initialize TicketDB with the snowflake connection
ticket_db = TicketDB(conn=snowflake_conn)

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
    try:
        # Use TicketDB to get all tickets
        all_tickets = ticket_db.get_all_tickets()

        # Apply filtering if specified
        if status:
            all_tickets = [t for t in all_tickets if t.get('STATUS', '').lower() == status.lower()]
        if priority:
            all_tickets = [t for t in all_tickets if t.get('PRIORITY', '').lower() == priority.lower()]

        # Apply pagination
        start_idx = offset
        end_idx = offset + limit
        paginated_tickets = all_tickets[start_idx:end_idx]

        return paginated_tickets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tickets: {str(e)}")

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

# --- WEBHOOK ENDPOINTS ---

# Configuration for webhook security
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-key")
AUTOTASK_WEBHOOK_URL = os.getenv("AUTOTASK_WEBHOOK_URL", "https://your-autotask-instance.com/api/webhooks")

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

        # Convert webhook data to our internal ticket format
        ticket_request = TicketCreateRequest(
            title=webhook_data.title,
            description=webhook_data.description,
            due_date=webhook_data.due_date,
            priority=webhook_data.priority,
            user_email=webhook_data.requester_email,
            requester_name=webhook_data.requester_name
        )

        # Process through our agentic workflow
        print(f"🚀 Processing Autotask ticket through AI workflow: {webhook_data.title}")

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

async def send_assignment_to_autotask(ticket_id: str, assignment_result: Dict, full_result: Dict) -> bool:
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
                "notification": "/webhooks/autotask/notification"
            },
            "security": {
                "signature_verification": bool(WEBHOOK_SECRET),
                "cors_enabled": True
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

