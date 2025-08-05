#!/usr/bin/env python3
"""
Test Escalation Functionality
Test the new escalation endpoint and email notification
"""

import sys
import os
import requests
import json

# Add the src directory to the path
sys.path.append('src')

def test_escalation_endpoint():
    """Test the escalation endpoint"""
    print("🧪 TESTING ESCALATION FUNCTIONALITY")
    print("=" * 50)
    
    # Test data
    test_ticket_number = "T20250804.0001"  # Use a test ticket number
    escalation_data = {
        "escalation_reason": "Due date exceeded - urgent ticket requires management attention",
        "technician_id": "T001"
    }
    
    try:
        # Test the escalation endpoint
        print(f"📡 Testing escalation endpoint for ticket: {test_ticket_number}")
        
        response = requests.post(
            "http://localhost:8001/tickets/{}/escalate".format(test_ticket_number),
            json=escalation_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Escalation endpoint test PASSED")
            print(f"📧 Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Escalation endpoint test FAILED")
            print(f"📧 Status Code: {response.status_code}")
            print(f"📧 Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend server")
        print("💡 Make sure the backend is running on http://localhost:8001")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_notification_agent():
    """Test the notification agent directly"""
    print("\n📧 TESTING NOTIFICATION AGENT")
    print("=" * 50)
    
    try:
        from src.agents.notification_agent import NotificationAgent
        from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE
        
        # Initialize notification agent
        print("🔧 Initializing notification agent...")
        notification_agent = NotificationAgent(db_connection=None)  # Test without DB connection first
        
        if not notification_agent.enabled:
            print("❌ Notification agent is disabled")
            return False
        
        print("✅ Notification agent initialized and enabled")
        
        # Test escalation notification
        test_ticket_data = {
            'ticket_number': 'T20250804.0001',
            'title': 'Test Escalation Ticket',
            'description': 'This is a test ticket to verify escalation notifications.',
            'priority': 'High',
            'due_date': '2025-01-01',
            'status': 'Escalated',
            'escalation_reason': 'Due date exceeded - requires management attention',
            'technician_id': 'T001',
            'user_email': 'test@example.com',
            'user_id': 'Test User',
            'phone_number': '123-456-7890',
            'technician_email': 'technician@example.com',
            'created_at': '2025-01-01T10:00:00'
        }
        
        print(f"🧪 Testing escalation notification...")
        
        # Test sending escalation notification
        success = notification_agent.send_escalation_notification(
            recipient_email='anantlad66@gmail.com',
            ticket_data=test_ticket_data,
            ticket_number='T20250804.0001',
            escalation_reason='Due date exceeded for urgent ticket T20250804.0001',
            recipient_type='manager'
        )
        
        if success:
            print("✅ Escalation notification test PASSED")
            print("📧 Email sent successfully to anantlad66@gmail.com")
            return True
        else:
            print("❌ Escalation notification test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Notification agent test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting escalation functionality tests...")
    
    # Test notification agent first
    notification_test = test_notification_agent()
    
    # Test escalation endpoint
    endpoint_test = test_escalation_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    print(f"📧 Notification Agent: {'✅ PASSED' if notification_test else '❌ FAILED'}")
    print(f"🔗 Escalation Endpoint: {'✅ PASSED' if endpoint_test else '❌ FAILED'}")
    
    if notification_test and endpoint_test:
        print("\n🎉 All tests PASSED! Escalation functionality is working correctly.")
    else:
        print("\n⚠️  Some tests FAILED. Please check the implementation.") 