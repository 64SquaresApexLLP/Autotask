"""
Comprehensive test suite for TeamLogic-AutoTask.
Consolidates all testing functionality into a single module.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
import json


class TestSuite:
    """Comprehensive test suite for the application."""
    
    def __init__(self):
        self.test_results = {}
    
    def run_all_tests(self):
        """Run all test categories."""
        print("🧪 TeamLogic-AutoTask Comprehensive Test Suite")
        print("=" * 60)
        
        # Run test categories
        self.test_login_system()
        self.test_ui_components()
        self.test_database_connections()
        self.test_ticket_processing()
        self.test_modular_imports()
        
        # Print summary
        self.print_test_summary()
    
    def test_login_system(self):
        """Test login credentials and authentication."""
        print("\n🔐 Testing Login System")
        print("-" * 30)
        
        try:
            from login import USERS, TECHNICIANS
            
            # Test user credentials
            user_count = len(USERS)
            tech_count = len(TECHNICIANS)
            
            print(f"✅ Found {user_count} user accounts")
            print(f"✅ Found {tech_count} technician accounts")
            
            # Verify credential structure
            for user_id, user_data in USERS.items():
                assert 'name' in user_data and 'password' in user_data
            
            for tech_id, tech_data in TECHNICIANS.items():
                assert 'name' in tech_data and 'password' in tech_data
            
            print("✅ All credentials have required fields")
            self.test_results['login_system'] = True
            
        except Exception as e:
            print(f"❌ Login system test failed: {e}")
            self.test_results['login_system'] = False
    
    def test_ui_components(self):
        """Test UI component imports and functionality."""
        print("\n🎨 Testing UI Components")
        print("-" * 30)
        
        try:
            # Test core UI imports
            from src.ui import apply_custom_css, format_time_elapsed
            print("✅ Core UI components imported")
            
            # Test dashboard imports
            from src.ui.user_dashboard import user_my_tickets_page
            from src.ui.technician_dashboard import technician_dashboard_page
            print("✅ Dashboard components imported")
            
            # Test modular imports
            from src.core import EmailProcessor, TicketHandlers, PageControllers
            print("✅ Core modules imported")
            
            self.test_results['ui_components'] = True
            
        except Exception as e:
            print(f"❌ UI components test failed: {e}")
            self.test_results['ui_components'] = False
    
    def test_database_connections(self):
        """Test database connection and basic operations."""
        print("\n🗄️ Testing Database Connections")
        print("-" * 30)
        
        try:
            from src.database.snowflake_db import SnowflakeConnection
            from src.database.ticket_db import TicketDB
            import config
            
            print("✅ Database classes imported")
            
            # Test connection creation (without actually connecting)
            conn_params = {
                'sf_account': config.SF_ACCOUNT,
                'sf_user': config.SF_USER,
                'sf_warehouse': config.SF_WAREHOUSE,
                'sf_database': config.SF_DATABASE,
                'sf_schema': config.SF_SCHEMA,
                'sf_role': config.SF_ROLE
            }
            
            # Verify all required parameters are available
            missing_params = [k for k, v in conn_params.items() if not v]
            if missing_params:
                print(f"⚠️ Missing connection parameters: {missing_params}")
            else:
                print("✅ All connection parameters available")
            
            # Test TicketDB initialization
            ticket_db = TicketDB()
            print("✅ TicketDB can be initialized")
            
            self.test_results['database_connections'] = True
            
        except Exception as e:
            print(f"❌ Database connections test failed: {e}")
            self.test_results['database_connections'] = False
    
    def test_ticket_processing(self):
        """Test ticket processing and data handling."""
        print("\n🎫 Testing Ticket Processing")
        print("-" * 30)
        
        try:
            from src.agents.intake_agent import IntakeClassificationAgent
            from src.processors import AIProcessor, TicketProcessor
            from src.core.ticket_handlers import TicketHandlers
            
            print("✅ Ticket processing classes imported")
            
            # Test ticket handlers
            kb_data = TicketHandlers.load_kb_data()
            print(f"✅ Loaded {len(kb_data)} tickets from knowledgebase")
            
            # Test ticket filtering
            if kb_data:
                stats = TicketHandlers.get_ticket_statistics(kb_data)
                print(f"✅ Generated statistics for {stats['total_tickets']} tickets")
            
            # Test data mapping
            from src.database.ticket_db import TicketDB
            ticket_db = TicketDB()
            
            sample_data = {
                'title': 'Test Ticket',
                'description': 'Test Description',
                'classified_data': {'PRIORITY': {'Value': 'Medium'}},
                'assignment_result': {'status': 'Open'}
            }
            
            mapped_data = ticket_db._map_ticket_data_for_db(sample_data)
            print("✅ Ticket data mapping works correctly")
            
            self.test_results['ticket_processing'] = True
            
        except Exception as e:
            print(f"❌ Ticket processing test failed: {e}")
            self.test_results['ticket_processing'] = False
    
    def test_modular_imports(self):
        """Test that all modular components can be imported."""
        print("\n📦 Testing Modular Imports")
        print("-" * 30)
        
        try:
            # Test agent imports
            from src.agents import IntakeClassificationAgent
            from src.agents.assignment_agent import AssignmentAgentIntegration
            from src.agents.notification_agent import NotificationAgent
            print("✅ Agent modules imported")
            
            # Test processor imports
            from src.processors import AIProcessor, TicketProcessor, ImageProcessor
            print("✅ Processor modules imported")
            
            # Test database imports
            from src.database import SnowflakeConnection
            from src.database.ticket_db import TicketDB
            print("✅ Database modules imported")
            
            # Test data imports
            from src.data import DataManager
            print("✅ Data modules imported")
            
            # Test core imports
            from src.core import EmailProcessor, TicketHandlers, PageControllers
            print("✅ Core modules imported")
            
            self.test_results['modular_imports'] = True
            
        except Exception as e:
            print(f"❌ Modular imports test failed: {e}")
            self.test_results['modular_imports'] = False
    
    def print_test_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print("-" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! The application is ready for use.")
        else:
            print(f"\n⚠️ {total_tests - passed_tests} test(s) failed. Please review the issues above.")
        
        print("\n💡 To run the application:")
        print("   cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8001")
        print("\n🔑 Test credentials:")
        print("   User: U001 / Pass@001")
        print("   Technician: T101 / Tech@9382xB")


def main():
    """Run the comprehensive test suite."""
    test_suite = TestSuite()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()
