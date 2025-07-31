#!/usr/bin/env python3
"""
Test script to send a support ticket email and verify it gets processed.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_test_support_email():
    """Send a test support ticket email"""
    
    # Email configuration
    sender_email = "your_test_email@gmail.com"  # Replace with your test email
    sender_password = os.getenv('TEST_EMAIL_PASSWORD')  # Set this environment variable
    receiver_email = "rohankul2017@gmail.com"  # The support email address
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "URGENT: Printer not working - need immediate help"
    
    # Email body
    body = """
    Hi Support Team,
    
    I'm having a critical issue with my office printer. It's completely stopped working and I have important documents to print for a meeting in 2 hours.
    
    Details:
    - Printer model: HP LaserJet Pro M404n
    - Error message: "Paper jam" but there's no paper stuck
    - I've tried restarting the printer and computer
    - The printer shows offline status
    
    This is urgent as I need to print documents for an important client meeting.
    
    Please help ASAP!
    
    Thanks,
    Test User
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Create SMTP session
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        
        print("✅ Test support email sent successfully!")
        print(f"📧 Sent to: {receiver_email}")
        print("📝 Subject: URGENT: Printer not working - need immediate help")
        print("\n🔄 The email processing system should pick this up within 5 minutes...")
        
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")
        print("\n💡 To test manually:")
        print("1. Send an email to rohankul2017@gmail.com")
        print("2. Use subject line with support keywords like: 'printer', 'error', 'not working', 'urgent'")
        print("3. Include technical details in the body")
        print("4. Wait 5 minutes for automatic processing")

if __name__ == "__main__":
    send_test_support_email() 