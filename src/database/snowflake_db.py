"""
Database connection and operations module for TeamLogic-AutoTask application.
Handles Snowflake connections and database queries.
"""

import snowflake.connector
import pandas as pd
import re
import json
from typing import List, Dict, Optional


class SnowflakeConnection:
    """
    Manages Snowflake database connections and operations.
    """

    def __init__(self, account: str, user: str, authenticator: str, warehouse: str, database: str, schema: str, role: str):
        self.account = account
        self.user = user
        self.authenticator = authenticator
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        self.role = role
        self.conn = None
        self._connect_to_snowflake()

    def _connect_to_snowflake(self):
        try:
            self.conn = snowflake.connector.connect(
                user=self.user,
                account=self.account,
                authenticator=self.authenticator,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
                role=self.role
            )
            print("Successfully connected to Snowflake.")
        except Exception as e:
            print(f"Error connecting to Snowflake: {e}")
            self.conn = None

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """
        Executes a SQL query on Snowflake and returns the results.

        Args:
            query (str): The SQL query string
            params (tuple, optional): Parameters to pass to the query

        Returns:
            list: A list of dictionaries, where each dictionary represents a row
        """
        if not self.conn:
            print("Not connected to Snowflake. Please check connection.")
            return []

        try:
            with self.conn.cursor(snowflake.connector.DictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except Exception as e:
            print(f"Error executing Snowflake query: {e}")
            return []

    def call_cortex_llm(self, prompt_text: str, model: str = 'mixtral-8x7b', expect_json: bool = True):
        """
        Calls the Snowflake Cortex LLM (CORTEX_COMPLETE) with the given prompt.

        Args:
            prompt_text (str): The prompt to send to the LLM
            model (str): The LLM model to use
            expect_json (bool): Whether to expect and parse JSON response

        Returns:
            dict/str: The parsed JSON response from the LLM, raw string if expect_json=False, or None if failed
        """
        if not self.conn:
            print("Cannot call LLM: Not connected to Snowflake.")
            return None

        import re
        import json

        escaped_prompt_text = prompt_text.replace("'", "''")
        query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped_prompt_text}') AS LLM_RESPONSE;
        """
        print(f"Calling Snowflake Cortex LLM with model: {model}...")
        results = self.execute_query(query)

        if results and results[0]['LLM_RESPONSE']:
            response_str = results[0]['LLM_RESPONSE']

            if not expect_json:
                # Return raw text response
                return response_str.strip()

            try:
                # Extract JSON block from LLM response
                match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', response_str)
                if not match:
                    match = re.search(r'```\s*(\{[\s\S]*?\})\s*```', response_str)
                if match:
                    response_str = match.group(1)
                else:
                    # Try to find the first { ... } block
                    match = re.search(r'(\{[\s\S]*\})', response_str)
                    if match:
                        response_str = match.group(1)

                # Clean JSON by removing comments
                response_str = self._clean_json_response(response_str)
                return json.loads(response_str)
            except json.JSONDecodeError as e:
                print(f"Error decoding LLM response JSON: {e}")
                print(f"Raw LLM response: {results[0]['LLM_RESPONSE']}")
                return None
        return None

    def _clean_json_response(self, json_str: str) -> str:
        """
        Clean JSON response by removing comments and fixing common issues.

        Args:
            json_str (str): Raw JSON string that may contain comments

        Returns:
            str: Cleaned JSON string
        """
        # Remove single-line comments (// comment)
        json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)

        # Remove multi-line comments (/* comment */)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        return json_str.strip()

    def find_similar_tickets(self, search_conditions: List[str], params: List[str]) -> List[Dict]:
        """
        Searches for similar tickets based on provided conditions.

        Args:
            search_conditions (list): List of SQL WHERE conditions
            params (list): List of parameters for the conditions

        Returns:
            list: List of similar tickets
        """
        where_clause = ""
        if search_conditions:
            where_clause = "WHERE " + " OR ".join(search_conditions)

        query = f"""
        SELECT
            TITLE,
            DESCRIPTION,
            ISSUETYPE,
            SUBISSUETYPE,
            TICKETCATEGORY,
            TICKETTYPE,
            PRIORITY,
            STATUS
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
        {where_clause}
        LIMIT 50;
        """
        print(f"Searching for similar tickets...")
        return self.execute_query(query, tuple(params))

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
        results = self.execute_query(query)

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

    def get_all_tickets(self, limit=50, offset=0, status_filter=None, priority_filter=None):
        columns = [
            "TICKETNUMBER", "TITLE", "DESCRIPTION", "DUEDATETIME", "PRIORITY", "STATUS",
            "TECHNICIANEMAIL", "USEREMAIL", "USERID"
        ]
        query = f"SELECT {', '.join(columns)} FROM TEST_DB.PUBLIC.TICKETS"
        filters = []
        params = []
        if status_filter:
            filters.append("STATUS = %s")
            params.append(status_filter)
        if priority_filter:
            filters.append("PRIORITY = %s")
            params.append(priority_filter)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += f" ORDER BY TICKETNUMBER DESC LIMIT {int(limit)} OFFSET {int(offset)}"
        print("DEBUG: Executing query:", query)
        print("DEBUG: With params:", params)
        results = self.execute_query(query, tuple(params) if params else None)
        print("DEBUG: Results:", results)
        return results

    def get_ticket_by_number(self, ticket_number):
        query = "SELECT * FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s"
        result = self.execute_query(query, (ticket_number,))
        return result[0] if result else None

    def get_technician_by_ticket_number(self, ticket_number):
        # Get technician_id from ticket
        ticket = self.get_ticket_by_number(ticket_number)
        if not ticket or 'TECHNICIAN_ID' not in ticket:
            return None
        technician_id = ticket['TECHNICIAN_ID']
        # Get technician details
        query = "SELECT TECHNICIAN_ID, TECHNICIAN_NAME, TECHNICIAN_EMAIL FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA WHERE TECHNICIAN_ID = %s"
        result = self.execute_query(query, (technician_id,))
        return result[0] if result else None

    def get_all_tickets(self, limit: int = 50, offset: int = 0,
                       status_filter: Optional[str] = None,
                       priority_filter: Optional[str] = None) -> List[Dict]:
        """
        Get all tickets with optional filtering and pagination.

        Args:
            limit (int): Maximum number of tickets to return
            offset (int): Number of tickets to skip
            status_filter (str, optional): Filter by status
            priority_filter (str, optional): Filter by priority

        Returns:
            list: List of ticket dictionaries
        """
        if not self.conn:
            print("Not connected to Snowflake. Please check connection.")
            return []

        try:
            # Build WHERE clause for filters
            where_conditions = []
            params = []

            if status_filter:
                where_conditions.append("STATUS = %s")
                params.append(status_filter)

            if priority_filter:
                where_conditions.append("PRIORITY = %s")
                params.append(priority_filter)

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            query = f"""
                SELECT
                    TICKETNUMBER,
                    TITLE,
                    DESCRIPTION,
                    DUEDATETIME,
                    PRIORITY,
                    STATUS,
                    TECHNICIANEMAIL,
                    USEREMAIL,
                    USERID
                FROM TEST_DB.PUBLIC.TICKETS
                {where_clause}
                ORDER BY TICKETNUMBER DESC
                LIMIT {limit} OFFSET {offset}
            """

            return self.execute_query(query, tuple(params) if params else None)

        except Exception as e:
            print(f"Error getting all tickets: {e}")
            return []

    def get_ticket_by_number(self, ticket_number: str) -> Optional[Dict]:
        """
        Get a specific ticket by its ticket number.

        Args:
            ticket_number (str): The ticket number to search for

        Returns:
            dict: Ticket data or None if not found
        """
        if not self.conn:
            print("Not connected to Snowflake. Please check connection.")
            return None

        try:
            query = """
                SELECT
                    TICKETNUMBER,
                    TITLE,
                    DESCRIPTION,
                    DUEDATETIME,
                    PRIORITY,
                    STATUS,
                    TECHNICIANEMAIL,
                    USEREMAIL,
                    USERID
                FROM TEST_DB.PUBLIC.TICKETS
                WHERE TICKETNUMBER = %s
            """

            results = self.execute_query(query, (ticket_number,))
            return results[0] if results else None

        except Exception as e:
            print(f"Error getting ticket by number: {e}")
            return None

    def close_connection(self):
        """Close the Snowflake connection."""
        if self.conn:
            self.conn.close()
            print("Snowflake connection closed.")