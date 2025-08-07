"""
Email Listener Service - Background Gmail IMAP monitoring
Integrates DirectGmailIntegration with IntakeAgent pipeline via webhook
"""

import imaplib
import email
import time
import threading
import requests
import json
import asyncio
from datetime import datetime
from email.header import decode_header
from email.utils import parseaddr
from typing import Dict, List, Optional, Callable


class EmailListenerService:
    """
    Background email monitoring service that integrates Gmail IMAP with IntakeAgent pipeline.
    Runs continuously in a separate thread without blocking main application.
    """
    
    def __init__(self, webhook_url: str = "http://localhost:8001/webhooks/gmail/simple",
                 email_address: str = "rohankool2021@gmail.com",
                 check_interval: int = 30):
        """
        Initialize the email listener service.
        
        Args:
            webhook_url: Local webhook endpoint for processing emails
            email_address: Gmail address to monitor
            check_interval: Seconds between email checks (default: 30)
        """
        self.webhook_url = webhook_url
        self.email_address = email_address
        self.check_interval = check_interval
        self.app_password = None
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        
        # Connection and monitoring state
        self.mail = None
        self.is_monitoring = False
        self.monitor_thread = None
        self.processed_uids = set()
        self._stop_event = threading.Event()
        
        # Error handling
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.reconnect_delay = 60  # seconds
        
        print(f"EmailListenerService initialized")
        print(f"Target: {self.email_address}")
        print(f"Webhook: {self.webhook_url}")
        print(f"Check interval: {self.check_interval}s")
    
    def load_app_password(self) -> bool:
        """
        Load Gmail App Password from file.
        
        Returns:
            bool: True if password loaded successfully
        """
        try:
            with open('.gmail_app_password', 'r') as f:
                self.app_password = f.read().strip()
            print("Gmail App password loaded from saved file")
            return True
        except FileNotFoundError:
            print("No saved Gmail App password found - email monitoring disabled")
            print("To enable email monitoring, run: python gmail_direct_integration.py")
            return False
        except Exception as e:
            print(f"Error loading Gmail App password: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test Gmail IMAP connection.
        
        Returns:
            bool: True if connection successful
        """
        try:
            if not self.app_password:
                if not self.load_app_password():
                    return False
            
            logger.debug("Testing Gmail IMAP connection...")
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            mail.select('inbox')
            
            # Get inbox info
            status, messages = mail.search(None, 'ALL')
            if status == 'OK':
                email_count = len(messages[0].split()) if messages[0] else 0
                print(f"Gmail connection successful - {email_count} emails in inbox")
            
            mail.logout()
            return True
            
        except imaplib.IMAP4.error as e:
            print(f"Gmail IMAP authentication failed: {e}")
            if "authentication failed" in str(e).lower():
                print("Check your Gmail App password or create a new one")
                print("Gmail App Password setup: https://myaccount.google.com/apppasswords")
            return False
        except Exception as e:
            print(f"Gmail connection error: {e}")
            return False
    
    def connect_to_gmail(self) -> bool:
        """
        Connect to Gmail IMAP server.
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(self.email_address, self.app_password)
            self.mail.select('inbox')
            logger.debug("Connected to Gmail IMAP")
            return True
        except Exception as e:
            logger.error(f"Gmail connection failed: {e}")
            self.mail = None
            return False
    
    def extract_email_data(self, msg) -> Optional[Dict]:
        """
        Extract structured data from email message.
        
        Args:
            msg: Email message object
            
        Returns:
            Dict: Extracted email data or None if extraction fails
        """
        try:
            # Extract subject
            subject = ""
            if msg.get("Subject"):
                subject_parts = decode_header(msg.get("Subject"))
                subject = ""
                for part, encoding in subject_parts:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or "utf-8", errors='ignore')
                    else:
                        subject += part
            
            # Extract sender information
            from_header = msg.get("From", "")
            to_header = msg.get("To", "")
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
                'source': 'gmail_imap_background',
                'message_id': msg.get("Message-ID", ""),
                'thread_id': msg.get("X-Gmail-ThreadId", "")
            }
            
        except Exception as e:
            logger.error(f"Error extracting email data: {e}")
            return None
    
    def send_to_webhook(self, email_data: Dict) -> bool:
        """
        Send email data to webhook endpoint for processing.
        
        Args:
            email_data: Extracted email data
            
        Returns:
            bool: True if webhook processing successful
        """
        try:
            logger.info(f"Processing email: {email_data['subject']}")
            logger.debug(f"From: {email_data['from_name']} <{email_data['from_email']}>")
            
            response = requests.post(
                self.webhook_url,
                json=email_data,
                headers={'Content-Type': 'application/json'},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Email processed successfully by webhook")
                
                if result.get('ticket_number'):
                    logger.info(f"Ticket created: {result['ticket_number']}")
                
                return True
            else:
                logger.error(f"Webhook error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending to webhook: {e}")
            return False
    
    def check_new_emails(self) -> List[Dict]:
        """
        Check for new emails and return email data.
        
        Returns:
            List[Dict]: List of new email data
        """
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
                                email_data['imap_uid'] = email_id.decode()
                                new_emails.append(email_data)
                            
                            self.processed_uids.add(email_id)
                
                except Exception as e:
                    logger.warning(f"Error processing email {email_id}: {e}")
                    continue
            
            return new_emails
            
        except Exception as e:
            logger.error(f"Error checking emails: {e}")
            return []
    
    def _monitor_loop(self):
        """
        Main monitoring loop - runs in background thread.
        """
        logger.info(f"Email monitoring started (checking every {self.check_interval} seconds)")
        logger.info(f"Monitoring: {self.email_address}")
        
        # Get baseline emails to avoid processing old emails
        try:
            if self.mail:
                status, messages = self.mail.search(None, 'ALL')
                if status == 'OK' and messages[0]:
                    initial_emails = messages[0].split()
                    self.processed_uids.update(initial_emails)
                    logger.info(f"Baseline: {len(initial_emails)} existing emails (will skip)")
        except Exception as e:
            logger.warning(f"Error setting baseline: {e}")
        
        while self.is_monitoring and not self._stop_event.is_set():
            try:
                # Check for new emails
                new_emails = self.check_new_emails()
                
                # Process each new email
                for email_data in new_emails:
                    logger.info("New email detected!")
                    success = self.send_to_webhook(email_data)
                    
                    if success:
                        self.consecutive_failures = 0
                    else:
                        self.consecutive_failures += 1
                        logger.warning(f"Webhook processing failed ({self.consecutive_failures}/{self.max_consecutive_failures})")
                
                # Keep connection alive
                if self.mail:
                    self.mail.noop()
                
                # Reset failure counter on successful check
                if new_emails is not None:  # Empty list is still success
                    self.consecutive_failures = 0
                
                # Wait for next check
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                self.consecutive_failures += 1
                
                # Try to reconnect if too many failures
                if self.consecutive_failures >= self.max_consecutive_failures:
                    logger.warning(f"Too many consecutive failures ({self.consecutive_failures}), attempting reconnect...")
                    
                    if self.connect_to_gmail():
                        logger.info("Reconnected to Gmail successfully")
                        self.consecutive_failures = 0
                    else:
                        logger.error(f"Reconnection failed, waiting {self.reconnect_delay}s...")
                        self._stop_event.wait(self.reconnect_delay)
                else:
                    # Short delay before retry
                    self._stop_event.wait(10)
        
        logger.info("Email monitoring loop ended")
    
    def start_monitoring(self) -> bool:
        """
        Start background email monitoring.
        
        Returns:
            bool: True if monitoring started successfully
        """
        if self.is_monitoring:
            logger.warning("Email monitoring already running")
            return True
        
        # Test connection first
        if not self.test_connection():
            logger.error("Cannot start email monitoring - connection test failed")
            return False
        
        # Connect to Gmail
        if not self.connect_to_gmail():
            logger.error("Cannot start email monitoring - Gmail connection failed")
            return False
        
        # Start monitoring thread
        self.is_monitoring = True
        self._stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Email monitoring started successfully")
        return True
    
    def stop_monitoring(self):
        """
        Stop email monitoring gracefully.
        """
        if not self.is_monitoring:
            return
        
        logger.info("Stopping email monitoring...")
        self.is_monitoring = False
        self._stop_event.set()
        
        # Close Gmail connection
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass
            self.mail = None
        
        # Wait for thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("Email monitoring stopped")
    
    def is_running(self) -> bool:
        """
        Check if email monitoring is currently running.
        
        Returns:
            bool: True if monitoring is active
        """
        return self.is_monitoring and (self.monitor_thread and self.monitor_thread.is_alive())
    
    def get_status(self) -> Dict:
        """
        Get current status of email monitoring service.
        
        Returns:
            Dict: Status information
        """
        return {
            "is_monitoring": self.is_monitoring,
            "is_running": self.is_running(),
            "email_address": self.email_address,
            "webhook_url": self.webhook_url,
            "check_interval": self.check_interval,
            "processed_emails": len(self.processed_uids),
            "consecutive_failures": self.consecutive_failures,
            "has_app_password": bool(self.app_password),
            "connected_to_gmail": bool(self.mail)
        }