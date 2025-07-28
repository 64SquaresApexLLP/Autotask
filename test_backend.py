#!/usr/bin/env python3
"""
Test script to verify the backend and agentic workflow are working correctly.
"""

import sys
import os

# Add the src directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import config
from src.agents.intake_agent import IntakeClassificationAgent
from src.agents.assignment_agent import AssignmentAgentIntegration
from src.agents.notification_agent import NotificationAgent
from src.database.snowflake_db import SnowflakeConnection
from src.data.data_manager import DataManager

def test_database_connection():
    """Test if we can connect to Snowflake"""
    print("🔗 Testing Snowflake connection...")
    try:
        snowflake_conn = SnowflakeConnection(
            account=config.SNOWFLAKE_ACCOUNT,
            user=config.SNOWFLAKE_USER,
            authenticator=config.SNOWFLAKE_AUTHENTICATOR,
            warehouse=config.SNOWFLAKE_WAREHOUSE,
            database=config.SNOWFLAKE_DATABASE,
            schema=config.SNOWFLAKE_SCHEMA,
            role=config.SNOWFLAKE_ROLE
        )
        
        if snowflake_conn.conn:
            print("✅ Snowflake connection successful")
            
            # Test a simple query
            result = snowflake_conn.execute_query("SELECT 1 as test")
            if result:
                print("✅ Database query test successful")
                return snowflake_conn
            else:
                print("❌ Database query test failed")
                return None
        else:
            print("❌ Snowflake connection failed")
            return None
    except Exception as e:
        print(f"❌ Snowflake connection error: {e}")
        return None

def test_agents_initialization():
    """Test if agents can be initialized"""
    print("\n🤖 Testing agents initialization...")
    try:
        # Test data manager
        data_manager = DataManager()
        print("✅ Data manager initialized")
        
        # Test intake agent
        intake_agent = IntakeClassificationAgent(
            sf_account=config.SNOWFLAKE_ACCOUNT,
            sf_user=config.SNOWFLAKE_USER,
            sf_authenticator=config.SNOWFLAKE_AUTHENTICATOR,
            sf_warehouse=config.SNOWFLAKE_WAREHOUSE,
            sf_database=config.SNOWFLAKE_DATABASE,
            sf_schema=config.SNOWFLAKE_SCHEMA,
            sf_role=config.SNOWFLAKE_ROLE,
            data_ref_file=config.DATA_REF_FILE
        )
        print("✅ Intake agent initialized")
        
        # Test assignment agent
        assignment_agent = AssignmentAgentIntegration(db_connection=intake_agent.db_connection)
        print("✅ Assignment agent initialized")
        
        # Test notification agent
        notification_agent = NotificationAgent()
        print("✅ Notification agent initialized")
        
        return intake_agent, assignment_agent, notification_agent
        
    except Exception as e:
        print(f"❌ Agent initialization error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def test_ticket_processing():
    """Test the complete ticket processing workflow"""
    print("\n🎫 Testing ticket processing workflow...")
    
    # Initialize agents
    intake_agent, assignment_agent, notification_agent = test_agents_initialization()
    
    if not intake_agent:
        print("❌ Cannot test ticket processing - agent initialization failed")
        return False
    
    try:
        # Test ticket data
        test_ticket = {
            "ticket_name": "Test User",
            "ticket_description": "My computer won't start. The power button doesn't respond and there are no lights.",
            "ticket_title": "Computer won't start",
            "due_date": "2024-12-31",
            "priority_initial": "High",
            "user_email": "test@company.com"
        }
        
        print(f"Processing test ticket: {test_ticket['ticket_title']}")
        
        # Process the ticket
        result = intake_agent.process_new_ticket(
            ticket_name=test_ticket["ticket_name"],
            ticket_description=test_ticket["ticket_description"],
            ticket_title=test_ticket["ticket_title"],
            due_date=test_ticket["due_date"],
            priority_initial=test_ticket["priority_initial"],
            user_email=test_ticket["user_email"]
        )
        
        if result:
            print("✅ Ticket processing successful")
            print(f"   Ticket Number: {result.get('ticket_number')}")
            print(f"   Priority: {result.get('classified_data', {}).get('PRIORITY', {}).get('Label', 'N/A')}")
            print(f"   Assigned to: {result.get('assignment_result', {}).get('assigned_technician', 'N/A')}")
            return True
        else:
            print("❌ Ticket processing failed - no result returned")
            return False
            
    except Exception as e:
        print(f"❌ Ticket processing error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🧪 Starting Backend and Agentic Workflow Tests")
    print("=" * 50)
    
    # Test database connection
    db_conn = test_database_connection()
    
    # Test agents
    agents_ok = test_agents_initialization()
    
    # Test ticket processing
    if agents_ok[0]:  # If intake agent is OK
        ticket_ok = test_ticket_processing()
    else:
        ticket_ok = False
    
    print("\n" + "=" * 50)
    print("🏁 Test Summary:")
    print(f"   Database Connection: {'✅ PASS' if db_conn else '❌ FAIL'}")
    print(f"   Agent Initialization: {'✅ PASS' if agents_ok[0] else '❌ FAIL'}")
    print(f"   Ticket Processing: {'✅ PASS' if ticket_ok else '❌ FAIL'}")
    
    if db_conn and agents_ok[0] and ticket_ok:
        print("\n🎉 All tests passed! Backend is ready.")
        return True
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
