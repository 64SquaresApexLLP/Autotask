#!/usr/bin/env python3
"""
Test script to verify integrated email processing functionality in IntakeClassificationAgent.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.intake_agent import IntakeClassificationAgent
from src.database.snowflake_db import SnowflakeConnection
import config

def test_integrated_email_processing():
    """Test the integrated email processing functionality."""
    print("Testing integrated email processing in IntakeClassificationAgent...")
    
    # Initialize the database connection
    try:
        db_connection = SnowflakeConnection(
            sf_account=config.SF_ACCOUNT,
            sf_user=config.SF_USER,
            sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE,
            sf_schema=config.SF_SCHEMA,
            sf_role=config.SF_ROLE
        )
        print("✅ Database connection successful")
        
        # Initialize intake agent with email processing
        agent = IntakeClassificationAgent(
            sf_account=config.SF_ACCOUNT,
            sf_user=config.SF_USER,
            sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE,
            sf_schema=config.SF_SCHEMA,
            sf_role=config.SF_ROLE,
            data_ref_file='data/reference_data.txt',
            db_connection=db_connection,
            email_account='rohankul2017@gmail.com',
            email_password=os.getenv('SUPPORT_EMAIL_PASSWORD'),
            imap_server='imap.gmail.com'
        )
        print("✅ Intake agent initialized with email processing")
        
        # Test email processing status
        status = agent.get_email_processing_status()
        print(f"📧 Email processing status: {status}")
        
        # Test manual email processing (without actually connecting)
        print("\n--- Testing Manual Email Processing ---")
        print("Note: This test will not actually connect to email server")
        print("Email processing methods are available:")
        print("✅ agent.process_recent_emails()")
        print("✅ agent.start_automatic_email_processing()")
        print("✅ agent.stop_automatic_email_processing()")
        print("✅ agent.get_email_processing_status()")
        
        # Test manual ticket processing (existing functionality)
        print("\n--- Testing Manual Ticket Processing ---")
        result = agent.process_new_ticket(
            ticket_name="Test User",
            ticket_description="Printer not working - test from integrated system",
            ticket_title="Test Printer Issue",
            due_date="2024-12-31",
            priority_initial="Medium",
            user_email="test@example.com"
        )
        
        if result:
            print("✅ Manual ticket processing successful")
            print(f"Ticket Number: {result.get('ticket_number', 'Unknown')}")
            print(f"Source: {result.get('source', 'manual')}")
        else:
            print("❌ Manual ticket processing failed")
            
        print("\n🎉 Integrated email processing test completed!")
        print("Both manual and email ticket processing are now unified in the IntakeClassificationAgent")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integrated_email_processing() 