"""
Main intake classification agent that orchestrates all modules.
This is the main class that provides the same interface as the original monolithic code.
"""

import json
import uuid
import hashlib
import os
# Email processing imports removed
# Removed: threading, time, schedule (no longer needed for webhook processing)
# pytz removed - no longer needed
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database import SnowflakeConnection
from src.data import DataManager
from src.processors import AIProcessor, TicketProcessor
from src.agents.notification_agent import NotificationAgent
from src.agents.assignment_agent import AssignmentAgentIntegration


class IntakeClassificationAgent:
    """
    An AI Agent for intake and classification of support tickets using Snowflake Cortex.
    This class orchestrates all the modular components to maintain the same functionality.
    """

    def __init__(self, sf_account: str = None, sf_user: str = None, sf_warehouse: str = None,
                 sf_database: str = None, sf_schema: str = None, sf_role: str = None,
                 data_ref_file: str = 'data.txt', db_connection=None):
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
            email_account: Email account for intake processing
            email_password: Email password for intake processing
            imap_server: IMAP server for email intake
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
        # Check if credentials file exists, if not, assignment agent will work without calendar integration
        self.assignment_agent = AssignmentAgentIntegration(
            self.db_connection,
            google_calendar_credentials_path=google_calendar_credentials_path
        )
        self.conn = self.db_connection.conn
        self.reference_data = self.data_manager.reference_data
        
        # Email processing removed - no longer processing emails
        print("📧 Email processing: Disabled - no longer processing emails")

    def generate_ticket_number(self, ticket_data: Dict) -> str:
        """
        Generate a unique ticket number in format TYYYYMMDD.NNNN.
        Finds the highest sequence number for today and increments dynamically.

        Args:
            ticket_data (dict): Ticket information

        Returns:
            str: Unique ticket number in format TYYYYMMDD.NNNN
        """
        # Get current timestamp
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
                # Query both tables to find the highest sequence number for today
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
                    next_sequence = max_sequence + 1 + attempt  # Add attempt to avoid collisions
                    print(f"Found existing tickets for {date_part}, next sequence: {next_sequence}")
                else:
                    next_sequence = 1 + attempt
                    print(f"No existing tickets for {date_part}, starting with sequence: {next_sequence}")

                # Test if this number would be unique
                test_ticket_number = f"T{date_part}.{next_sequence:04d}"
                if self._is_ticket_number_unique(test_ticket_number):
                    return next_sequence
                else:
                    print(f"Ticket number {test_ticket_number} already exists, trying next...")
                    continue

            except Exception as e:
                print(f"Error querying database for sequence number (attempt {attempt + 1}): {e}")

        # If all attempts failed, fallback to file-based sequence
        print("All database attempts failed, falling back to file-based sequence")
        return self._get_next_sequence_number_fallback(date_part)

    def _get_next_sequence_number_fallback(self, date_part: str) -> int:
        """
        Fallback method using file-based sequence tracking with uniqueness check.
        Used when database query fails.

        Args:
            date_part (str): Date in YYYYMMDD format

        Returns:
            int: Next sequential number
        """
        import fcntl  # For file locking
        sequence_file = "data/ticket_sequence.json"
        max_attempts = 50

        for attempt in range(max_attempts):
            try:
                # Ensure data directory exists
                os.makedirs("data", exist_ok=True)

                # Load existing sequence data with file locking
                sequence_data = {}
                if os.path.exists(sequence_file):
                    try:
                        with open(sequence_file, 'r') as f:
                            fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                            sequence_data = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError):
                        sequence_data = {}

                # Get current sequence for this date, default to 0
                current_sequence = sequence_data.get(date_part, 0)

                # Increment sequence
                next_sequence = current_sequence + 1

                # Test if this number would be unique
                test_ticket_number = f"T{date_part}.{next_sequence:04d}"
                if self._is_ticket_number_unique(test_ticket_number):
                    # Update sequence data with exclusive lock
                    sequence_data[date_part] = next_sequence

                    try:
                        with open(sequence_file, 'w') as f:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                            json.dump(sequence_data, f, indent=2)
                    except Exception as e:
                        print(f"Warning: Could not save sequence file: {e}")

                    return next_sequence
                else:
                    # If not unique, update the file with a higher number and try again
                    sequence_data[date_part] = next_sequence
                    try:
                        with open(sequence_file, 'w') as f:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                            json.dump(sequence_data, f, indent=2)
                    except Exception as e:
                        print(f"Warning: Could not save sequence file: {e}")

                    print(f"Ticket number {test_ticket_number} already exists, trying next...")
                    continue

            except Exception as e:
                print(f"Error in fallback sequence generation (attempt {attempt + 1}): {e}")

        # If all attempts failed, return a high number based on current time
        from datetime import datetime
        return int(datetime.now().strftime("%H%M%S")) % 9999 + 1

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
                return True  # If query fails, assume unique

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
                    return count == 0
            except Exception as e2:
                print(f"Fallback uniqueness check also failed: {e2}")

            return True  # If all queries fail, assume unique

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

        # Use the internal method to find similar tickets with semantic similarity
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

        # Combine title and description for the new ticket
        new_ticket_text = f"{title.strip()} {description.strip()}".strip()

        if not new_ticket_text:
            print("No ticket text provided for similarity search.")
            return []

        # Escape single quotes for SQL
        escaped_ticket_text = new_ticket_text.replace("'", "''")

        # Use Snowflake Cortex AI_SIMILARITY for semantic matching
        # Note: AI_SIMILARITY returns values between 0 and 1, where 1 is most similar
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
                for i, ticket in enumerate(results[:3]):  # Show top 3 scores
                    score = ticket.get('SIMILARITY_SCORE', 'N/A')
                    title = ticket.get('TITLE', 'N/A')[:50]
                    if isinstance(score, (int, float)):
                        print(f"  #{i+1}: Score={score:.4f}, Title='{title}...'")
                    else:
                        print(f"  #{i+1}: Score={score}, Title='{title}...'")

                # Filter results by minimum similarity threshold
                # AI_SIMILARITY typically returns values between 0 and 1
                min_similarity_threshold = 0.1  # Adjust this threshold as needed
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
                          extract_model: str = 'llama3-8b', classify_model: str = 'mixtral-8x7b', resolution_model: str = 'mixtral-8x7b') -> Optional[Dict]:
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

    # Email processing methods removed - no longer processing emails
