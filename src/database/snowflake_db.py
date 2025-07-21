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

    def __init__(self, sf_account: str, sf_user: str, sf_warehouse: str,
                 sf_database: str, sf_schema: str, sf_role: str):
        """
        Initialize Snowflake connection parameters for SSO authentication.

        Args:
            sf_account (str): Snowflake account identifier
            sf_user (str): Snowflake username
            sf_warehouse (str): Snowflake warehouse to use
            sf_database (str): Snowflake database to use
            sf_schema (str): Snowflake schema to use
            sf_role (str): Snowflake role to use
        """
        self.sf_account = sf_account
        self.sf_user = sf_user
        self.sf_warehouse = sf_warehouse
        self.sf_database = sf_database
        self.sf_schema = sf_schema
        self.sf_role = sf_role
        self.conn = None

        self._connect_to_snowflake()

    def _connect_to_snowflake(self):
        """Establishes a connection to Snowflake using SSO (externalbrowser) authentication."""
        try:
            # Use SSO authentication with externalbrowser
            connection_params = {
                'user': self.sf_user,
                'account': self.sf_account,
                'authenticator': 'externalbrowser',
                'warehouse': self.sf_warehouse,
                'database': self.sf_database,
                'schema': self.sf_schema,
                'role': self.sf_role
            }

            self.conn = snowflake.connector.connect(**connection_params)
            print("Successfully connected to Snowflake using SSO.")
        except Exception as e:
            error_msg = str(e)
            print(f"Error connecting to Snowflake: {e}")

            # Provide specific guidance for common SSO errors
            if "Failed to connect to DB" in error_msg:
                print("Connection Error: Check your network connection and Snowflake account details.")
            elif "Authentication failed" in error_msg:
                print("SSO Authentication Error: Please ensure you have proper SSO access configured.")
            elif "Browser" in error_msg:
                print("Browser Error: Please ensure your browser can open for SSO authentication.")

            self.conn = None

    def reconnect(self):
        """Reconnect to Snowflake using SSO authentication."""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        self._connect_to_snowflake()
        return self.conn is not None

    def is_connected(self) -> bool:
        """Check if the connection is still active."""
        if not self.conn:
            return False
        try:
            self.conn.cursor().execute("SELECT 1")
            return True
        except:
            return False

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

        if results and len(results) > 0 and 'LLM_RESPONSE' in results[0] and results[0]['LLM_RESPONSE']:
            response_str = results[0]['LLM_RESPONSE']

            if not expect_json:
                # Return raw text response
                return response_str.strip()

            try:
                # Extract JSON block from LLM response
                match = re.search(r'```json\\s*(\\{[\\s\\S]*?\\})\\s*```', response_str)
                if not match:
                    match = re.search(r'```\\s*(\\{[\\s\\S]*?\\})\\s*```', response_str)
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

    # def find_similar_tickets(self, search_conditions: List[str], params: List[str]) -> List[Dict]:
    #     """
    #     Searches for similar tickets based on provided conditions.

    #     Args:
    #         search_conditions (list): List of SQL WHERE conditions
    #         params (list): List of parameters for the conditions

    #     Returns:
    #         list: List of similar tickets
    #     """
    #     where_clause = ""
    #     if search_conditions:
    #         where_clause = "WHERE " + " OR ".join(search_conditions)

    #     query = f"""
    #     SELECT
    #         TITLE,
    #         DESCRIPTION,
    #         ISSUETYPE,
    #         SUBISSUETYPE,
    #         TICKETCATEGORY,
    #         TICKETTYPE,
    #         PRIORITY,
    #         STATUS
    #     FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
    #     {where_clause}
    #     LIMIT 50;
    #     """
        print(f"Searching for similar tickets...")
        return self.execute_query(query, tuple(params))

    def find_similar_tickets_by_embedding(self, ticket_embedding: list, top_n: int = 5) -> List[Dict]:
        """
        Finds the most similar tickets using embedding similarity via Cortex AI_Similarity.
        Args:
            ticket_embedding (list): The embedding vector for the incoming ticket
            top_n (int): Number of top similar tickets to return
        Returns:
            list: List of similar tickets with similarity scores
        """
        if not self.conn:
            print("Not connected to Snowflake. Please check connection.")
            return []

        # Convert embedding to string for SQL
        embedding_str = str(ticket_embedding)
        query = f'''
        SELECT
            TICKET_ID,
            TITLE,
            DESCRIPTION,
            ISSUETYPE,
            SUBISSUETYPE,
            TICKETCATEGORY,
            TICKETTYPE,
            PRIORITY,
            STATUS,
            EMBEDDING,
            SNOWFLAKE.CORTEX.AI_SIMILARITY(EMBEDDING, PARSE_JSON(%s)) AS SIMILARITY
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
        WHERE EMBEDDING IS NOT NULL
        ORDER BY SIMILARITY DESC
        LIMIT {top_n};
        '''
        print(f"Searching for similar tickets using embedding similarity...")
        return self.execute_query(query, (embedding_str,))

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

    def close_connection(self):
        """Close the Snowflake connection."""
        if self.conn:
            self.conn.close()
            print("Snowflake connection closed.")