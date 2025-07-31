#!/usr/bin/env python3
"""
Simple test to verify classification fix.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.processors.ai_processor import AIProcessor
from src.database.snowflake_db import SnowflakeConnection
import config

def test_classification():
    """Test the classification functionality directly."""
    print("Testing classification fix...")
    
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
        
        # Initialize AI processor with reference data
        from src.data.data_manager import DataManager
        data_manager = DataManager('data/reference_data.txt')
        ai_processor = AIProcessor(db_connection, data_manager.reference_data)
        print("✅ AI processor initialized")
        
        # Test data
        new_ticket_data = {
            "title": "Printer not working",
            "description": "My printer is showing an error and won't print documents",
            "priority": "Medium"
        }
        
        extracted_metadata = {
            "main_issue": "Printer not working",
            "affected_system": "Printer",
            "urgency_level": "Medium",
            "error_messages": "Error and won't print documents",
            "technical_keywords": ["printer", "error", "printing"],
            "user_actions": "Trying to print documents",
            "resolution_indicators": "Printer driver issue or paper jam"
        }
        
        similar_tickets = []  # Empty for this test
        
        # Test classification
        print("\n--- Testing Classification ---")
        result = ai_processor.classify_ticket(new_ticket_data, extracted_metadata, similar_tickets)
        
        if result:
            print("✅ Classification successful")
            print("Result:")
            for field, data in result.items():
                if isinstance(data, dict):
                    print(f"  {field}: {data.get('Value', 'N/A')} ({data.get('Label', 'N/A')})")
                else:
                    print(f"  {field}: {data}")
        else:
            print("❌ Classification failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_classification() 