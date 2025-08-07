#!/usr/bin/env python3
"""
Direct Gmail Integration using IMAP
Skips OAuth and uses direct IMAP connection with App Password
"""

import imaplib
import email
import time
import threading
import requests
import json
import os
from datetime import datetime
from email.header import decode_header
from email.utils import parseaddr


class DirectGmailIntegration:
    """
    Direct Gmail integration using IMAP - no OAuth required
    Uses rohankool2021@gmail.com with App Password
    """
    
    def __init__(self, webhook_url="http://localhost:8001/webhooks/gmail/simple"):
        self.webhook_url = webhook_url
        self.email_address = "rohankool2021@gmail.com"
        self.app_password = None
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        
        self.mail = None
        self.is_monitoring = False
        self.monitor_thread = None
        self.processed_uids = set()
        
        print("📧 DIRECT GMAIL INTEGRATION")
        print("=" * 50)
        print("🎯 Target: rohankool2021@gmail.com")
        print("🔧 Method: IMAP + App Password (No OAuth)")
        print("📡 Webhook: " + self.webhook_url)
        print("=" * 50)
    
    def setup_app_password(self):
        """Guide user to set up Gmail App Password"""
        print("\n🔐 GMAIL APP PASSWORD SETUP")
        print("This method uses Gmail App Passwords - much simpler than OAuth!")
        print("")
        print("📋 QUICK SETUP STEPS:")
        print("")
        print("1️⃣  Enable 2-Factor Authentication (if not already):")
        print("   • Go to: https://myaccount.google.com/security")
        print("   • Login with: rohankool2021@gmail.com")
        print("   • Enable 2-Step Verification")
        print("")
        print("2️⃣  Generate App Password:")
        print("   • Go to: https://myaccount.google.com/apppasswords")
        print("   • Select app: 'Mail'")
        print("   • Select device: 'Other (custom name)'")
        print("   • Enter name: 'TeamLogic AutoTask'")
        print("   • Click 'Generate'")
        print("")
        print("3️⃣  Copy the 16-character password:")
        print("   • Google will show: xxxx xxxx xxxx xxxx")
        print("   • Copy it (remove spaces)")
        print("   • Paste below")
        print("")
        
        # Option to open the URLs
        choice = input("Open App Password setup page? (y/n): ").lower().strip()
        if choice == 'y':
            import webbrowser
            print("🌐 Opening App Password setup...")
            webbrowser.open("https://myaccount.google.com/apppasswords")
            print("💡 Complete the setup and come back here")
        
        print("\n📝 Enter App Password:")
        app_password = input("16-character app password (no spaces): ").strip().replace(" ", "")
        
        if len(app_password) != 16:
            print("❌ App password should be exactly 16 characters")
            print("💡 It looks like: abcdabcdabcdabcd")
            return False
        
        self.app_password = app_password
        
        # Save for future use
        try:
            with open('.gmail_app_password', 'w') as f:
                f.write(app_password)
            print("✅ App password saved to .gmail_app_password")
        except Exception as e:
            print(f"⚠️ Could not save password: {e}")
        
        return True
    
    def load_app_password(self):
        """Load saved app password"""
        # Try multiple possible locations for the password file
        password_files = [
            '.gmail_app_password',  # Current directory
            '../.gmail_app_password',  # Parent directory (when running from backend/)
            os.path.join(os.path.dirname(__file__), '.gmail_app_password')  # Same directory as this script
        ]
        
        for password_file in password_files:
            try:
                if os.path.exists(password_file):
                    with open(password_file, 'r') as f:
                        self.app_password = f.read().strip()
                    print(f"✅ App password loaded from {password_file}")
                    return True
            except Exception as e:
                print(f"⚠️ Error loading app password from {password_file}: {e}")
                continue
        
        print("ℹ️ No saved app password found in any location")
        return False
    
    def test_connection(self, interactive=True):
        """Test Gmail IMAP connection"""
        try:
            if not self.app_password:
                if not self.load_app_password():
                    if interactive and self.setup_app_password():
                        pass  # Password was set up interactively
                    else:
                        print("❌ No Gmail app password available and running in non-interactive mode")
                        print("💡 Please set up the Gmail app password first by running the script manually")
                        return False
            
            print("🔌 Testing Gmail IMAP connection...")
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            mail.select('inbox')
            
            # Get inbox info
            status, messages = mail.search(None, 'ALL')
            if status == 'OK':
                email_count = len(messages[0].split()) if messages[0] else 0
                print(f"✅ Connection successful!")
                print(f"📧 Connected to: {self.email_address}")
                print(f"📊 Total emails in inbox: {email_count}")
            
            mail.logout()
            return True
            
        except imaplib.IMAP4.error as e:
            print(f"❌ IMAP authentication failed: {e}")
            if "authentication failed" in str(e).lower():
                print("💡 Check your app password or create a new one")
                print("💡 Make sure 2-Factor Authentication is enabled")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def connect_to_gmail(self):
        """Connect to Gmail IMAP"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(self.email_address, self.app_password)
            self.mail.select('inbox')
            return True
        except Exception as e:
            print(f"❌ Gmail connection failed: {e}")
            return False
    
    def extract_email_data(self, msg):
        """Extract email data from message"""
        try:
            # Get headers
            subject = ""
            if msg.get("Subject"):
                subject_parts = decode_header(msg.get("Subject"))
                subject = ""
                for part, encoding in subject_parts:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or "utf-8", errors='ignore')
                    else:
                        subject += part
            
            from_header = msg.get("From", "")
            to_header = msg.get("To", "")
            
            # Parse sender
            from_name, from_email = parseaddr(from_header)
            if not from_name:
                from_name = from_email.split('@')[0] if '@' in from_email else from_email
            
            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                        except:
                            continue
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = str(msg.get_payload())
            
            return {
                'subject': subject,
                'from_email': from_email,
                'from_name': from_name,
                'to_email': to_header,
                'body': body.strip(),
                'received_at': datetime.now().isoformat(),
                'source': 'gmail_imap_direct'
            }
            
        except Exception as e:
            print(f"⚠️ Error extracting email data: {e}")
            return None
    
    def send_to_webhook(self, email_data):
        """Send email to webhook for processing"""
        try:
            print(f"📧 Processing: {email_data['subject']}")
            print(f"   From: {email_data['from_name']} <{email_data['from_email']}>")
            
            response = requests.post(
                self.webhook_url,
                json=email_data,
                headers={'Content-Type': 'application/json'},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Email processed successfully!")
                
                if result.get('ticket_number'):
                    print(f"🎫 Ticket created: {result['ticket_number']}")
                
                return True
            else:
                print(f"❌ Webhook error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending to webhook: {e}")
            return False
    
    def check_new_emails(self):
        """Check for new emails"""
        try:
            if not self.mail:
                return []
            
            # Search for all emails
            status, messages = self.mail.search(None, 'ALL')
            if status != 'OK' or not messages[0]:
                return []
            
            email_ids = messages[0].split()
            new_emails = []
            
            # Process only new emails
            for email_id in email_ids:
                if email_id in self.processed_uids:
                    continue
                
                try:
                    # Fetch email
                    status, msg_data = self.mail.fetch(email_id, '(RFC822)')
                    
                    if status == 'OK' and msg_data:
                        email_body = msg_data[0][1]
                        if isinstance(email_body, bytes):
                            email_message = email.message_from_bytes(email_body)
                            
                            email_data = self.extract_email_data(email_message)
                            if email_data:
                                email_data['message_id'] = email_id.decode()
                                new_emails.append(email_data)
                            
                            self.processed_uids.add(email_id)
                
                except Exception as e:
                    print(f"⚠️ Error processing email {email_id}: {e}")
                    continue
            
            return new_emails
            
        except Exception as e:
            print(f"❌ Error checking emails: {e}")
            return []
    
    def start_monitoring(self, check_interval=5):
        """Start email monitoring"""
        if self.is_monitoring:
            print("📧 Already monitoring")
            return
        
        if not self.connect_to_gmail():
            print("❌ Cannot start - connection failed")
            return
        
        # Get baseline emails
        try:
            status, messages = self.mail.search(None, 'ALL')
            if status == 'OK' and messages[0]:
                initial_emails = messages[0].split()
                self.processed_uids.update(initial_emails)
                print(f"📊 Baseline: {len(initial_emails)} existing emails (will skip)")
        except:
            pass
        
        self.is_monitoring = True
        
        def monitor_loop():
            print(f"🔍 Monitoring started (checking every {check_interval} seconds)")
            print("📧 Send email to rohankool2021@gmail.com to test!")
            print("=" * 60)
            
            while self.is_monitoring:
                try:
                    new_emails = self.check_new_emails()
                    
                    for email_data in new_emails:
                        print(f"\n🚨 NEW EMAIL!")
                        success = self.send_to_webhook(email_data)
                        print("=" * 60)
                    
                    if self.mail:
                        self.mail.noop()  # Keep alive
                    
                    time.sleep(check_interval)
                    
                except Exception as e:
                    print(f"❌ Monitor error: {e}")
                    if self.connect_to_gmail():
                        print("✅ Reconnected")
                    else:
                        time.sleep(30)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass
        print("🛑 Monitoring stopped")


def main():
    """Main function"""
    integration = DirectGmailIntegration()
    
    # Test connection first
    if not integration.test_connection():
        print("\n❌ Connection test failed!")
        print("💡 Set up App Password and try again")
        return
    
    print("\n🎉 Connection test successful!")
    
    # Start monitoring
    try:
        if integration.start_monitoring():
            print("\n🔄 Email monitoring ACTIVE!")
            print("⚠️ Press Ctrl+C to stop")
            
            while True:
                time.sleep(1)
        else:
            print("❌ Failed to start monitoring")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        integration.stop_monitoring()
        print("✅ Stopped successfully")


if __name__ == "__main__":
    main()
