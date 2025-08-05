#!/usr/bin/env python3
"""
Test Email Notifications
Test the fixed notification agent with Gmail app password
"""

import sys
import os

# Add the src directory to the path
sys.path.append('src')

from agents.notification_agent import NotificationAgent


def test_notification_agent():
    """Test the notification agent with Gmail app password"""
    print("📧 TESTING EMAIL NOTIFICATIONS")
    print("=" * 50)
    
    # Initialize notification agent
    print("🔧 Initializing notification agent...")
    notification_agent = NotificationAgent(db_connection=None)
    
    if not notification_agent.enabled:
        print("❌ Notification agent is disabled")
        print("💡 Make sure .gmail_app_password file exists")
        return False
    
    print("✅ Notification agent initialized and enabled")
    print(f"📧 SMTP Server: {notification_agent.smtp_server}")
    print(f"📧 SMTP Username: {notification_agent.smtp_username}")
    print(f"📧 From Email: {notification_agent.from_email}")
    
    # Test email data
    test_ticket_data = {
        'ticket_number': 'TL-2024-TEST-001',
        'title': 'Test Email Notification',
        'description': 'This is a test ticket to verify email notifications are working.',
        'priority': 'Medium',
        'category': 'General Support',
        'assigned_technician': 'Test Technician',
        'technician_email': 'anantlad66@gmail.com',  # Test email
        'customer_email': 'anantlad66@gmail.com',    # Test email
        'status': 'Open',
        'created_at': '2024-01-01 10:00:00'
    }
    
    print(f"\n🧪 Testing email notification...")
    print(f"📧 Test recipient: {test_ticket_data['customer_email']}")
    
    # Test sending notification
    try:
        success = notification_agent.send_ticket_confirmation(
            user_email=test_ticket_data['customer_email'],
            ticket_data=test_ticket_data,
            ticket_number=test_ticket_data['ticket_number']
        )
        
        if success:
            print("✅ Test email sent successfully!")
            return True
        else:
            print("❌ Test email failed to send")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        return False


def check_gmail_app_password():
    """Check if Gmail app password file exists"""
    print("\n🔍 CHECKING GMAIL APP PASSWORD")
    print("=" * 40)
    
    app_password_file = '.gmail_app_password'
    
    if os.path.exists(app_password_file):
        try:
            with open(app_password_file, 'r') as f:
                password = f.read().strip()
                if len(password) == 16:
                    print("✅ Gmail app password file found and valid")
                    print(f"📁 File: {app_password_file}")
                    print(f"🔑 Password: {password[:4]}************")
                    return True
                else:
                    print("❌ Gmail app password file exists but invalid length")
                    print(f"   Expected: 16 characters, Got: {len(password)}")
                    return False
        except Exception as e:
            print(f"❌ Error reading app password file: {e}")
            return False
    else:
        print("❌ Gmail app password file not found")
        print(f"💡 Expected file: {app_password_file}")
        print("💡 Run the Gmail direct integration to create this file")
        return False


def main():
    """Main function"""
    print("🔧 EMAIL NOTIFICATION TESTING")
    print("=" * 60)
    print("Testing the fixed notification agent with Gmail app password")
    print("=" * 60)
    
    # Check app password first
    if not check_gmail_app_password():
        print("\n❌ Gmail app password not available")
        print("💡 Run: python gmail_direct_integration.py to set up app password")
        return False
    
    # Test notification agent
    if test_notification_agent():
        print("\n🎉 EMAIL NOTIFICATION TEST SUCCESSFUL!")
        print("✅ Notification agent is working correctly")
        print("✅ Gmail app password authentication working")
        print("✅ Ready for production email notifications")
        return True
    else:
        print("\n❌ EMAIL NOTIFICATION TEST FAILED!")
        print("💡 Check the error messages above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
