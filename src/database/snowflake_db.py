"""
Database connection module for TeamLogic-AutoTask application.
Handles Snowflake connections and basic database operations only.
Business logic has been moved to appropriate agent files.
"""

import os
import snowflake.connector
import re
import json
from typing import List, Dict, Optional


class SnowflakeConnection:
    """
    Manages Snowflake database connections and basic operations.

    This class is responsible for:
    - Establishing and managing Snowflake connections
    - Executing SQL queries
    - Calling Snowflake Cortex LLM services
    - Connection health checks and reconnection

    Business logic methods have been moved to appropriate agent files:
    - Similarity search methods -> IntakeClassificationAgent
    - Resolution generation -> Future NoteAgent
    - Assignment logic -> AssignmentAgent
    """

    def __init__(self, sf_account: str, sf_user: str, sf_warehouse: str,
                 sf_database: str, sf_schema: str, sf_role: str,
                 sf_password: str = None, sf_authenticator: str = None,
                 sf_passcode: str = None):
        """
        Initialize Snowflake connection parameters.

        Args:
            sf_account (str): Snowflake account identifier
            sf_user (str): Snowflake username
            sf_warehouse (str): Snowflake warehouse to use
            sf_database (str): Snowflake database to use
            sf_schema (str): Snowflake schema to use
            sf_role (str): Snowflake role to use
            sf_password (str, optional): Password, used when sf_authenticator is not 'externalbrowser'
            sf_authenticator (str): 'externalbrowser' for SSO, or 'snowflake' for username/password
            sf_passcode (str, optional): MFA passcode if required
        """
        import os
        self.sf_account = sf_account
        self.sf_user = sf_user
        self.sf_warehouse = sf_warehouse
        self.sf_database = sf_database
        self.sf_schema = sf_schema
        self.sf_role = sf_role
        self.sf_password = sf_password
        self.sf_authenticator = sf_authenticator or os.getenv('SF_AUTHENTICATOR', os.getenv('SNOWFLAKE_AUTHENTICATOR', 'externalbrowser'))
        self.sf_passcode = sf_passcode
        self.conn = None

        self._connect_to_snowflake()

    def _connect_to_snowflake(self):
        """Establishes a connection to Snowflake supporting MFA (TOTP, Duo Push, Cached MFA token, or SSO)."""
        try:
            # Determine authenticator
            auth = self.sf_authenticator or os.getenv('SF_AUTHENTICATOR', 'snowflake')
            if auth not in ['snowflake', 'username_password_mfa', 'externalbrowser']:
                auth = 'snowflake'

            connection_params = {
                'user': self.sf_user,
                'account': self.sf_account,
                'authenticator': auth,
                'warehouse': self.sf_warehouse,
                'database': self.sf_database,
                'schema': self.sf_schema,
                'role': self.sf_role,
                'client_request_mfa_token': True,
                'client_store_temporary_credential': True
            }

            if auth != 'externalbrowser':
                connection_params['password'] = self.sf_password

            # Passcode for TOTP / MFA
            passcode = self.sf_passcode or os.getenv('SF_PASSCODE') or os.getenv('SNOWFLAKE_PASSCODE')
            if passcode:
                connection_params['passcode'] = str(passcode).strip()
            else:
                # Allows passcode appended to password or cached token
                connection_params['passcode_in_password'] = False

            self.conn = snowflake.connector.connect(**connection_params)
            print(f"[SUCCESS] Connected to Snowflake (authenticator: {auth}).")
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Connecting to Snowflake: {e}")

            if "MFA with TOTP is required" in error_msg:
                print("[MFA] Snowflake MFA required: Enter your 6-digit TOTP code in SF_PASSCODE.")
            elif "Failed to connect to DB" in error_msg:
                print("[ERROR] Connection: Check your network connection and Snowflake account details.")
            elif "Authentication failed" in error_msg:
                print("[ERROR] Authentication: Please check your credentials.")

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

    def call_cortex_llm(self, prompt_text: str, model: str = 'llama3.1-70b', expect_json: bool = True):
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

    def close_connection(self):
        """Close the Snowflake connection."""
        if self.conn:
            self.conn.close()
            print("Snowflake connection closed.")