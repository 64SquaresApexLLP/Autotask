#!/usr/bin/env python3
"""
Debug script to test intent detection in the chatbot service.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.chatbot.services.chatbot_service import ConversationalChatbotService
from backend.chatbot.database import SessionLocal
from backend.chatbot.services.llm_service import LLMService

def test_intent_detection():
    """Test the intent detection logic."""
    print("🔍 Testing Intent Detection...")
    
    # Create a mock database session and LLM service
    db = SessionLocal()
    llm_service = LLMService()
    
    # Create chatbot service
    chatbot_service = ConversationalChatbotService(db, llm_service)
    
    # Test messages
    test_messages = [
        "AI resolution: My computer is running slow",
        "AI help: I can't connect to the printer",
        "Find similar tickets to T20250804.0001",
        "Show me tickets like network problems",
        "Hello, how are you?",
        "Show my tickets"
    ]
    
    for message in test_messages:
        print(f"\n📝 Testing: '{message}'")
        try:
            intent, entities = chatbot_service._analyze_message(message)
            print(f"   Intent: {intent}")
            print(f"   Entities: {entities}")
        except Exception as e:
            print(f"   Error: {e}")
    
    db.close()

if __name__ == "__main__":
    test_intent_detection() 