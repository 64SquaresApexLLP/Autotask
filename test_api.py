#!/usr/bin/env python3
"""
Test script to verify the FastAPI backend endpoints are working correctly.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8001"

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_detailed_health_check():
    """Test the detailed health check endpoint"""
    print("\n🔍 Testing detailed health check...")
    try:
        response = requests.get(f"{BASE_URL}/health/detailed")
        if response.status_code == 200:
            data = response.json()
            print("✅ Detailed health check passed")
            print(f"   Database: {data.get('database', 'unknown')}")
            print(f"   Agents: {data.get('agents', {})}")
            return True
        else:
            print(f"❌ Detailed health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Detailed health check error: {e}")
        return False

def test_create_ticket():
    """Test ticket creation with agentic workflow"""
    print("\n🎫 Testing ticket creation...")
    
    ticket_data = {
        "title": "Laptop screen flickering",
        "description": "My laptop screen keeps flickering and sometimes goes black. It happens more frequently when I'm using multiple applications.",
        "due_date": "2024-12-31",
        "user_email": "john.doe@company.com",
        "priority": "High",
        "requester_name": "John Doe"
    }
    
    try:
        print(f"   Creating ticket: {ticket_data['title']}")
        response = requests.post(f"{BASE_URL}/tickets", json=ticket_data)
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Ticket creation successful")
            print(f"   Ticket Number: {data.get('ticket_number')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Priority: {data.get('priority')}")
            print(f"   Assigned Technician: {data.get('assigned_technician')}")
            print(f"   Technician Email: {data.get('technician_email')}")
            return data.get('ticket_number')
        else:
            print(f"❌ Ticket creation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ticket creation error: {e}")
        return None

def test_get_ticket(ticket_number):
    """Test getting a ticket by number"""
    if not ticket_number:
        print("\n⏭️  Skipping get ticket test - no ticket number")
        return False
        
    print(f"\n📋 Testing get ticket by number: {ticket_number}")
    try:
        response = requests.get(f"{BASE_URL}/tickets/{ticket_number}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Get ticket successful")
            print(f"   Title: {data.get('TITLE')}")
            print(f"   Description: {data.get('DESCRIPTION')[:50]}...")
            print(f"   Priority: {data.get('PRIORITY')}")
            print(f"   Status: {data.get('STATUS')}")
            return True
        elif response.status_code == 404:
            print("❌ Ticket not found")
            return False
        else:
            print(f"❌ Get ticket failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get ticket error: {e}")
        return False

def test_get_technician(ticket_number):
    """Test getting assigned technician by ticket number"""
    if not ticket_number:
        print("\n⏭️  Skipping get technician test - no ticket number")
        return False
        
    print(f"\n👨‍💻 Testing get technician for ticket: {ticket_number}")
    try:
        response = requests.get(f"{BASE_URL}/tickets/{ticket_number}/technician")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Get technician successful")
            print(f"   Technician Email: {data.get('technician_email')}")
            print(f"   Assigned Technician: {data.get('assigned_technician')}")
            print(f"   Ticket Number: {data.get('ticket_number')}")
            return True
        elif response.status_code == 404:
            print("❌ Technician not found or not assigned")
            return False
        else:
            print(f"❌ Get technician failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get technician error: {e}")
        return False

def test_get_all_tickets():
    """Test getting all tickets"""
    print("\n📊 Testing get all tickets...")
    try:
        response = requests.get(f"{BASE_URL}/tickets?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Get all tickets successful - found {len(data)} tickets")
            if data:
                print("   Recent tickets:")
                for i, ticket in enumerate(data[:3]):
                    print(f"     {i+1}. {ticket.get('TICKETNUMBER')} - {ticket.get('TITLE')}")
            return True
        else:
            print(f"❌ Get all tickets failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get all tickets error: {e}")
        return False

def test_tickets_stats():
    """Test getting ticket statistics"""
    print("\n📈 Testing ticket statistics...")
    try:
        response = requests.get(f"{BASE_URL}/tickets/stats")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Ticket statistics successful")
            print(f"   By Status: {data.get('by_status', {})}")
            print(f"   By Priority: {data.get('by_priority', {})}")
            return True
        else:
            print(f"❌ Ticket statistics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ticket statistics error: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Starting FastAPI Backend Tests")
    print("=" * 50)
    
    # Test basic health
    health_ok = test_health_check()
    detailed_health_ok = test_detailed_health_check()
    
    # Test ticket operations
    ticket_number = test_create_ticket()
    
    # Wait a moment for the ticket to be processed
    if ticket_number:
        print("\n⏳ Waiting for ticket to be processed...")
        time.sleep(2)
    
    get_ticket_ok = test_get_ticket(ticket_number)
    get_technician_ok = test_get_technician(ticket_number)
    get_all_tickets_ok = test_get_all_tickets()
    stats_ok = test_tickets_stats()
    
    print("\n" + "=" * 50)
    print("🏁 Test Summary:")
    print(f"   Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"   Detailed Health: {'✅ PASS' if detailed_health_ok else '❌ FAIL'}")
    print(f"   Create Ticket: {'✅ PASS' if ticket_number else '❌ FAIL'}")
    print(f"   Get Ticket: {'✅ PASS' if get_ticket_ok else '❌ FAIL'}")
    print(f"   Get Technician: {'✅ PASS' if get_technician_ok else '❌ FAIL'}")
    print(f"   Get All Tickets: {'✅ PASS' if get_all_tickets_ok else '❌ FAIL'}")
    print(f"   Ticket Statistics: {'✅ PASS' if stats_ok else '❌ FAIL'}")
    
    all_passed = all([health_ok, detailed_health_ok, ticket_number, get_ticket_ok, 
                     get_technician_ok, get_all_tickets_ok, stats_ok])
    
    if all_passed:
        print("\n🎉 All API tests passed! Backend is working correctly.")
        return True
    else:
        print("\n⚠️  Some API tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
