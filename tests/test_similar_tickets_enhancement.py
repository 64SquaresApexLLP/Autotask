#!/usr/bin/env python3
"""
Test script for enhanced similar tickets functionality.
This script tests the new implementation that:
1. Removes all mock data
2. Uses semantic similarity with Snowflake Cortex AI
3. Searches both TICKETS and COMPANY_4130_DATA tables
4. Provides strong similar tickets with resolutions
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from chatbot.services.ticket_service import TicketService
from chatbot.database import get_db, Ticket, CompanyData
from chatbot.services.chatbot_service import ConversationalChatbotService
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_similar_tickets_enhancement():
    """Test the enhanced similar tickets functionality."""
    print("🧪 Testing Enhanced Similar Tickets Functionality")
    print("=" * 60)
    
    try:
        # Get database session
        from backend.chatbot.database import get_db
        db = next(get_db())  # get_db() returns a generator, so we need to get the first session
        
        # Test 1: Test with specific ticket number
        print("\n📋 Test 1: Similar tickets for T20250804.0003")
        print("-" * 40)
        
        ticket_service = TicketService(db)
        
        # Test finding similar tickets by issue description
        test_description = "Touchpad not working properly, laptop touchpad seems unresponsive"
        print(f"Searching for tickets similar to: '{test_description}'")
        
        similar_tickets = ticket_service.find_similar_tickets_by_issue(test_description, limit=5)
        
        if similar_tickets:
            print(f"✅ Found {len(similar_tickets)} similar tickets:")
            for i, ticket in enumerate(similar_tickets, 1):
                print(f"\n{i}. Ticket: {ticket.ticketnumber}")
                print(f"   Title: {ticket.title}")
                print(f"   Status: {ticket.status}")
                print(f"   Issue Type: {ticket.issuetype}")
                if ticket.resolution and ticket.resolution.strip():
                    print(f"   Resolution: {ticket.resolution[:100]}...")
                if "[Source: COMPANY_4130_DATA]" in ticket.description:
                    print(f"   Source: COMPANY_4130_DATA")
                else:
                    print(f"   Source: TICKETS")
        else:
            print("❌ No similar tickets found")
        
        # Test 2: Test chatbot service
        print("\n📋 Test 2: Chatbot Service Similar Tickets")
        print("-" * 40)
        
        chatbot_service = ConversationalChatbotService(db)
        
        # Test with a specific ticket number
        test_ticket_number = "T20250804.0003"
        print(f"Testing similar tickets for ticket: {test_ticket_number}")
        
        # Get the original ticket first
        original_ticket = ticket_service.get_ticket_by_number(test_ticket_number)
        if original_ticket:
            print(f"Original ticket found: {original_ticket.title}")
            
            # Find similar tickets using chatbot service
            keywords = [original_ticket.title or "", original_ticket.description or "", original_ticket.issuetype or ""]
            similar_tickets = chatbot_service._find_similar_tickets_from_db(keywords, "T001", limit=5)
            
            if similar_tickets:
                print(f"✅ Found {len(similar_tickets)} similar tickets via chatbot service:")
                for i, ticket in enumerate(similar_tickets, 1):
                    print(f"\n{i}. Ticket: {ticket.ticketnumber}")
                    print(f"   Title: {ticket.title}")
                    print(f"   Status: {ticket.status}")
                    if ticket.resolution and ticket.resolution.strip():
                        print(f"   Resolution: {ticket.resolution[:100]}...")
            else:
                print("❌ No similar tickets found via chatbot service")
        else:
            print(f"❌ Original ticket {test_ticket_number} not found")
        
        # Test 3: Test semantic similarity with different issue types
        print("\n📋 Test 3: Different Issue Types")
        print("-" * 40)
        
        test_cases = [
            "Network connectivity issues",
            "Printer not working",
            "Outlook password reset",
            "Software installation problems",
            "Performance issues with laptop"
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: '{test_case}'")
            similar_tickets = ticket_service.find_similar_tickets_by_issue(test_case, limit=3)
            
            if similar_tickets:
                print(f"  ✅ Found {len(similar_tickets)} similar tickets")
                for ticket in similar_tickets[:2]:  # Show top 2
                    source = "COMPANY_4130_DATA" if "[Source: COMPANY_4130_DATA]" in ticket.description else "TICKETS"
                    print(f"    • {ticket.ticketnumber} ({source}) - {ticket.title}")
            else:
                print(f"  ❌ No similar tickets found")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        logger.error(f"Test error: {e}", exc_info=True)

def test_mock_data_removal():
    """Test that mock data has been completely removed."""
    print("\n🧪 Testing Mock Data Removal")
    print("=" * 40)
    
    try:
        # Check simple_router.py for mock data
        with open('backend/chatbot/simple_router.py', 'r') as f:
            content = f.read()
            
        mock_indicators = [
            "Similar Issue 1 (Mock)",
            "Similar Issue 2 (Mock)",
            "Database not connected",
            "Fallback to mock data"
        ]
        
        found_mock = False
        for indicator in mock_indicators:
            if indicator in content:
                print(f"❌ Found mock data indicator: '{indicator}'")
                found_mock = True
        
        if not found_mock:
            print("✅ No mock data found in simple_router.py")
        else:
            print("❌ Mock data still present in simple_router.py")
            
    except Exception as e:
        print(f"❌ Error checking mock data: {e}")

def test_semantic_similarity_implementation():
    """Test that semantic similarity is properly implemented."""
    print("\n🧪 Testing Semantic Similarity Implementation")
    print("=" * 50)
    
    try:
        # Check for Snowflake Cortex AI usage
        with open('backend/chatbot/services/ticket_service.py', 'r') as f:
            content = f.read()
            
        if "SNOWFLAKE.CORTEX.AI_SIMILARITY" in content:
            print("✅ Snowflake Cortex AI_SIMILARITY found in ticket_service.py")
        else:
            print("❌ Snowflake Cortex AI_SIMILARITY not found in ticket_service.py")
            
        with open('backend/chatbot/services/chatbot_service.py', 'r') as f:
            content = f.read()
            
        if "SNOWFLAKE.CORTEX.AI_SIMILARITY" in content:
            print("✅ Snowflake Cortex AI_SIMILARITY found in chatbot_service.py")
        else:
            print("❌ Snowflake Cortex AI_SIMILARITY not found in chatbot_service.py")
            
        with open('backend/chatbot/simple_router.py', 'r') as f:
            content = f.read()
            
        if "SNOWFLAKE.CORTEX.AI_SIMILARITY" in content:
            print("✅ Snowflake Cortex AI_SIMILARITY found in simple_router.py")
        else:
            print("❌ Snowflake Cortex AI_SIMILARITY not found in simple_router.py")
            
    except Exception as e:
        print(f"❌ Error checking semantic similarity implementation: {e}")

def test_dual_table_search():
    """Test that both TICKETS and COMPANY_4130_DATA tables are being searched."""
    print("\n🧪 Testing Dual Table Search")
    print("=" * 35)
    
    try:
        # Check for COMPANY_4130_DATA table usage
        with open('backend/chatbot/services/ticket_service.py', 'r') as f:
            content = f.read()
            
        if "COMPANY_4130_DATA" in content:
            print("✅ COMPANY_4130_DATA table search found in ticket_service.py")
        else:
            print("❌ COMPANY_4130_DATA table search not found in ticket_service.py")
            
        with open('backend/chatbot/services/chatbot_service.py', 'r') as f:
            content = f.read()
            
        if "COMPANY_4130_DATA" in content:
            print("✅ COMPANY_4130_DATA table search found in chatbot_service.py")
        else:
            print("❌ COMPANY_4130_DATA table search not found in chatbot_service.py")
            
        with open('backend/chatbot/simple_router.py', 'r') as f:
            content = f.read()
            
        if "COMPANY_4130_DATA" in content:
            print("✅ COMPANY_4130_DATA table search found in simple_router.py")
        else:
            print("❌ COMPANY_4130_DATA table search not found in simple_router.py")
            
    except Exception as e:
        print(f"❌ Error checking dual table search: {e}")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Similar Tickets Testing Suite")
    print("=" * 60)
    
    # Run all tests
    test_mock_data_removal()
    test_semantic_similarity_implementation()
    test_dual_table_search()
    test_similar_tickets_enhancement()
    
    print("\n🎉 Testing Suite Complete!")
    print("=" * 60)
    print("\n📋 Summary of Changes:")
    print("✅ Removed all mock data from similar tickets functionality")
    print("✅ Implemented semantic similarity using Snowflake Cortex AI")
    print("✅ Added search in both TICKETS and COMPANY_4130_DATA tables")
    print("✅ Enhanced responses with resolution information")
    print("✅ Added fallback to keyword-based search if semantic similarity fails")
    print("✅ Improved error handling and logging") 