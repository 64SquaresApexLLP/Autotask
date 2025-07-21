import os
from src.database.snowflake_db import SnowflakeConnection
from config import *
import json

class TicketDB:
    def __init__(self, conn=None):
        if conn is not None:
            self.conn = conn
        else:
            self.conn = SnowflakeConnection(
                sf_account=SF_ACCOUNT,
                sf_user=SF_USER,
                sf_warehouse=SF_WAREHOUSE,
                sf_database=SF_DATABASE,
                sf_schema=SF_SCHEMA,
                sf_role=SF_ROLE
            )

    def insert_ticket(self, ticket_data: dict):
        """Insert ticket data into the database with proper field mapping."""
        # Map the ticket data from agent format to database format
        mapped_data = self._map_ticket_data_for_db(ticket_data)

        query = '''
        INSERT INTO TEST_DB.PUBLIC.TICKETS (
            TITLE, DESCRIPTION, TICKETTYPE, TICKETNUMBER, TICKETCATEGORY,
            ISSUETYPE, SUBISSUETYPE, DUEDATETIME, RESOLUTION, USERID,
            USEREMAIL, TECHNICIANEMAIL, PHONENUMBER
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        '''
        # Convert to tuple in the correct order
        values = (
            mapped_data['TITLE'], mapped_data['DESCRIPTION'], mapped_data['TICKETTYPE'],
            mapped_data['TICKETNUMBER'], mapped_data['TICKETCATEGORY'], mapped_data['ISSUETYPE'],
            mapped_data['SUBISSUETYPE'], mapped_data['DUEDATETIME'], mapped_data['RESOLUTION'],
            mapped_data['USERID'], mapped_data['USEREMAIL'], mapped_data['TECHNICIANEMAIL'],
            mapped_data['PHONENUMBER']
        )
        self.conn.execute_query(query, values)

    def _map_ticket_data_for_db(self, ticket_data: dict) -> dict:
        """Map ticket data from agent format to database column format."""
        from datetime import datetime

        # Get classified data and assignment result
        classified_data = ticket_data.get('classified_data', {})
        assignment_result = ticket_data.get('assignment_result', {})

        # Extract values from classified data (which may have Label/Value structure)
        def extract_value(data, key, default=''):
            if key in data:
                if isinstance(data[key], dict) and 'Label' in data[key]:
                    return data[key]['Label']
                elif isinstance(data[key], dict) and 'Value' in data[key]:
                    return data[key]['Value']
                return data[key]
            return default

        # Map the data to match the required database schema
        mapped_data = {
            'TITLE': ticket_data.get('title', ''),
            'DESCRIPTION': ticket_data.get('description', ''),
            'TICKETTYPE': extract_value(classified_data, 'TICKETTYPE', 'Support'),
            'TICKETNUMBER': ticket_data.get('ticket_number', ''),
            'TICKETCATEGORY': extract_value(classified_data, 'TICKETCATEGORY', 'General'),
            'ISSUETYPE': extract_value(classified_data, 'ISSUETYPE', 'Other'),
            'SUBISSUETYPE': extract_value(classified_data, 'SUBISSUETYPE', 'General'),
            'DUEDATETIME': ticket_data.get('due_date', ''),
            'RESOLUTION': ticket_data.get('resolution_note', ''),
            'USERID': ticket_data.get('user_id', ''),
            'USEREMAIL': ticket_data.get('user_email', ''),
            'TECHNICIANEMAIL': assignment_result.get('technician_email', ''),
            'PHONENUMBER': ticket_data.get('phone_number', '')
        }

        return mapped_data

    def get_tickets_for_technician(self, technician_email: str):
        """Get all tickets assigned to a specific technician."""
        query = '''
        SELECT * FROM TEST_DB.PUBLIC.TICKETS
        WHERE TECHNICIANEMAIL = %s
        ORDER BY TICKETNUMBER DESC
        '''
        return self.conn.execute_query(query, (technician_email,))

    def get_all_tickets(self):
        """Get all tickets from the database."""
        query = '''
        SELECT * FROM TEST_DB.PUBLIC.TICKETS
        ORDER BY TICKETNUMBER DESC
        '''
        return self.conn.execute_query(query)

    def get_tickets_by_status(self, status: str):
        """Get tickets by status (if status column exists)."""
        # Note: Status is not in the required schema, but keeping for compatibility
        query = '''
        SELECT * FROM TEST_DB.PUBLIC.TICKETS
        ORDER BY TICKETNUMBER DESC
        '''
        return self.conn.execute_query(query)

    def update_ticket_assignment(self, ticket_number: str, technician_email: str):
        query = '''
        UPDATE TEST_DB.PUBLIC.TICKETS SET TECHNICIANEMAIL = %s WHERE TICKETNUMBER = %s
        '''
        self.conn.execute_query(query, (technician_email, ticket_number))

    def get_tickets_for_user(self, user_id: str):
        query = '''
        SELECT * FROM TEST_DB.PUBLIC.TICKETS WHERE USERID = %s
        '''
        return self.conn.execute_query(query, (user_id,))

    def get_tickets_for_technician(self, technician_email: str):
        query = '''
        SELECT * FROM TEST_DB.PUBLIC.TICKETS WHERE TECHNICIANEMAIL = %s
        '''
        return self.conn.execute_query(query, (technician_email,))

    def get_technician_by_email(self, email: str):
        query = '''
        SELECT * FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA WHERE EMAIL = %s
        '''
        results = self.conn.execute_query(query, (email,))
        return results[0] if results else None

    def update_ticket_status(self, ticket_number: str, status: str):
        query = '''
        UPDATE TEST_DB.PUBLIC.TICKETS SET STATUS = %s WHERE TICKETNUMBER = %s
        '''
        self.conn.execute_query(query, (status, ticket_number))

    def add_work_note(self, ticket_number: str, note: str):
        # Fetch current notes
        query_select = '''
        SELECT WORK_NOTES FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s
        '''
        result = self.conn.execute_query(query_select, (ticket_number,))
        notes = []
        if result and result[0].get('WORK_NOTES'):
            try:
                notes = json.loads(result[0]['WORK_NOTES'])
            except Exception:
                notes = []
        from datetime import datetime
        notes.append({'note': note, 'time': datetime.now().isoformat()})
        notes_json = json.dumps(notes)
        query_update = '''
        UPDATE TEST_DB.PUBLIC.TICKETS SET WORK_NOTES = %s WHERE TICKETNUMBER = %s
        '''
        self.conn.execute_query(query_update, (notes_json, ticket_number)) 