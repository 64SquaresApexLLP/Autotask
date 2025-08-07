#!/usr/bin/env python3
"""
Test script to verify the Gmail webhook endpoint is working correctly
"""

import requests
import json
import time
from datetime import datetime

def test_webhook_accessibility():
    """Test if the webhook endpoint is accessible"""
    print("🔍 Testing webhook accessibility...")
    
    try:
        # Test GET request (should return info)
        response = requests.get("http://localhost:8001/webhooks/gmail/simple", timeout=10)
        if response.status_code == 200:
            print("✅ GET request successful - webhook is accessible")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ GET request failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_webhook_with_valid_data():
    """Test webhook with valid email data"""
    print("\n📧 Testing webhook with valid email data...")
    
    # Sample email data
    email_data = {
        "subject": "Test Email - Webhook Integration",
        "from_email": "test@example.com",
        "from_name": "Test User",
        "to_email": "rohankool2021@gmail.com",
        "body": "This is a test email to verify the webhook integration is working properly.",
        "received_at": datetime.now().isoformat(),
        "source": "gmail_imap_test",
        "message_id": "test-message-123",
        "thread_id": "test-thread-456",
        "imap_uid": "12345"
    }
    
    try:
        response = requests.post(
            "http://localhost:8001/webhooks/gmail/simple",
            json=email_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ POST request successful")
            print(f"   Response: {result}")
            
            if result.get('status') == 'success':
                print(f"🎫 Ticket created: {result.get('ticket_number', 'Unknown')}")
                return True
            else:
                print(f"⚠️ Processing failed: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ POST request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_webhook_with_empty_data():
    """Test webhook with empty data (should handle gracefully)"""
    print("\n🔍 Testing webhook with empty data...")
    
    try:
        response = requests.post(
            "http://localhost:8001/webhooks/gmail/simple",
            data="",
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Empty data handled gracefully")
            print(f"   Response: {result}")
            
            if result.get('status') == 'error' and 'empty' in result.get('message', '').lower():
                print("✅ Proper error handling for empty data")
                return True
            else:
                print("⚠️ Unexpected response for empty data")
                return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_webhook_with_invalid_json():
    """Test webhook with invalid JSON (should handle gracefully)"""
    print("\n🔍 Testing webhook with invalid JSON...")
    
    try:
        response = requests.post(
            "http://localhost:8001/webhooks/gmail/simple",
            data="invalid json data {",
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Invalid JSON handled gracefully")
            print(f"   Response: {result}")
            
            if result.get('status') == 'error' and 'json' in result.get('message', '').lower():
                print("✅ Proper error handling for invalid JSON")
                return True
            else:
                print("⚠️ Unexpected response for invalid JSON")
                return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_backend_status():
    """Test if the backend is running and responsive"""
    print("🔍 Testing backend status...")
    
    endpoints = [
        "/docs",
        "/gmail/status",
        "/webhooks/gmail/test"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8001{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"⚠️ {endpoint} - {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Failed: {e}")

def main():
    """Run all webhook tests"""
    print("🧪 Gmail Webhook Integration Tests")
    print("=" * 50)
    
    # Check if backend is running
    test_backend_status()
    print()
    
    # Run webhook tests
    tests = [
        ("Webhook Accessibility", test_webhook_accessibility),
        ("Valid Email Data", test_webhook_with_valid_data),
        ("Empty Data Handling", test_webhook_with_empty_data),
        ("Invalid JSON Handling", test_webhook_with_invalid_json)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"💥 {test_name} CRASHED: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All webhook tests passed!")
        print("✅ Gmail webhook integration is working correctly")
    else:
        print(f"⚠️ {failed} tests failed - check the backend logs for details")
    
    print("\n💡 Next steps:")
    print("1. Start email monitoring: python gmail_direct_integration.py")
    print("2. Send test email to rohankool2021@gmail.com")
    print("3. Check backend logs for processing confirmation")

if __name__ == "__main__":
    main()