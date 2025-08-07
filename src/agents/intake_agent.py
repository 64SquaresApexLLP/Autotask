"""
Main intake classification agent that orchestrates all modules.
This is the main class that provides the same interface as the original monolithic code.
"""

import json
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.database import SnowflakeConnection
from src.data import DataManager
from src.processors import AIProcessor, TicketProcessor
from src.agents.notification_agent import NotificationAgent
from src.agents.assignment_agent import AssignmentAgentIntegration
from src.services.email_listener import EmailListenerService

# Cross-platform file locking mechanism
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    # Use threading.Lock as fallback for Windows
    _file_locks = {}
    _file_locks_lock = threading.Lock()


def _get_file_lock(filename: str) -> threading.Lock:
    """Get or create a file lock for cross-platform compatibility."""
    with _file_locks_lock:
        if filename not in _file_locks:
            _file_locks[filename] = threading.Lock()
        return _file_locks[filename]


class IntakeClassificationAgent:
    """
    An AI Agent for intake and classification of support tickets using Snowflake Cortex.
    This class orchestrates all the modular components to maintain the same functionality.
    """

    def __init__(self, sf_account: str = None, sf_user: str = None, sf_warehouse: str = None,
                 sf_database: str = None, sf_schema: str = None, sf_role: str = None,
                 data_ref_file: str = 'data.txt', db_connection=None, 
                 enable_email_monitoring: bool = False, webhook_url: str = "http://localhost:8001/webhooks/gmail/simple",
                 email_check_interval: int = 30):
        """
        Initializes the agent with Snowflake connection details and loads reference data.
        If db_connection is provided, use it; otherwise, create a new one.
        Uses SSO authentication for Snowflake connection.
        
        Args:
            sf_account: Snowflake account
            sf_user: Snowflake user
            sf_warehouse: Snowflake warehouse
            sf_database: Snowflake database
            sf_schema: Snowflake schema
            sf_role: Snowflake role
            data_ref_file: Reference data file path
            db_connection: Existing database connection
            enable_email_monitoring: Whether to start background email monitoring
            webhook_url: Webhook URL for email processing
            email_check_interval: Email check interval in seconds
        """
        if db_connection is not None:
            self.db_connection = db_connection
        else:
            self.db_connection = SnowflakeConnection(
                sf_account, sf_user, sf_warehouse,
                sf_database, sf_schema, sf_role
            )
        
        self.data_manager = DataManager(data_ref_file)
        self.ai_processor = AIProcessor(self.db_connection, self.data_manager.reference_data)
        self.ticket_processor = TicketProcessor(self.data_manager.reference_data)
        self.notification_agent = NotificationAgent(db_connection=self.db_connection)
        
        google_calendar_credentials_path = "credentials/google-calendar-credentials.json"
        self.assignment_agent = AssignmentAgentIntegration(
            self.db_connection,
            google_calendar_credentials_path=google_calendar_credentials_path
        )
        
        self.conn = self.db_connection.conn
        self.reference_data = self.data_manager.reference_data
        
        # Initialize email monitoring service (optional)
        self.email_listener = None
        if enable_email_monitoring:
            try:
                self.email_listener = EmailListenerService(
                    webhook_url=webhook_url,
                    check_interval=email_check_interval
                )
                
                # Start email monitoring in background
                if self.email_listener.start_monitoring():
                    print("✅ Email monitoring started successfully")
                else:
                    print("⚠️ Email monitoring failed to start - continuing without email integration")
                    self.email_listener = None
            except Exception as e:
                print(f"❌ Failed to initialize email monitoring: {e}")
                print("Continuing without email integration")
                self.email_listener = None
        else:
            print("📧 Email monitoring disabled")
        
        print("IntakeClassificationAgent initialized successfully")

    def generate_ticket_number(self, ticket_data: Dict) -> str:
        """
        Generate a unique ticket number in format TYYYYMMDD.NNNN.
        Finds the highest sequence number for today and increments dynamically.

        Args:
            ticket_data (dict): Ticket information

        Returns:
            str: Unique ticket number in format TYYYYMMDD.NNNN
        """
        now = datetime.now()
        date_part = now.strftime("%Y%m%d")

        # Get next sequential number for today by checking database
        sequence_number = self._get_next_sequence_number_for_date(date_part)

        # Generate ticket number: TYYYYMMDD.NNNN
        ticket_number = f"T{date_part}.{sequence_number:04d}"

        # Double-check uniqueness and retry if needed
        max_retries = 10
        for retry in range(max_retries):
            test_ticket_number = f"T{date_part}.{sequence_number + retry:04d}"
            if self._is_ticket_number_unique(test_ticket_number):
                print(f"Generated unique ticket number: {test_ticket_number}")
                return test_ticket_number
            else:
                print(f"Ticket number {test_ticket_number} already exists, trying next...")

        # If all retries failed, use timestamp-based approach
        timestamp_suffix = int(datetime.now().strftime("%H%M%S"))
        fallback_ticket_number = f"T{date_part}.{timestamp_suffix:04d}"
        print(f"Generated fallback ticket number: {fallback_ticket_number}")
        return fallback_ticket_number

    def _get_next_sequence_number_for_date(self, date_part: str) -> int:
        """
        Get the next sequential number for the given date by checking both TICKETS and CLOSED_TICKETS tables.
        Finds the highest sequence number for today and increments it.

        Args:
            date_part (str): Date in YYYYMMDD format

        Returns:
            int: Next sequential number for the date
        """
        max_attempts = 10

        for attempt in range(max_attempts):
            try:
                query = f"""
                WITH all_tickets AS (
                    SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'T{date_part}.%'
                    UNION ALL
                    SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.CLOSED_TICKETS WHERE TICKETNUMBER LIKE 'T{date_part}.%'
                )
                SELECT MAX(CAST(SUBSTRING(TICKETNUMBER, 11, 4) AS INTEGER)) as max_sequence
                FROM all_tickets
                WHERE TICKETNUMBER IS NOT NULL
                """

                result = self.db_connection.execute_query(query)

                if result and len(result) > 0 and result[0]['MAX_SEQUENCE'] is not None:
                    max_sequence = result[0]['MAX_SEQUENCE']
                    next_sequence = max_sequence + 1 + attempt
                    print(f"Found existing tickets for {date_part}, next sequence: {next_sequence}")
                else:
                    next_sequence = 1 + attempt
                    print(f"No existing tickets for {date_part}, starting with sequence: {next_sequence}")

                test_ticket_number = f"T{date_part}.{next_sequence:04d}"
                if self._is_ticket_number_unique(test_ticket_number):
                    return next_sequence
                else:
                    print(f"Ticket number {test_ticket_number} already exists, trying next...")
                    continue

            except Exception as e:
                print(f"Error querying database for sequence number (attempt {attempt + 1}): {e}")

        print("All database attempts failed, falling back to file-based sequence")
        return self._get_next_sequence_number_fallback(date_part)

    def _get_next_sequence_number_fallback(self, date_part: str) -> int:
        """
        Fallback method using file-based sequence tracking with cross-platform file locking.
        Used when database query fails.

        Args:
            date_part (str): Date in YYYYMMDD format

        Returns:
            int: Next sequential number
        """
        sequence_file = "data/ticket_sequence.json"
        max_attempts = 50

        for attempt in range(max_attempts):
            try:
                os.makedirs("data", exist_ok=True)

                # Cross-platform file locking
                file_lock = _get_file_lock(sequence_file) if not HAS_FCNTL else None
                
                if file_lock:
                    file_lock.acquire()

                try:
                    sequence_data = {}
                    if os.path.exists(sequence_file):
                        try:
                            with open(sequence_file, 'r') as f:
                                if HAS_FCNTL:
                                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                                sequence_data = json.load(f)
                        except (json.JSONDecodeError, FileNotFoundError):
                            sequence_data = {}

                    current_sequence = sequence_data.get(date_part, 0)
                    next_sequence = current_sequence + 1

                    test_ticket_number = f"T{date_part}.{next_sequence:04d}"
                    if self._is_ticket_number_unique(test_ticket_number):
                        sequence_data[date_part] = next_sequence

                        try:
                            with open(sequence_file, 'w') as f:
                                if HAS_FCNTL:
                                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                                json.dump(sequence_data, f, indent=2)
                        except Exception as e:
                            print(f"Warning: Could not save sequence file: {e}")

                        return next_sequence
                    else:
                        sequence_data[date_part] = next_sequence
                        try:
                            with open(sequence_file, 'w') as f:
                                if HAS_FCNTL:
                                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                                json.dump(sequence_data, f, indent=2)
                        except Exception as e:
                            print(f"Warning: Could not save sequence file: {e}")

                        print(f"Ticket number {test_ticket_number} already exists, trying next...")
                        continue

                finally:
                    if file_lock:
                        file_lock.release()

            except Exception as e:
                print(f"Error in fallback sequence generation (attempt {attempt + 1}): {e}")

        # If all attempts failed, return a high number based on current time
        fallback_sequence = int(datetime.now().strftime("%H%M%S")) % 9999 + 1
        print(f"All fallback attempts failed, using timestamp-based sequence: {fallback_sequence}")
        return fallback_sequence

    def _is_ticket_number_unique(self, ticket_number: str) -> bool:
        """
        Check if a ticket number is unique across both TICKETS and CLOSED_TICKETS tables.

        Args:
            ticket_number (str): Ticket number to check

        Returns:
            bool: True if unique, False if already exists
        """
        try:
            # Check both TICKETS and CLOSED_TICKETS tables
            query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s
                UNION ALL
                SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.CLOSED_TICKETS WHERE TICKETNUMBER = %s
            ) combined
            """

            result = self.db_connection.execute_query(query, (ticket_number, ticket_number))

            if result and len(result) > 0:
                count = result[0]['COUNT']
                return count == 0
            else:
                print(f"No result returned for uniqueness check of {ticket_number}, assuming not unique for safety")
                return False

        except Exception as e:
            print(f"Error checking ticket number uniqueness: {e}")
            
            # Fallback: check only TICKETS table if CLOSED_TICKETS doesn't exist
            try:
                fallback_query = """
                SELECT COUNT(*) as count
                FROM TEST_DB.PUBLIC.TICKETS
                WHERE TICKETNUMBER = %s
                """
                result = self.db_connection.execute_query(fallback_query, (ticket_number,))
                if result and len(result) > 0:
                    count = result[0]['COUNT']
                    is_unique = count == 0
                    if not is_unique:
                        print(f"Fallback check: ticket {ticket_number} exists in TICKETS table")
                    return is_unique
            except Exception as e2:
                print(f"Fallback uniqueness check also failed: {e2}")

            # If all queries fail, assume NOT unique for safety to prevent duplicates
            print(f"All uniqueness checks failed for {ticket_number}, assuming NOT unique for safety")
            return False

    def extract_metadata(self, title: str, description: str, model: str = 'llama3-8b') -> Optional[Dict]:
        """
        Extracts structured metadata from the ticket title and description using LLM.
        """
        return self.ai_processor.extract_metadata(title, description, model)

    def find_similar_tickets(self, title: str, description: str, extracted_metadata: Dict) -> List[Dict]:
        """
        Searches the Snowflake database for similar tickets using Snowflake Cortex AI semantic similarity.
        """
        print("Searching for similar tickets using Snowflake Cortex AI semantic similarity...")

        similar_tickets = self._find_similar_tickets_by_metadata(
            title=title,
            description=description,
            top_n=10
        )

        if similar_tickets:
            print(f"Found {len(similar_tickets)} similar tickets based on semantic similarity")
        else:
            print("No similar tickets found based on semantic similarity")

        return similar_tickets

    def _find_similar_tickets_by_metadata(self, title: str, description: str,
                                       main_issue: str = "", affected_system: str = "",
                                       technical_keywords: str = "", error_messages: str = "",
                                       top_n: int = 10) -> List[Dict]:
        """
        Finds similar tickets using Snowflake Cortex AI semantic similarity matching.

        This method leverages Snowflake's native AI_SIMILARITY() function to find
        semantically similar tickets based on the combined title and description text,
        rather than using traditional keyword-based pattern matching.

        Args:
            title (str): New ticket title
            description (str): New ticket description
            main_issue (str): Main issue description (legacy parameter, optional)
            affected_system (str): Affected system/application (legacy parameter, optional)
            technical_keywords (str): Technical keywords (legacy parameter, optional)
            error_messages (str): Error messages (legacy parameter, optional)
            top_n (int): Number of similar tickets to return (max 10)

        Returns:
            list: List of similar tickets ordered by semantic similarity score (highest first)
        """
        if not self.db_connection.conn:
            print("Not connected to Snowflake. Please check connection.")
            return []

        new_ticket_text = f"{title.strip()} {description.strip()}".strip()

        if not new_ticket_text:
            print("No ticket text provided for similarity search.")
            return []

        escaped_ticket_text = new_ticket_text.replace("'", "''")

        query = f"""
        SELECT
            TITLE,
            DESCRIPTION,
            SNOWFLAKE.CORTEX.AI_SIMILARITY(
                COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, ''),
                '{escaped_ticket_text}'
            ) AS SIMILARITY_SCORE
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
        WHERE TITLE IS NOT NULL
        AND DESCRIPTION IS NOT NULL
        AND TRIM(TITLE) != ''
        AND TRIM(DESCRIPTION) != ''
        AND LENGTH(TRIM(TITLE || ' ' || DESCRIPTION)) > 10
        ORDER BY SIMILARITY_SCORE DESC
        LIMIT {min(top_n, 10)}
        """

        print(f"Searching for top {min(top_n, 10)} semantically similar tickets using Snowflake Cortex AI...")
        print(f"New ticket text: '{new_ticket_text[:100]}{'...' if len(new_ticket_text) > 100 else ''}'")

        try:
            results = self.db_connection.execute_query(query)

            if results:
                print(f"Found {len(results)} similar tickets based on semantic similarity")

                # Log similarity scores for debugging
                for i, ticket in enumerate(results[:3]):
                    score = ticket.get('SIMILARITY_SCORE', 'N/A')
                    title_preview = ticket.get('TITLE', 'N/A')[:50]
                    if isinstance(score, (int, float)):
                        print(f"  #{i+1}: Score={score:.4f}, Title='{title_preview}...'")
                    else:
                        print(f"  #{i+1}: Score={score}, Title='{title_preview}...'")

                # Filter results by minimum similarity threshold
                min_similarity_threshold = 0.1
                filtered_results = []

                for ticket in results:
                    score = ticket.get('SIMILARITY_SCORE')
                    if isinstance(score, (int, float)) and score >= min_similarity_threshold:
                        filtered_results.append(ticket)
                    elif not isinstance(score, (int, float)):
                        # Include tickets where score couldn't be calculated
                        filtered_results.append(ticket)

                if filtered_results:
                    print(f"After filtering by similarity threshold ({min_similarity_threshold}): {len(filtered_results)} tickets")
                    return filtered_results
                else:
                    print(f"No tickets met minimum similarity threshold of {min_similarity_threshold}")
                    return []
            else:
                print("No similar tickets found using semantic similarity")
                return []

        except Exception as e:
            print(f"Error in semantic similarity search: {e}")
            print("Falling back to recent tickets...")
            return []

    def classify_ticket(self, new_ticket_data: Dict, extracted_metadata: Dict,
                       similar_tickets: List[Dict], model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Classifies the new ticket based on extracted metadata and similar tickets using LLM.
        """
        return self.ai_processor.classify_ticket(new_ticket_data, extracted_metadata, similar_tickets, model)

    def generate_resolution_note(self, ticket_data: Dict, classified_data: Dict,
                               extracted_metadata: Dict, model: str = 'mixtral-8x7b') -> str:
        """
        Generates a resolution note using Cortex LLM.
        """
        try:
            return self.ai_processor.generate_resolution_note(ticket_data, classified_data, extracted_metadata, model)
        except TypeError:
            return self.ai_processor.generate_resolution_note(ticket_data, classified_data, extracted_metadata)

    def process_new_ticket(self, ticket_name: str, ticket_description: str, ticket_title: str,
                          due_date: str, priority_initial: str, user_email: Optional[str] = None,
                          user_id: Optional[str] = None, phone_number: Optional[str] = None,
                          extract_model: str = 'llama3-8b', classify_model: str = 'mixtral-8x7b', 
                          resolution_model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Orchestrates the entire process for a new incoming ticket.

        Args:
            ticket_name (str): Name of the person raising the ticket.
            ticket_description (str): Description of the issue.
            ticket_title (str): Title of the ticket.
            due_date (str): Due date for the ticket (e.g., "YYYY-MM-DD").
            priority_initial (str): Initial priority set by the user (e.g., "Medium").
            user_email (str, optional): User's email address for notifications.
            user_id (str, optional): User's unique identifier.
            phone_number (str, optional): User's phone number.
            extract_model (str): Model to use for metadata extraction.
            classify_model (str): Model to use for classification.
            resolution_model (str): Model to use for resolution note generation.

        Returns:
            dict: The classified ticket data, or None if the process fails.
        """
        print(f"\n--- Processing New Ticket: '{ticket_title}' ---")

        creation_time = datetime.now()
        ticket_date = creation_time.strftime("%Y-%m-%d")
        ticket_time = creation_time.strftime("%H:%M:%S")

        new_ticket_raw = {
            "name": ticket_name,
            "description": ticket_description,
            "title": ticket_title,
            "date": ticket_date,
            "time": ticket_time,
            "due_date": due_date,
            "priority": priority_initial
        }

        # Generate unique ticket number
        ticket_number = self.generate_ticket_number(new_ticket_raw)

        # Extract metadata
        extracted_metadata = self.extract_metadata(ticket_title, ticket_description, model=extract_model)
        if not extracted_metadata:
            print("Failed to extract metadata. Aborting ticket processing.")
            return None
        
        print("Extracted Metadata:")
        print(json.dumps(extracted_metadata, indent=2))

        # Find similar tickets using semantic similarity
        similar_tickets = self.find_similar_tickets(ticket_title, ticket_description, extracted_metadata)
        if similar_tickets:
            print(f"\nFound {len(similar_tickets)} similar tickets:")
            for i, ticket in enumerate(similar_tickets):
                issue_type_label = self.reference_data.get('issuetype', {}).get(str(ticket.get('ISSUETYPE')), 'N/A')
                priority_label = self.reference_data.get('priority', {}).get(str(ticket.get('PRIORITY')), 'N/A')
                print(f"  {i+1}. Title: {ticket.get('TITLE', 'N/A')}, Type: {issue_type_label}, Priority: {priority_label}")
        else:
            print("\nNo similar tickets found.")

        # Classify ticket
        classified_data = self.classify_ticket(new_ticket_raw, extracted_metadata, similar_tickets, model=classify_model)
        if not classified_data:
            print("Failed to classify ticket. Aborting ticket processing.")
            return None
        
        print("\nClassified Ticket Data:")
        print(json.dumps(classified_data, indent=2))

        # Generate resolution note
        print("\n--- Generating Resolution Note ---")
        resolution_note = self.generate_resolution_note(new_ticket_raw, classified_data, extracted_metadata, model=resolution_model)
        print("Generated Resolution Note:")
        print(resolution_note)

        # Prepare final ticket data
        final_ticket_data = {
            **new_ticket_raw,
            "ticket_number": ticket_number,
            "user_email": user_email if user_email and user_email.strip() else "",
            "user_id": user_id if user_id and user_id.strip() else "",
            "phone_number": phone_number if phone_number and phone_number.strip() else "",
            "extracted_metadata": extracted_metadata,
            "classified_data": classified_data,
            "resolution_note": resolution_note
        }

        # Process assignment after classification
        print("\n--- Processing Ticket Assignment ---")
        try:
            assignment_result = self.assignment_agent.process_ticket_assignment({"new_ticket": final_ticket_data})
            final_ticket_data["assignment_result"] = assignment_result.get("assignment_result", {})
            print("Assignment Result:")
            print(json.dumps(assignment_result, indent=2))
        except Exception as e:
            print(f"❌ Assignment failed: {e}")
            # Continue processing even if assignment fails
            final_ticket_data["assignment_result"] = {
                "status": "Assignment Failed",
                "error": str(e),
                "assigned_technician": "IT Manager",
                "technician_email": "itmanager@company.com"
            }

        # Send comprehensive notifications
        print(f"\n--- Sending Notifications ---")

        # Send customer confirmation email
        if user_email and user_email.strip():
            print(f"Sending confirmation email to customer: {user_email}")
            confirmation_sent = self.notification_agent.send_ticket_confirmation(
                user_email=user_email,
                ticket_data=final_ticket_data,
                ticket_number=ticket_number
            )
            if confirmation_sent:
                print("✅ Customer confirmation email sent successfully")
            else:
                print("❌ Failed to send customer confirmation email")

        # Send assignment notifications (technician, customer update, manager if needed)
        assignment_notifications = self.notification_agent.send_assignment_notifications(final_ticket_data)

        # Log notification results
        for notification_type, success in assignment_notifications.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"{status}: {notification_type.replace('_', ' ').title()}")

        print(f"\n--- Ticket Processing Complete (#{ticket_number}) ---")
        return final_ticket_data

    def start_email_monitoring(self, webhook_url: str = "http://localhost:8001/webhooks/gmail/simple",
                              check_interval: int = 30) -> bool:
        """
        Start email monitoring service if not already running.
        
        Args:
            webhook_url: Webhook URL for email processing
            check_interval: Email check interval in seconds
            
        Returns:
            bool: True if monitoring started successfully
        """
        if self.email_listener and self.email_listener.is_running():
            print("Email monitoring already running")
            return True
        
        try:
            if not self.email_listener:
                self.email_listener = EmailListenerService(
                    webhook_url=webhook_url,
                    check_interval=check_interval
                )
            
            if self.email_listener.start_monitoring():
                print("Email monitoring started successfully")
                return True
            else:
                print("Failed to start email monitoring")
                return False
                
        except Exception as e:
            print(f"Error starting email monitoring: {e}")
            return False

    def stop_email_monitoring(self):
        """
        Stop email monitoring service gracefully.
        """
        if self.email_listener:
            self.email_listener.stop_monitoring()
            print("Email monitoring stopped")
        else:
            print("Email monitoring was not running")

    def get_email_monitoring_status(self) -> Dict:
        """
        Get status of email monitoring service.
        
        Returns:
            Dict: Email monitoring status information
        """
        if self.email_listener:
            return self.email_listener.get_status()
        else:
            return {
                "is_monitoring": False,
                "is_running": False,
                "email_address": None,
                "webhook_url": None,
                "check_interval": None,
                "processed_emails": 0,
                "consecutive_failures": 0,
                "has_app_password": False,
                "connected_to_gmail": False,
                "error": "Email listener not initialized"
            }

    def __del__(self):
        """
        Cleanup when agent is destroyed.
        """
        try:
            if hasattr(self, 'email_listener') and self.email_listener:
                self.email_listener.stop_monitoring()
        except:
            pass