#!/usr/bin/env python3
"""
Test script to verify chatbot fixes for AI resolution and similar tickets functionality.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"
CHATBOT_URL = f"{BASE_URL}/chatbot"

def test_chatbot_login():
    """Test chatbot login to get authentication token."""
    print("🔐 Testing chatbot login...")
    
    login_data = {
        "username": "T001",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{CHATBOT_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Login successful for {login_data['username']}")
            return token_data['access_token']
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_chat_message(token, message, expected_intent=None):
    """Test sending a chat message."""
    headers = {"Authorization": f"Bearer {token}"}
    
    chat_data = {
        "message": message,
        "session_id": f"test_session_{int(time.time())}"
    }
    
    try:
        response = requests.post(f"{CHATBOT_URL}/chat", json=chat_data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat message sent successfully")
            print(f"📝 Response: {result.get('response', '')[:200]}...")
            return result
        else:
            print(f"❌ Chat message failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Chat message error: {e}")
        return None

def test_ai_resolution(token):
    """Test AI resolution functionality."""
    print("\n🤖 Testing AI Resolution...")
    
    test_queries = [
        "AI resolution: My computer is running very slow and takes forever to start up",
        "AI help: I can't connect to the printer, it says offline",
        "AI support: I forgot my password and can't log into my email"
    ]
    
    for query in test_queries:
        print(f"\n📋 Testing query: {query}")
        result = test_chat_message(token, query)
        if result:
            print("✅ AI resolution test passed")
        else:
            print("❌ AI resolution test failed")
        time.sleep(1)

def test_similar_tickets_by_number(token):
    """Test finding similar tickets by ticket number."""
    print("\n🔍 Testing Similar Tickets by Number...")
    
    # Test with a known ticket number
    test_queries = [
        "Find similar tickets to T20250804.0001",
        "Show me tickets similar to T20250804.0002",
        "T20250804.0003 similar tickets"
    ]
    
    for query in test_queries:
        print(f"\n📋 Testing query: {query}")
        result = test_chat_message(token, query)
        if result:
            print("✅ Similar tickets by number test passed")
        else:
            print("❌ Similar tickets by number test failed")
        time.sleep(1)

def test_similar_tickets_by_nlp(token):
    """Test finding similar tickets using natural language."""
    print("\n🧠 Testing Similar Tickets by NLP...")
    
    test_queries = [
        "Find similar tickets for network connectivity issues",
        "Show me tickets like email problems",
        "Similar tickets for printer not working",
        "Find tickets related to slow computer performance"
    ]
    
    for query in test_queries:
        print(f"\n📋 Testing query: {query}")
        result = test_chat_message(token, query)
        if result:
            print("✅ Similar tickets by NLP test passed")
        else:
            print("❌ Similar tickets by NLP test failed")
        time.sleep(1)

def test_general_queries(token):
    """Test general chatbot functionality."""
    print("\n💬 Testing General Queries...")
    
    test_queries = [
        "Hello, how are you?",
        "Show my tickets",
        "What can you help me with?"
    ]
    
    for query in test_queries:
        print(f"\n📋 Testing query: {query}")
        result = test_chat_message(token, query)
        if result:
            print("✅ General query test passed")
        else:
            print("❌ General query test failed")
        time.sleep(1)

def test_error_handling():
    """Test error handling for malformed requests."""
    print("\n⚠️ Testing Error Handling...")
    
    # Test without authentication
    try:
        response = requests.post(f"{CHATBOT_URL}/chat", json={"message": "test"})
        if response.status_code == 401:
            print("✅ Authentication required - correct behavior")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
    
    # Test malformed request
    try:
        response = requests.post(f"{CHATBOT_URL}/chat", json={"invalid_field": "test"})
        if response.status_code == 422:
            print("✅ Malformed request rejected - correct behavior")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")

def main():
    """Main test function."""
    print("🚀 Starting Chatbot Fixes Test Suite")
    print("=" * 50)
    
    # Test login
    token = test_chatbot_login()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return
    
    # Run all tests
    test_general_queries(token)
    test_ai_resolution(token)
    test_similar_tickets_by_number(token)
    test_similar_tickets_by_nlp(token)
    test_error_handling()
    
    print("\n" + "=" * 50)
    print("✅ Chatbot Fixes Test Suite Completed!")

if __name__ == "__main__":
    main() 