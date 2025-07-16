"""
Notification Agent for sending email confirmations to users.
Handles SMTP email sending functionality for ticket confirmations.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationAgent:
    """
    Handles email notifications for ticket confirmations.
    """
    
    def __init__(self):
        """
        Initialize the notification agent with SMTP configuration.
        """
        # SMTP Configuration from environment variables
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', os.getenv('EMAIL_ACCOUNT', 'rohankul2017@gmail.com'))
        self.smtp_password = os.getenv('SMTP_PASSWORD', os.getenv('SUPPORT_EMAIL_PASSWORD'))
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'TeamLogic Support')
        
        # Validate configuration
        if not self.smtp_password:
            logger.warning("SMTP password not configured. Email notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Notification agent initialized successfully")
    
    def send_ticket_confirmation(self, user_email: str, ticket_data: Dict, ticket_number: str) -> bool:
        """
        Send a ticket confirmation email to the user.
        
        Args:
            user_email (str): User's email address
            ticket_data (dict): Ticket information
            ticket_number (str): Generated ticket number
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email notifications are disabled due to missing SMTP configuration")
            return False
            
        if not user_email or not user_email.strip():
            logger.warning("No user email provided for notification")
            return False
            
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Ticket Confirmation - #{ticket_number}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = user_email
            
            # Create email content
            html_content = self._create_confirmation_email_html(ticket_data, ticket_number)
            text_content = self._create_confirmation_email_text(ticket_data, ticket_number)
            
            # Attach both text and HTML versions
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            logger.info(f"Confirmation email sent successfully to {user_email} for ticket #{ticket_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send confirmation email to {user_email}: {str(e)}")
            return False

    def send_technician_assignment(self, technician_email: str, ticket_data: Dict, ticket_number: str) -> bool:
        """
        Send a ticket assignment notification to the technician.
        
        Args:
            technician_email (str): Technician's email address
            ticket_data (dict): Ticket information
            ticket_number (str): Generated ticket number
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email notifications are disabled due to missing SMTP configuration")
            return False
            
        if not technician_email or not technician_email.strip():
            logger.warning("No technician email provided for notification")
            return False
            
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"New Ticket Assignment - #{ticket_number}"
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = technician_email
            
            # Create email content
            html_content = self._create_assignment_email_html(ticket_data, ticket_number)
            text_content = self._create_assignment_email_text(ticket_data, ticket_number)
            
            # Attach both text and HTML versions
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
            logger.info(f"Assignment email sent successfully to {technician_email} for ticket #{ticket_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send assignment email to {technician_email}: {str(e)}")
            return False

    def _create_confirmation_email_html(self, ticket_data: Dict, ticket_number: str) -> str:
        """
        Create HTML version of the confirmation email.
        """
        classified_data = ticket_data.get('classified_data', {})
        extracted_metadata = ticket_data.get('extracted_metadata', {})
        resolution_note = ticket_data.get('resolution_note', 'No resolution note available')
        
        # Get classification labels
        issue_type = classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')
        priority = classified_data.get('PRIORITY', {}).get('Label', 'N/A')
        ticket_type = classified_data.get('TICKETTYPE', {}).get('Label', 'N/A')
        
        # Format resolution note for HTML
        resolution_html = resolution_note.replace('\n', '<br>')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .ticket-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .resolution {{ background-color: #e8f5e8; padding: 15px; border-radius: 5px; border-left: 4px solid #28a745; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
                .ticket-number {{ font-size: 24px; font-weight: bold; color: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Ticket Confirmation</h1>
                <div class="ticket-number">#{ticket_number}</div>
            </div>
            
            <div class="content">
                <h2>Thank you for submitting your support ticket!</h2>
                <p>Your ticket has been received and automatically classified by our AI system. Here are the details:</p>
                
                <div class="ticket-info">
                    <h3>Ticket Information</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold;">Ticket Number:</td><td style="padding: 5px;">#{ticket_number}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Title:</td><td style="padding: 5px;">{ticket_data.get('title', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Submitted By:</td><td style="padding: 5px;">{ticket_data.get('name', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Date Created:</td><td style="padding: 5px;">{ticket_data.get('date', 'N/A')} {ticket_data.get('time', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Due Date:</td><td style="padding: 5px;">{ticket_data.get('due_date', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Priority:</td><td style="padding: 5px;">{priority}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Issue Type:</td><td style="padding: 5px;">{issue_type}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Ticket Type:</td><td style="padding: 5px;">{ticket_type}</td></tr>
                    </table>
                </div>
                
                <div class="resolution">
                    <h3>🔧 Recommended Resolution Steps</h3>
                    <p>{resolution_html}</p>
                </div>
                
                <h3>What happens next?</h3>
                <ol>
                    <li>Your ticket has been automatically classified and assigned to the appropriate team</li>
                    <li>A support specialist will review your ticket within 2 business hours</li>
                    <li>Please try the recommended resolution steps above first</li>
                    <li>If the issue persists, our team will contact you directly</li>
                    <li>You can reference this ticket using number <strong>#{ticket_number}</strong></li>
                </ol>
                
                <p><strong>Need immediate assistance?</strong> Contact our support team at {os.getenv('SUPPORT_EMAIL', 'rohankul2017@gmail.com')} or {os.getenv('SUPPORT_PHONE', '9723100860')}</p>
            </div>
            
            <div class="footer">
                <p>This is an automated message from TeamLogic Support System.<br>
                Please do not reply to this email. For assistance, contact our support team.</p>
            </div>
        </body>
        </html>
        """
        return html_content

    def _create_confirmation_email_text(self, ticket_data: Dict, ticket_number: str) -> str:
        """
        Create plain text version of the confirmation email.
        """
        classified_data = ticket_data.get('classified_data', {})
        extracted_metadata = ticket_data.get('extracted_metadata', {})
        resolution_note = ticket_data.get('resolution_note', 'No resolution note available')
        
        # Get classification labels
        issue_type = classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')
        priority = classified_data.get('PRIORITY', {}).get('Label', 'N/A')
        ticket_type = classified_data.get('TICKETTYPE', {}).get('Label', 'N/A')
        
        text_content = f"""
TICKET CONFIRMATION - #{ticket_number}

Thank you for submitting your support ticket!

Your ticket has been received and automatically classified by our AI system.

TICKET INFORMATION:
- Ticket Number: #{ticket_number}
- Title: {ticket_data.get('title', 'N/A')}
- Submitted By: {ticket_data.get('name', 'N/A')}
- Date Created: {ticket_data.get('date', 'N/A')} {ticket_data.get('time', 'N/A')}
- Due Date: {ticket_data.get('due_date', 'N/A')}
- Priority: {priority}
- Issue Type: {issue_type}
- Ticket Type: {ticket_type}

RECOMMENDED RESOLUTION STEPS:
{resolution_note}

WHAT HAPPENS NEXT?
1. Your ticket has been automatically classified and assigned to the appropriate team
2. A support specialist will review your ticket within 2 business hours
3. Please try the recommended resolution steps above first
4. If the issue persists, our team will contact you directly
5. You can reference this ticket using number #{ticket_number}

Need immediate assistance? Contact our support team:
Email: {os.getenv('SUPPORT_EMAIL', 'rohankul2017@gmail.com')}
Phone: {os.getenv('SUPPORT_PHONE', '9723100860')}

---
This is an automated message from TeamLogic Support System.
Please do not reply to this email. For assistance, contact our support team.
        """
        return text_content.strip()

    def _create_assignment_email_html(self, ticket_data: Dict, ticket_number: str) -> str:
        """
        Create HTML version of the technician assignment email.
        """
        classified_data = ticket_data.get('classified_data', {})
        resolution_note = ticket_data.get('resolution_note', 'No resolution note available')
        
        # Get classification labels
        issue_type = classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')
        priority = classified_data.get('PRIORITY', {}).get('Label', 'N/A')
        ticket_type = classified_data.get('TICKETTYPE', {}).get('Label', 'N/A')
        
        # Format resolution note for HTML
        resolution_html = resolution_note.replace('\n', '<br>')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #e74c3c; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .ticket-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .priority-high {{ background-color: #ffebee; border-left: 4px solid #f44336; }}
                .priority-medium {{ background-color: #fff3e0; border-left: 4px solid #ff9800; }}
                .priority-low {{ background-color: #e8f5e8; border-left: 4px solid #4caf50; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
                .ticket-number {{ font-size: 24px; font-weight: bold; color: #fff; }}
                .description {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎫 New Ticket Assignment</h1>
                <div class="ticket-number">#{ticket_number}</div>
            </div>
            
            <div class="content">
                <h2>A new ticket has been assigned to you!</h2>
                
                <div class="ticket-info priority-{priority.lower()}">
                    <h3>Ticket Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold;">Ticket Number:</td><td style="padding: 5px;">#{ticket_number}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Title:</td><td style="padding: 5px;">{ticket_data.get('title', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Customer:</td><td style="padding: 5px;">{ticket_data.get('name', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Customer Email:</td><td style="padding: 5px;">{ticket_data.get('email', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Date Created:</td><td style="padding: 5px;">{ticket_data.get('date', 'N/A')} {ticket_data.get('time', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Due Date:</td><td style="padding: 5px;">{ticket_data.get('due_date', 'N/A')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Priority:</td><td style="padding: 5px; color: #e74c3c; font-weight: bold;">{priority}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Issue Type:</td><td style="padding: 5px;">{issue_type}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Ticket Type:</td><td style="padding: 5px;">{ticket_type}</td></tr>
                    </table>
                </div>
                
                <div class="description">
                    <h3>📝 Issue Description</h3>
                    <p>{ticket_data.get('description', 'No description provided')}</p>
                </div>
                
                <div class="description">
                    <h3>🔧 AI Suggested Resolution</h3>
                    <p>{resolution_html}</p>
                </div>
                
                <h3>⚡ Action Required</h3>
                <ol>
                    <li>Review the ticket details and AI suggestions above</li>
                    <li>Contact the customer if additional information is needed</li>
                    <li>Update ticket status as you work on the resolution</li>
                    <li>Close the ticket once resolved with resolution notes</li>
                </ol>
                
                <p><strong>Need help?</strong> Contact the support team lead or check the knowledge base.</p>
            </div>
            
            <div class="footer">
                <p>This is an automated assignment from TeamLogic Support System.<br>
                Please acknowledge receipt and begin working on this ticket.</p>
            </div>
        </body>
        </html>
        """
        return html_content

    def _create_assignment_email_text(self, ticket_data: Dict, ticket_number: str) -> str:
        """
        Create plain text version of the technician assignment email.
        """
        classified_data = ticket_data.get('classified_data', {})
        resolution_note = ticket_data.get('resolution_note', 'No resolution note available')
        
        # Get classification labels
        issue_type = classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')
        priority = classified_data.get('PRIORITY', {}).get('Label', 'N/A')
        ticket_type = classified_data.get('TICKETTYPE', {}).get('Label', 'N/A')
        
        text_content = f"""
NEW TICKET ASSIGNMENT - #{ticket_number}

A new ticket has been assigned to you!

TICKET DETAILS:
- Ticket Number: #{ticket_number}
- Title: {ticket_data.get('title', 'N/A')}
- Customer: {ticket_data.get('name', 'N/A')}
- Customer Email: {ticket_data.get('email', 'N/A')}
- Date Created: {ticket_data.get('date', 'N/A')} {ticket_data.get('time', 'N/A')}
- Due Date: {ticket_data.get('due_date', 'N/A')}
- Priority: {priority}
- Issue Type: {issue_type}
- Ticket Type: {ticket_type}

ISSUE DESCRIPTION:
{ticket_data.get('description', 'No description provided')}

AI SUGGESTED RESOLUTION:
{resolution_note}

ACTION REQUIRED:
1. Review the ticket details and AI suggestions above
2. Contact the customer if additional information is needed
3. Update ticket status as you work on the resolution
4. Close the ticket once resolved with resolution notes

Need help? Contact the support team lead or check the knowledge base.

---
This is an automated assignment from TeamLogic Support System.
Please acknowledge receipt and begin working on this ticket.
        """
        return text_content.strip()
