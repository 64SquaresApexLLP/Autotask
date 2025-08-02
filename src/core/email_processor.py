"""
Email processing module for TeamLogic-AutoTask.
Handles email connection, processing, and ticket creation from emails.
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr
import pytz
import re
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config import *


class EmailProcessor:
    """Handles email processing and ticket creation from emails."""
    
    def __init__(self, email_account: str, email_password: str, imap_server: str):
        """
        Initialize email processor.
        
        Args:
            email_account: Email account to connect to
            email_password: Email password
            imap_server: IMAP server address
        """
        self.email_account = email_account
        self.email_password = email_password
        self.imap_server = imap_server
        self.ist = pytz.timezone('Asia/Kolkata')
    
    def connect_email(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to email server."""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_account, self.email_password)
            mail.select("inbox")
            return mail
        except Exception as e:
            print(f"❌ Email connection failed: {e}")
            return None
    

    
    def process_email_with_images(self, msg, agent, image_processor) -> Optional[Dict]:
        """Process a single email with image attachment support."""
        try:
            # Extract basic email info
            subject, encoding = decode_header(msg.get("Subject"))[0]
            subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject
            from_ = msg.get("From")
            name, addr = parseaddr(from_)
            email_date = msg.get("Date")
            received_dt = parsedate_to_datetime(email_date).astimezone(self.ist)
            
            # Extract email body
            body = ""
            image_attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            continue
                    elif content_type.startswith('image/') and image_processor:
                        # Handle image attachments
                        filename = part.get_filename()
                        if filename:
                            image_data = part.get_payload(decode=True)
                            image_attachments.append({
                                'filename': filename,
                                'data': image_data,
                                'content_type': content_type
                            })
            else:
                try:
                    body = msg.get_payload(decode=True).decode()
                except:
                    body = str(msg.get_payload())
            
            # Process images if available
            image_context = ""
            if image_attachments and image_processor:
                for img in image_attachments:
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                            tmp_file.write(img['data'])
                            tmp_path = tmp_file.name
                        
                        # Extract text from image
                        extracted_text = image_processor.extract_text_from_image(tmp_path)
                        if extracted_text.strip():
                            image_context += f"\n[Image {img['filename']}]: {extracted_text}"
                        
                        os.unlink(tmp_path)
                    except Exception as e:
                        print(f"⚠️ Error processing image {img['filename']}: {e}")
            
            # Combine body and image context
            full_description = body
            if image_context:
                full_description += f"\n\nImage Content:{image_context}"
            
            # Create ticket data
            ticket_data = {
                'title': subject or "Email Support Request",
                'description': full_description,
                'user_email': addr,
                'user_name': name or addr,
                'source': 'email',
                'received_at': received_dt.isoformat()
            }
            
            # Process with agent
            result = agent.process_new_ticket(ticket_data)
            return result
            
        except Exception as e:
            print(f"❌ Error processing email: {e}")
            return None
    
    def extract_email_body(self, msg) -> str:
        """Extract plain text body from email message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                body = str(msg.get_payload())
        
        return body.strip()
