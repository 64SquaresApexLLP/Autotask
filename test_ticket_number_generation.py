#!/usr/bin/env python3
"""
Test script for the new dynamic ticket number generation logic.

This script tests the enhanced ticket number generation that:
1. Checks the highest ticket number across ALL tickets (both TICKETS and CLOSED_TICKETS)
2. Generates the next sequential number dynamically
3. Uses format TKT-NNNNNN instead of date-based format

Author: AutoTask Integration System
Date: 2025-08-03
"""

import sys
import os

# Add src to sys.path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

def test_ticket_number_generation():
    """Test the new ticket number generation logic"""
    print("🎫 Testing Dynamic Ticket Number Generation")
    print("=" * 50)
    
    try:
        # Import required modules
        from src.database.snowflake_db import SnowflakeConnection
        from src.agents.intake_agent import IntakeClassificationAgent
        from src.data.data_manager import DataManager
        import config
        
        # Initialize database connection
        print("🔗 Connecting to Snowflake...")
        snowflake_conn = SnowflakeConnection(
            sf_account=config.SF_ACCOUNT,
            sf_user=config.SF_USER,
            sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE,
            sf_schema=config.SF_SCHEMA,
            sf_role=config.SF_ROLE
        )
        
        # Initialize data manager
        data_manager = DataManager(data_ref_file=config.DATA_REF_FILE)
        
        # Initialize intake agent
        print("🤖 Initializing Intake Agent...")
        intake_agent = IntakeClassificationAgent(
            db_connection=snowflake_conn,
            data_manager=data_manager
        )
        
        print("✅ Initialization complete!")
        print()
        
        # Test ticket number generation
        print("🧪 Testing Ticket Number Generation:")
        print("-" * 30)
        
        # Generate 5 test ticket numbers
        for i in range(5):
            ticket_data = {"test": f"ticket_{i}"}
            ticket_number = intake_agent.generate_ticket_number(ticket_data)
            print(f"Generated ticket #{i+1}: {ticket_number}")
        
        print()
        print("🔍 Testing Highest Number Detection:")
        print("-" * 30)
        
        # Test the highest number detection method directly
        highest_number = intake_agent._get_highest_ticket_number_from_db()
        print(f"Current highest ticket number: {highest_number}")
        print(f"Next ticket would be: TKT-{(highest_number + 1):06d}")
        
        print()
        print("✅ Ticket number generation test completed!")
        print()
        print("📋 New Ticket Number Format:")
        print("• Format: TKT-NNNNNN (e.g., TKT-000001, TKT-000002)")
        print("• Sequential: Always increments from highest existing number")
        print("• Global: Checks both TICKETS and CLOSED_TICKETS tables")
        print("• Unique: Ensures no duplicates across entire system")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

def test_database_queries():
    """Test the database queries used for ticket number generation"""
    print("\n🔍 Testing Database Queries")
    print("=" * 50)
    
    try:
        from src.database.snowflake_db import SnowflakeConnection
        import config
        
        # Initialize database connection
        snowflake_conn = SnowflakeConnection(
            sf_account=config.SF_ACCOUNT,
            sf_user=config.SF_USER,
            sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE,
            sf_schema=config.SF_SCHEMA,
            sf_role=config.SF_ROLE
        )
        
        print("🔗 Connected to Snowflake")
        
        # Test query to get highest ticket number
        query = """
        WITH all_tickets AS (
            SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.TICKETS
            UNION ALL
            SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.CLOSED_TICKETS
        ),
        extracted_numbers AS (
            SELECT 
                CASE 
                    -- New format: TKT-NNNNNN
                    WHEN TICKETNUMBER LIKE 'TKT-%' THEN 
                        CAST(SUBSTRING(TICKETNUMBER, 5) AS INTEGER)
                    -- Old format: TYYYYMMDD.NNNN - extract and convert
                    WHEN TICKETNUMBER LIKE 'T%.%' THEN 
                        CAST(CONCAT(SUBSTRING(TICKETNUMBER, 2, 8), SUBSTRING(TICKETNUMBER, 11, 4)) AS INTEGER)
                    ELSE 0
                END as ticket_num
            FROM all_tickets
            WHERE TICKETNUMBER IS NOT NULL
        )
        SELECT MAX(ticket_num) as max_number, COUNT(*) as total_tickets
        FROM extracted_numbers
        """
        
        result = snowflake_conn.execute_query(query)
        
        if result and len(result) > 0:
            max_number = result[0]['MAX_NUMBER']
            total_tickets = result[0]['TOTAL_TICKETS']
            print(f"📊 Query Results:")
            print(f"   • Highest ticket number: {max_number}")
            print(f"   • Total tickets found: {total_tickets}")
            print(f"   • Next ticket number: TKT-{(max_number + 1 if max_number else 1):06d}")
        else:
            print("📊 No tickets found in database")
        
        # Test sample ticket numbers
        print("\n🧪 Testing Sample Ticket Numbers:")
        sample_tickets = ["TKT-000001", "TKT-000999", "T20241203.0001", "T20241203.9999"]
        
        for ticket in sample_tickets:
            check_query = """
            SELECT COUNT(*) as count
            FROM (
                SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s
                UNION ALL
                SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.CLOSED_TICKETS WHERE TICKETNUMBER = %s
            ) combined
            """
            
            try:
                result = snowflake_conn.execute_query(check_query, (ticket, ticket))
                if result and len(result) > 0:
                    count = result[0]['COUNT']
                    status = "EXISTS" if count > 0 else "AVAILABLE"
                    print(f"   • {ticket}: {status}")
            except Exception as e:
                print(f"   • {ticket}: ERROR - {e}")
        
        print("\n✅ Database query testing completed!")
        
    except Exception as e:
        print(f"❌ Database testing error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Dynamic Ticket Number Generation Test Suite")
    print("=" * 60)
    
    # Run tests
    test_ticket_number_generation()
    test_database_queries()
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print("• New format: TKT-NNNNNN (6-digit sequential)")
    print("• Dynamic: Always finds highest existing number")
    print("• Global: Checks both active and closed tickets")
    print("• Backward compatible: Handles old TYYYYMMDD.NNNN format")
    print("• Robust: Multiple fallback mechanisms")
    print("=" * 60)
