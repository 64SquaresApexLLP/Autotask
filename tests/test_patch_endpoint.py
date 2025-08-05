#!/usr/bin/env python3
"""
Test script to debug the PATCH endpoint error

This script tests the ticket update functionality to identify
the source of the 500 Internal Server Error.

Author: AutoTask Integration System
Date: 2025-08-03
"""

import requests
import json
from datetime import datetime, timedelta

# Backend URL
BASE_URL = "http://localhost:8001"

def test_patch_endpoint_debug():
    """Test the PATCH endpoint with detailed error handling"""
    print("🔧 Testing PATCH Endpoint - Debug Mode")
    print("=" * 45)
    
    # First, create a test ticket
    test_ticket = {
        "title": "Test ticket for PATCH debugging",
        "description": "This ticket will be used to test the PATCH endpoint",
        "due_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "user_email": "patchtest@company.com",
        "priority": "Medium",
        "requester_name": "Patch Tester",
        "phone_number": "+1-555-PATCH-01"
    }
    
    try:
        # Step 1: Create a ticket
        print("📋 Step 1: Creating test ticket...")
        create_response = requests.post(f"{BASE_URL}/tickets", json=test_ticket)
        
        if create_response.status_code == 201:
            ticket_data = create_response.json()
            ticket_number = ticket_data.get('ticket_number')
            print(f"✅ Created ticket: {ticket_number}")
            print(f"🆔 Technician ID: {ticket_data.get('technician_id')}")
            print(f"📧 Technician Email: {ticket_data.get('technician_email')}")
        else:
            print(f"❌ Failed to create ticket: {create_response.status_code}")
            print(f"Error: {create_response.text}")
            return
        
        # Step 2: Test simple priority update (should work)
        print(f"\n📋 Step 2: Testing priority update...")
        priority_update = {"priority": "High"}
        
        priority_response = requests.patch(f"{BASE_URL}/tickets/{ticket_number}", json=priority_update)
        
        if priority_response.status_code == 200:
            print("✅ Priority update successful")
            priority_result = priority_response.json()
            print(f"Updated fields: {priority_result.get('updated_fields')}")
        else:
            print(f"❌ Priority update failed: {priority_response.status_code}")
            print(f"Error: {priority_response.text}")
        
        # Step 3: Test status update to "In Progress" (should work)
        print(f"\n📋 Step 3: Testing status update to 'In Progress'...")
        status_update = {"status": "In Progress"}
        
        status_response = requests.patch(f"{BASE_URL}/tickets/{ticket_number}", json=status_update)
        
        if status_response.status_code == 200:
            print("✅ Status update to 'In Progress' successful")
            status_result = status_response.json()
            print(f"Updated fields: {status_result.get('updated_fields')}")
            print(f"Moved to closed: {status_result.get('moved_to_closed')}")
        else:
            print(f"❌ Status update failed: {status_response.status_code}")
            print(f"Error: {status_response.text}")
        
        # Step 4: Test status update to "Closed" (this might be causing the error)
        print(f"\n📋 Step 4: Testing status update to 'Closed' (potential error source)...")
        close_update = {"status": "Closed"}
        
        close_response = requests.patch(f"{BASE_URL}/tickets/{ticket_number}", json=close_update)
        
        if close_response.status_code == 200:
            print("✅ Ticket closure successful")
            close_result = close_response.json()
            print(f"Updated fields: {close_result.get('updated_fields')}")
            print(f"Moved to closed: {close_result.get('moved_to_closed')}")
            print(f"Workload updated: {close_result.get('workload_updated')}")
            print(f"Technician email: {close_result.get('technician_email')}")
        else:
            print(f"❌ Ticket closure failed: {close_response.status_code}")
            print(f"Error: {close_response.text}")
            print(f"Response headers: {dict(close_response.headers)}")
            
            # Try to get more details from the error
            try:
                error_detail = close_response.json()
                print(f"Error detail: {error_detail}")
            except:
                print("Could not parse error response as JSON")
        
        # Step 5: Check if ticket was moved to closed tickets
        print(f"\n📋 Step 5: Checking closed tickets...")
        closed_response = requests.get(f"{BASE_URL}/tickets/closed")
        
        if closed_response.status_code == 200:
            closed_tickets = closed_response.json()
            print(f"✅ Retrieved {len(closed_tickets)} closed tickets")
            
            # Look for our ticket
            found_ticket = None
            for closed_ticket in closed_tickets:
                if closed_ticket.get('ticket_number') == ticket_number:
                    found_ticket = closed_ticket
                    break
            
            if found_ticket:
                print(f"✅ Found ticket {ticket_number} in closed tickets")
                print(f"🆔 Closed Technician ID: {found_ticket.get('technician_id')}")
                print(f"📞 Phone Number: {found_ticket.get('phone_number')}")
            else:
                print(f"⚠️ Ticket {ticket_number} not found in closed tickets")
        else:
            print(f"❌ Failed to retrieve closed tickets: {closed_response.status_code}")
            
    except Exception as e:
        print(f"❌ Test error: {e}")

def test_specific_ticket():
    """Test the specific ticket that was causing the error"""
    print("\n🎯 Testing Specific Ticket: T20250803.0005")
    print("=" * 45)
    
    ticket_number = "T20250803.0005"
    
    # Test if ticket exists
    try:
        get_response = requests.get(f"{BASE_URL}/tickets")
        if get_response.status_code == 200:
            tickets = get_response.json()
            
            # Look for the specific ticket
            target_ticket = None
            for ticket in tickets:
                if ticket.get('ticket_number') == ticket_number:
                    target_ticket = ticket
                    break
            
            if target_ticket:
                print(f"✅ Found ticket {ticket_number}")
                print(f"📧 Technician Email: {target_ticket.get('technician_email')}")
                print(f"🆔 Technician ID: {target_ticket.get('technician_id')}")
                print(f"📞 Phone Number: {target_ticket.get('phone_number')}")
                
                # Try to update it
                print(f"\n🔄 Attempting to close ticket {ticket_number}...")
                close_update = {"status": "Closed"}
                
                close_response = requests.patch(f"{BASE_URL}/tickets/{ticket_number}", json=close_update)
                
                if close_response.status_code == 200:
                    print("✅ Successfully closed the problematic ticket")
                    result = close_response.json()
                    print(f"Result: {result}")
                else:
                    print(f"❌ Still failing: {close_response.status_code}")
                    print(f"Error: {close_response.text}")
                    
            else:
                print(f"⚠️ Ticket {ticket_number} not found in active tickets")
                print("It may have already been closed or doesn't exist")
                
        else:
            print(f"❌ Failed to retrieve tickets: {get_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing specific ticket: {e}")

if __name__ == "__main__":
    print("🐛 PATCH Endpoint Debug Test Suite")
    print("=" * 50)
    print("This script will:")
    print("• Create a test ticket")
    print("• Test priority updates")
    print("• Test status updates")
    print("• Test ticket closure")
    print("• Debug any errors")
    print("=" * 50)
    
    # Run debug tests
    test_patch_endpoint_debug()
    test_specific_ticket()
    
    print("\n" + "=" * 50)
    print("🎯 Debug Summary:")
    print("Check the output above for any error details")
    print("Look for specific error messages or stack traces")
    print("=" * 50)
