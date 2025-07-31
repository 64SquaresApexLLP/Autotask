#!/usr/bin/env python3
"""
Test script to debug the classification issue.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.intake_agent import IntakeClassificationAgent
import config

def test_classification():
    """Test the classification functionality directly."""
    print("Testing classification functionality...")
    
    # Initialize the intake agent
    try:
        intake_agent = IntakeClassificationAgent(
            sf_account=config.SF_ACCOUNT,
            sf_user=config.SF_USER,
            sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE,
            sf_schema=config.SF_SCHEMA,
            sf_role=config.SF_ROLE,
            data_ref_file='data/reference_data.txt'
        )
        print("✅ Intake agent initialized successfully")
        
        # Test with a printer issue
        print("\n--- Testing Printer Issue ---")
        result = intake_agent.process_new_ticket(
            ticket_name="Test User",
            ticket_description="My printer is showing an error and won't print documents",
            ticket_title="Printer not working",
            due_date="2024-12-31",
            priority_initial="Medium"
        )
        
        if result:
            print("✅ Ticket processing successful")
            print(f"Ticket number: {result.get('ticket_number')}")
            print(f"Classified data: {result.get('classified_data')}")
        else:
            print("❌ Ticket processing failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_classification() 