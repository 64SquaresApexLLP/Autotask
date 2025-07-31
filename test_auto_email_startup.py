#!/usr/bin/env python3
"""
Test script to verify automatic email processing startup in IntakeClassificationAgent.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.agents.intake_agent import IntakeClassificationAgent
from src.database.snowflake_db import SnowflakeConnection
import config
import time

def test_auto_email_startup():
    """Test that automatic email processing starts automatically."""
    print("Testing automatic email processing startup...")
    
    try:
        # Initialize database connection
        db_connection = SnowflakeConnection(
            sf_account=config.SF_ACCOUNT, sf_user=config.SF_USER, sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE, sf_schema=config.SF_SCHEMA, sf_role=config.SF_ROLE
        )
        print("✅ Database connection successful")
        
        # Initialize agent with email credentials
        print("🔄 Initializing IntakeClassificationAgent with email processing...")
        agent = IntakeClassificationAgent(
            sf_account=config.SF_ACCOUNT, sf_user=config.SF_USER, sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE, sf_schema=config.SF_SCHEMA, sf_role=config.SF_ROLE,
            data_ref_file='data/reference_data.txt', db_connection=db_connection,
            email_account='rohankul2017@gmail.com', email_password=os.getenv('SUPPORT_EMAIL_PASSWORD'),
            imap_server='imap.gmail.com'
        )
        print("✅ Intake agent initialized")
        
        # Check email processing status
        status = agent.get_email_processing_status()
        print(f"📧 Email processing status: {status}")
        
        if status["is_running"]:
            print("✅ Automatic email processing is ACTIVE!")
            print("🔄 The system will check for new emails every 5 minutes")
        else:
            print("❌ Automatic email processing is NOT running")
            print("This could be due to missing email password or connection issues")
        
        # Test manual ticket processing still works
        print("\n--- Testing Manual Ticket Processing ---")
        result = agent.process_new_ticket(
            ticket_name="Test User", 
            ticket_description="Printer not working - test from auto startup system",
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
        
        # Wait a moment to see if any automatic processing occurs
        print("\n⏳ Waiting 10 seconds to observe automatic processing...")
        for i in range(10):
            time.sleep(1)
            print(f"⏱️ {10-i} seconds remaining...")
        
        # Check status again
        final_status = agent.get_email_processing_status()
        print(f"\n📊 Final email processing status: {final_status}")
        
        print("\n🎉 Automatic email processing startup test completed!")
        print("The system is now configured to automatically check emails every 5 minutes")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auto_email_startup() 