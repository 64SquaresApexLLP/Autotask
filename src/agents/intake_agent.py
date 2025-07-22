"""
Main intake classification agent that orchestrates all modules.
This is the main class that provides the same interface as the original monolithic code.
"""

import json
import uuid
import hashlib
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

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
        self.notification_agent = NotificationAgent()
        google_calendar_credentials_path = "credentials/google-calendar-credentials.json"
        # Check if credentials file exists, if not, assignment agent will work without calendar integration
        self.assignment_agent = AssignmentAgentIntegration(
            self.db_connection,
            google_calendar_credentials_path=google_calendar_credentials_path
        )
        self.conn = self.db_connection.conn
        self.reference_data = self.data_manager.reference_data

    def generate_ticket_number(self, ticket_data: Dict) -> str:
        """
        Generate a unique ticket number in format T20240916.0057

        Args:
            ticket_data (dict): Ticket information

        Returns:
            str: Unique ticket number in format TYYYYMMDD.NNNN
        """
        # Get current timestamp
        now = datetime.now()
        date_part = now.strftime("%Y%m%d")

        # Get next sequential number for today
        sequence_number = self._get_next_sequence_number(date_part)

        # Generate ticket number: TYYYYMMDD.NNNN
        ticket_number = f"T{date_part}.{sequence_number:04d}"

        print(f"Generated ticket number: {ticket_number}")
        return ticket_number

    def _get_next_sequence_number(self, date_part: str) -> int:
        """
        Get the next sequential number for the given date.

        Args:
            date_part (str): Date in YYYYMMDD format

        Returns:
            int: Next sequential number
        """
        sequence_file = "data/ticket_sequence.json"

        # Load existing sequence data
        sequence_data = {}
        if os.path.exists(sequence_file):
            try:
                with open(sequence_file, 'r') as f:
                    sequence_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                sequence_data = {}

        # Get current sequence for this date, default to 0
        current_sequence = sequence_data.get(date_part, 0)

        # Increment sequence
        next_sequence = current_sequence + 1

        # Update sequence data
        sequence_data[date_part] = next_sequence

        # Save updated sequence data
        try:
            with open(sequence_file, 'w') as f:
                json.dump(sequence_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save sequence file: {e}")

        return next_sequence

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
            TICKETNUMBER,
            TITLE,
            DESCRIPTION,
            ISSUETYPE,
            SUBISSUETYPE,
            TICKETCATEGORY,
            TICKETTYPE,
            PRIORITY,
            STATUS,
            RESOLUTION,
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
                    # Try a hybrid approach with keyword matching for better results
                    return self._hybrid_similarity_search(new_ticket_text, top_n)
            else:
                print("No similar tickets found using semantic similarity")
                return self._hybrid_similarity_search(new_ticket_text, top_n)

        except Exception as e:
            print(f"Error in semantic similarity search: {e}")
            print("Falling back to hybrid search...")
            return self._hybrid_similarity_search(new_ticket_text, top_n)

    def _hybrid_similarity_search(self, ticket_text: str, top_n: int = 10) -> List[Dict]:
        """
        Hybrid approach combining semantic similarity with keyword matching for better results.

        Args:
            ticket_text (str): Combined title and description text
            top_n (int): Number of tickets to return

        Returns:
            list: List of similar tickets
        """
        print("Using hybrid similarity search (semantic + keyword matching)...")

        # Extract key terms from the ticket text for keyword matching
        import re
        # Remove common stop words and extract meaningful terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'cannot', 'not', 'no', 'yes', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'a', 'an'}

        # Extract meaningful keywords (length > 3, not stop words)
        words = re.findall(r'\b\w+\b', ticket_text.lower())
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]

        if not keywords:
            # Fallback to recent tickets if no keywords found
            return self._get_recent_tickets(top_n)

        # Take top 5 most relevant keywords
        keywords = keywords[:5]
        print(f"Using keywords for hybrid search: {keywords}")

        # Build hybrid query combining semantic similarity with keyword matching
        escaped_ticket_text = ticket_text.replace("'", "''")
        keyword_conditions = []

        for keyword in keywords:
            escaped_keyword = keyword.replace("'", "''")
            keyword_conditions.append(f"(UPPER(TITLE) LIKE UPPER('%{escaped_keyword}%') OR UPPER(DESCRIPTION) LIKE UPPER('%{escaped_keyword}%'))")

        keyword_filter = " OR ".join(keyword_conditions)

        query = f"""
        SELECT
            TICKETNUMBER,
            TITLE,
            DESCRIPTION,
            ISSUETYPE,
            SUBISSUETYPE,
            TICKETCATEGORY,
            TICKETTYPE,
            PRIORITY,
            STATUS,
            RESOLUTION,
            SNOWFLAKE.CORTEX.AI_SIMILARITY(
                COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, ''),
                '{escaped_ticket_text}'
            ) AS SIMILARITY_SCORE
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
        WHERE TITLE IS NOT NULL
        AND DESCRIPTION IS NOT NULL
        AND TRIM(TITLE) != ''
        AND TRIM(DESCRIPTION) != ''
        AND ({keyword_filter})
        ORDER BY SIMILARITY_SCORE DESC
        LIMIT {min(top_n * 2, 20)}
        """

        try:
            results = self.db_connection.execute_query(query)
            if results:
                print(f"Hybrid search found {len(results)} tickets")
                # Return top N results
                return results[:top_n]
            else:
                print("Hybrid search found no results, falling back to recent tickets")
                return self._get_recent_tickets(top_n)
        except Exception as e:
            print(f"Error in hybrid search: {e}")
            return self._get_recent_tickets(top_n)

    def _get_recent_tickets(self, top_n: int = 10) -> List[Dict]:
        """
        Fallback method to get recent tickets when similarity search fails.

        Args:
            top_n (int): Number of tickets to return

        Returns:
            list: List of recent tickets
        """
        print("Falling back to recent tickets...")
        query = f"""
        SELECT
            TICKETNUMBER,
            TITLE,
            DESCRIPTION,
            ISSUETYPE,
            SUBISSUETYPE,
            TICKETCATEGORY,
            TICKETTYPE,
            PRIORITY,
            STATUS,
            RESOLUTION
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
        WHERE TITLE IS NOT NULL AND DESCRIPTION IS NOT NULL
        ORDER BY TICKETNUMBER DESC
        LIMIT {min(top_n, 10)}
        """
        return self.db_connection.execute_query(query) or []

    def fetch_reference_tickets(self) -> pd.DataFrame:
        """
        Fetches actual historical tickets with real, detailed resolutions.

        Returns:
            pd.DataFrame: DataFrame containing historical tickets with resolutions
        """

        query = """
            SELECT TITLE, DESCRIPTION, ISSUETYPE, SUBISSUETYPE, PRIORITY, RESOLUTION
            FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
            WHERE RESOLUTION IS NOT NULL
            AND RESOLUTION != ''
            AND RESOLUTION != 'N/A'
            AND RESOLUTION != 'None'
            AND RESOLUTION NOT LIKE '%contact%'
            AND RESOLUTION NOT LIKE '%escalate%'
            AND RESOLUTION NOT LIKE '%call%'
            AND LENGTH(RESOLUTION) > 50
            AND TITLE IS NOT NULL
            AND DESCRIPTION IS NOT NULL
            AND LENGTH(TITLE) > 10
            AND LENGTH(DESCRIPTION) > 20
            ORDER BY LENGTH(RESOLUTION) DESC, RANDOM()
            LIMIT 200
        """
        print("Fetching actual historical tickets with real resolutions...")
        results = self.db_connection.execute_query(query)

        if results:
            df = pd.DataFrame(results)
            print(f"Fetched {len(df)} historical tickets")

            # Additional filtering for actual technical resolutions
            df = df[df['RESOLUTION'].str.len() > 50]

            # Filter out generic responses
            generic_patterns = [
                'please try', 'contact support', 'escalate to', 'call helpdesk',
                'generic solution', 'standard procedure', 'follow up with'
            ]

            for pattern in generic_patterns:
                df = df[~df['RESOLUTION'].str.contains(pattern, case=False, na=False)]

            # Keep only resolutions with actual technical content
            technical_indicators = [
                'restart', 'configure', 'install', 'update', 'check', 'verify',
                'run', 'execute', 'open', 'close', 'delete', 'create', 'modify',
                'setting', 'option', 'parameter', 'file', 'folder', 'registry',
                'service', 'process', 'application', 'system'
            ]

            technical_mask = df['RESOLUTION'].str.contains('|'.join(technical_indicators), case=False, na=False)
            df = df[technical_mask]

            print(f"After filtering for actual technical resolutions: {len(df)} tickets available")

            return df
        else:
            print("No historical tickets found")
            return pd.DataFrame()

    def classify_ticket(self, new_ticket_data: Dict, extracted_metadata: Dict,
                       similar_tickets: List[Dict], model: str = 'mixtral-8x7b') -> Optional[Dict]:
        """
        Classifies the new ticket based on extracted metadata and similar tickets using LLM.
        """
        return self.ai_processor.classify_ticket(new_ticket_data, extracted_metadata, similar_tickets, model)

    def generate_resolution_note(self, ticket_data: Dict, classified_data: Dict,
                               extracted_metadata: Dict) -> str:
        """
        Generates a resolution note using Cortex LLM.
        """
        return self.ai_processor.generate_resolution_note(ticket_data, classified_data, extracted_metadata)

    # Note: save_to_knowledgebase method removed - tickets are now saved directly to database

    def process_new_ticket(self, ticket_name: str, ticket_description: str, ticket_title: str,
                          due_date: str, priority_initial: str, user_email: Optional[str] = None,
                          user_id: Optional[str] = None, phone_number: Optional[str] = None,
                          extract_model: str = 'llama3-8b', classify_model: str = 'mixtral-8x7b') -> Optional[Dict]:
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
        resolution_note = self.generate_resolution_note(new_ticket_raw, classified_data, extracted_metadata)
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

        # Note: Knowledgebase saving removed - tickets are now saved directly to database

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