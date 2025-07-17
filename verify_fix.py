"""
Quick verification script to test that all imports and core functionality work.
"""

import sys
import os

def test_imports():
    """Test that all imports work correctly."""
    print("🧪 Testing Import Fix")
    print("=" * 30)
    
    try:
        # Test main app imports
        print("1. Testing main app imports...")
        import app
        print("   ✅ Main app imports successfully")
        
        # Test core module imports
        print("2. Testing core module imports...")
        from src.core import EmailProcessor, TicketHandlers, PageControllers
        print("   ✅ Core modules import successfully")
        
        # Test email processor specifically
        print("3. Testing EmailProcessor...")
        email_processor = EmailProcessor("test@example.com", "password", "imap.gmail.com")
        print("   ✅ EmailProcessor can be instantiated")
        
        # Test ticket handlers
        print("4. Testing TicketHandlers...")
        kb_data = TicketHandlers.load_kb_data()
        print(f"   ✅ TicketHandlers loaded {len(kb_data)} tickets")
        
        # Test page controllers
        print("5. Testing PageControllers...")
        # Just test that the class exists and has the expected methods
        assert hasattr(PageControllers, 'show_user_dashboard')
        assert hasattr(PageControllers, 'show_technician_dashboard')
        print("   ✅ PageControllers has required methods")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Import test failed: {e}")
        return False

def test_streamlit_startup():
    """Test that Streamlit can start without errors."""
    print("\n🚀 Testing Streamlit Startup")
    print("=" * 30)
    
    try:
        # Import streamlit and key components
        import streamlit as st
        from login import login_page
        print("   ✅ Streamlit and login imports work")
        
        # Test that key functions exist
        import app
        assert hasattr(app, 'main')
        assert hasattr(app, 'get_agent')
        assert hasattr(app, 'fetch_and_process_emails')
        print("   ✅ Main app functions exist")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Streamlit startup test failed: {e}")
        return False

def test_database_connections():
    """Test database connection classes."""
    print("\n🗄️ Testing Database Connections")
    print("=" * 30)
    
    try:
        from src.database.snowflake_db import SnowflakeConnection
        from src.database.ticket_db import TicketDB
        print("   ✅ Database classes import successfully")
        
        # Test TicketDB initialization
        ticket_db = TicketDB()
        print("   ✅ TicketDB can be initialized")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🔧 Import Fix Verification")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_streamlit_startup,
        test_database_connections
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("📊 Verification Results")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! The import fix is successful.")
        print("✅ The application should now run without import errors.")
        print("\n💡 To start the application:")
        print("   streamlit run app.py")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
