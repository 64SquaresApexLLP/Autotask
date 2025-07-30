"""
Test script to verify that the Submit New Ticket page is working correctly.
"""

import sys
import os
import streamlit as st

def test_page_controllers_import():
    """Test that PageControllers can be imported and has the main_page method."""
    print("🧪 Testing PageControllers Import")
    print("=" * 40)
    
    try:
        from src.core.page_controllers import PageControllers
        print("✅ PageControllers imported successfully")
        
        # Check if main_page method exists
        assert hasattr(PageControllers, 'main_page'), "main_page method not found"
        print("✅ main_page method exists")
        
        # Check if helper methods exist
        assert hasattr(PageControllers, '_display_ticket_results'), "_display_ticket_results method not found"
        assert hasattr(PageControllers, '_display_about_section'), "_display_about_section method not found"
        assert hasattr(PageControllers, '_display_email_processing_section'), "_display_email_processing_section method not found"
        print("✅ All helper methods exist")
        
        return True
        
    except Exception as e:
        print(f"❌ PageControllers import failed: {e}")
        return False

def test_config_imports():
    """Test that required config constants are available."""
    print("\n🔧 Testing Config Imports")
    print("=" * 40)
    
    try:
        from config import PAGE_TITLE, PRIORITY_OPTIONS
        print(f"✅ PAGE_TITLE: {PAGE_TITLE}")
        print(f"✅ PRIORITY_OPTIONS: {PRIORITY_OPTIONS}")
        
        # Verify PRIORITY_OPTIONS is a list
        assert isinstance(PRIORITY_OPTIONS, list), "PRIORITY_OPTIONS should be a list"
        assert len(PRIORITY_OPTIONS) > 0, "PRIORITY_OPTIONS should not be empty"
        print("✅ PRIORITY_OPTIONS is valid")
        
        return True
        
    except Exception as e:
        print(f"❌ Config imports failed: {e}")
        return False

def test_ticket_handlers_import():
    """Test that TicketHandlers can be imported and used."""
    print("\n📋 Testing TicketHandlers Import")
    print("=" * 40)
    
    try:
        from src.core.ticket_handlers import TicketHandlers
        print("✅ TicketHandlers imported successfully")
        
        # Test load_kb_data method
        kb_data = TicketHandlers.load_kb_data()
        print(f"✅ Loaded {len(kb_data)} tickets from knowledgebase")
        
        return True
        
    except Exception as e:
        print(f"❌ TicketHandlers import failed: {e}")
        return False

def test_app_functions_import():
    """Test that required app functions can be imported."""
    print("\n🔗 Testing App Functions Import")
    print("=" * 40)
    
    try:
        from app import (
            validate_email, start_automatic_email_processing,
            stop_automatic_email_processing, fetch_and_process_emails,
            EMAIL_PROCESSING_STATUS
        )
        print("✅ All required app functions imported")
        
        # Test validate_email function
        assert validate_email("test@example.com") == True, "validate_email should return True for valid email"
        assert validate_email("invalid-email") == False, "validate_email should return False for invalid email"
        print("✅ validate_email function works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ App functions import failed: {e}")
        return False

def test_streamlit_compatibility():
    """Test that the page can work with Streamlit."""
    print("\n🌐 Testing Streamlit Compatibility")
    print("=" * 40)
    
    try:
        import streamlit as st
        print("✅ Streamlit imported successfully")
        
        # Test that we can import the main components
        from src.core.page_controllers import PageControllers
        from src.core.ticket_handlers import TicketHandlers
        print("✅ All components compatible with Streamlit")
        
        return True
        
    except Exception as e:
        print(f"❌ Streamlit compatibility test failed: {e}")
        return False

def main():
    """Run all tests to verify the Submit New Ticket fix."""
    print("🔧 Submit New Ticket Page Fix Verification")
    print("=" * 60)
    
    tests = [
        test_page_controllers_import,
        test_config_imports,
        test_ticket_handlers_import,
        test_app_functions_import,
        test_streamlit_compatibility
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! The Submit New Ticket page should now work correctly.")
        print("✅ The page should display the full ticket submission form.")
        print("✅ Users should be able to submit tickets and see results.")
        print("\n💡 To verify:")
        print("   1. Open the application: streamlit run app.py")
        print("   2. Login with user credentials (U001 / Pass@001)")
        print("   3. Navigate to the Home page")
        print("   4. You should see the complete ticket submission form")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the errors above.")
        print("The Submit New Ticket page may not work correctly.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
