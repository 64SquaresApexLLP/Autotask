"""
LLM-Based Notification Agent for IT Support System
Generates dynamic email notifications using AI based on ticket metadata
"""

import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from datetime import datetime
import logging

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import configuration
try:
    from config import (
        MANAGER_EMAIL, FALLBACK_TECHNICIAN_EMAIL, SUPPORT_EMAIL, SUPPORT_PHONE,
        HIGH_PRIORITY_NOTIFICATIONS, ESCALATION_KEYWORDS
    )
except ImportError:
    # Fallback values if config import fails
    MANAGER_EMAIL = os.getenv('MANAGER_EMAIL', 'itmanager@company.com')
    FALLBACK_TECHNICIAN_EMAIL = os.getenv('FALLBACK_TECHNICIAN_EMAIL', 'support@company.com')
    SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@company.com')
    SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '1-800-SUPPORT')
    HIGH_PRIORITY_NOTIFICATIONS = ['Critical', 'High', 'Desktop/User Down']
    ESCALATION_KEYWORDS = ['fallback', 'failed', 'error', 'escalated']

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationAgent:
    """
    LLM-powered notification agent that generates contextual email notifications
    based on ticket metadata and recipient type.
    """

    def __init__(self, db_connection=None):
        """
        Initialize the LLM-based notification agent.

        Args:
            db_connection: Database connection for LLM access (Snowflake Cortex)
        """
        # SMTP Configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', os.getenv('EMAIL_ACCOUNT', 'rohankul2017@gmail.com'))
        self.smtp_password = os.getenv('SMTP_PASSWORD', os.getenv('SUPPORT_EMAIL_PASSWORD'))
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)
        self.from_name = os.getenv('FROM_NAME', 'TeamLogic Support')

        # LLM Configuration
        self.db_connection = db_connection
        self.llm_enabled = db_connection is not None
        self.llm_model = 'mixtral-8x7b'

        # Email Configuration
        self.enabled = bool(self.smtp_password)

        if not self.enabled:
            logger.warning("SMTP password not configured. Email notifications disabled.")

        logger.info(f"NotificationAgent initialized - SMTP: {'enabled' if self.enabled else 'disabled'}, LLM: {'enabled' if self.llm_enabled else 'disabled'}")

    def generate_email_notification(self, notification_type: str, ticket_data: Dict,
                                  recipient_type: str = "customer") -> Dict[str, str]:
        """
        Generate email notification content using LLM based on ticket metadata.

        Args:
            notification_type (str): Type of notification (confirmation, assignment, status_update, etc.)
            ticket_data (dict): Complete ticket data with metadata
            recipient_type (str): Type of recipient (customer, technician, manager)

        Returns:
            dict: Email content with subject, html_content, text_content
        """
        if not self.llm_enabled:
            logger.warning("LLM not available - using basic template")
            return self._generate_basic_template(notification_type, ticket_data, recipient_type)

        try:
            # Build LLM prompt with ticket context
            prompt = self._build_llm_prompt(notification_type, ticket_data, recipient_type)

            # Call LLM to generate content with improved JSON handling
            logger.info(f"Generating {notification_type} email for {recipient_type} using LLM...")
            llm_response = self._call_llm_with_json_fix(prompt)

            if llm_response and isinstance(llm_response, dict):
                return {
                    'subject': llm_response.get('subject', f"Ticket #{ticket_data.get('ticket_number', 'N/A')} - {notification_type.title()}"),
                    'html_content': llm_response.get('html_content', ''),
                    'text_content': llm_response.get('text_content', '')
                }
            else:
                logger.warning("Invalid LLM response - using basic template")
                return self._generate_basic_template(notification_type, ticket_data, recipient_type)

        except Exception as e:
            logger.error(f"LLM email generation failed: {str(e)}")
            return self._generate_basic_template(notification_type, ticket_data, recipient_type)

    def _build_llm_prompt(self, notification_type: str, ticket_data: Dict, recipient_type: str) -> str:
        """Build comprehensive LLM prompt for email generation."""

        # Extract ticket metadata
        classified_data = ticket_data.get('classified_data', {})
        extracted_metadata = ticket_data.get('extracted_metadata', {})
        assignment_result = ticket_data.get('assignment_result', {})

        # Build comprehensive ticket context with all required metadata
        ticket_context = f"""
TICKET INFORMATION (All fields must be included in the notification):
- Ticket Number: #{ticket_data.get('ticket_number', 'N/A')}
- Title: {ticket_data.get('title', 'N/A')}
- Submitted By: {ticket_data.get('name', 'N/A')} ({ticket_data.get('user_email', 'N/A')})
- Date Created: {ticket_data.get('date', 'N/A')} {ticket_data.get('time', 'N/A')}
- Due Date: {ticket_data.get('due_date', 'N/A')}
- Priority: {classified_data.get('PRIORITY', {}).get('Label', ticket_data.get('priority', 'N/A'))}
- Issue Type: {classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')}
- Ticket Type: {classified_data.get('TICKETTYPE', {}).get('Label', 'N/A')}
- Description: {ticket_data.get('description', 'N/A')}
- Main Issue: {extracted_metadata.get('main_issue', 'N/A')}
- Affected Systems: {', '.join(extracted_metadata.get('affected_systems', [])) if extracted_metadata.get('affected_systems') else 'N/A'}
- Error Messages: {extracted_metadata.get('error_messages', 'N/A')}

TECHNICIAN INFORMATION:
- Assigned Technician Name: {assignment_result.get('assigned_technician', 'N/A')}
- Technician Email: {assignment_result.get('technician_email', 'N/A')}

RESOLUTION INFORMATION:
- Resolution Note: {ticket_data.get('resolution_note', 'N/A')}
"""

        # Get notification-specific instructions
        notification_instructions = self._get_notification_instructions(notification_type, ticket_data)

        # Get recipient-specific tone
        recipient_tone = self._get_recipient_tone(recipient_type)

        # Build complete prompt with explicit JSON formatting instructions
        prompt = f"""
You are an expert email communication specialist for an IT support system. Generate a professional, contextual email notification.

{ticket_context}

NOTIFICATION TYPE: {notification_type}
RECIPIENT TYPE: {recipient_type}
TONE: {recipient_tone}

{notification_instructions}

CRITICAL: Respond with VALID JSON only. Use proper escaping for quotes and backslashes.

RESPONSE FORMAT (VALID JSON):
{{
    "subject": "Clear, specific email subject line",
    "html_content": "Complete HTML email with professional styling and all metadata",
    "text_content": "Well-formatted plain text version with all metadata"
}}

REQUIREMENTS:
- Use professional, clear language appropriate for IT support
- MANDATORY: Include ALL metadata fields in structured format
- Make HTML version visually appealing with metadata tables
- Ensure text version is well-formatted with clear metadata sections
- Use appropriate tone for recipient type: {recipient_tone}
- Include TeamLogic Support branding
- IMPORTANT: Use "html_content" and "text_content" (no backslashes!)
"""

        return prompt

    def _call_llm_with_json_fix(self, prompt: str) -> Dict:
        """
        Call LLM and fix common JSON issues in the response.

        Args:
            prompt (str): The prompt to send to the LLM

        Returns:
            dict: Parsed LLM response or None if failed
        """
        try:
            # Get raw response from LLM
            raw_response = self.db_connection.call_cortex_llm(prompt, model=self.llm_model, expect_json=False)

            if not raw_response:
                return None

            # Fix common JSON issues
            fixed_json = self._fix_json_response(raw_response)

            if fixed_json:
                import json
                return json.loads(fixed_json)
            else:
                return None

        except Exception as e:
            logger.error(f"LLM call with JSON fix failed: {str(e)}")
            return None

    def _fix_json_response(self, raw_response: str) -> str:
        """
        Fix common JSON formatting issues in LLM responses.

        Args:
            raw_response (str): Raw response from LLM

        Returns:
            str: Fixed JSON string or None if unfixable
        """
        try:
            import re

            # Extract JSON block if it exists
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if not json_match:
                return None

            json_str = json_match.group(0)

            # Fix the most common issue: html\_content -> html_content
            json_str = json_str.replace('html\\_content', 'html_content')
            json_str = json_str.replace('text\\_content', 'text_content')

            # Fix other common escape issues
            json_str = json_str.replace('\\_', '_')

            return json_str

        except Exception as e:
            logger.warning(f"Failed to fix JSON response: {str(e)}")
            return None

    def _get_notification_instructions(self, notification_type: str, ticket_data: Dict) -> str:
        """Get specific instructions for each notification type."""

        instructions = {
            'confirmation': """
INSTRUCTIONS: Generate a customer confirmation email that:
1. Thanks the customer warmly for submitting their ticket
2. Confirms receipt with clear ticket number reference
3. MUST include ALL metadata fields in a structured format:
   - Ticket Number, Title, Submitted By (name and email), Date Created, Due Date
   - Priority, Issue Type, Ticket Type, Assigned Technician (name and email)
4. Summarizes the issue in customer-friendly language
5. Sets clear expectations for response time and next steps
6. Provides contact information for urgent issues
7. Uses an empathetic and reassuring tone
8. Format metadata in a clear, professional table or structured layout
""",
            'assignment': """
INSTRUCTIONS: Generate a technician assignment email that:
1. Clearly states a new ticket has been assigned
2. MUST include ALL metadata fields in a structured format:
   - Ticket Number, Title, Submitted By (name and email), Date Created, Due Date
   - Priority, Issue Type, Ticket Type, Technician Name, Technician Email
3. MUST include the complete AI-generated resolution steps in a prominent section
4. Provides comprehensive ticket details and customer contact information
5. Outlines specific actions required and deadlines
6. Uses a professional and action-oriented tone
7. Includes escalation procedures if needed
8. Format metadata in a clear, professional table or structured layout
9. Highlight the resolution steps as actionable guidance for the technician
""",
            'status_update': f"""
INSTRUCTIONS: Generate a status update email that:
1. Clearly communicates the status change: {ticket_data.get('status_change', 'Status updated')}
2. Provides context and reasoning for the update
3. Includes timeline information and next steps
4. Sets appropriate expectations for resolution
5. Uses a professional and informative tone
""",
            'escalation': f"""
INSTRUCTIONS: Generate an escalation email that:
1. Clearly indicates the ticket has been escalated
2. Explains the reason: {ticket_data.get('escalation_reason', 'Requires specialized attention')}
3. Provides complete ticket history and context
4. Sets new expectations and timelines
5. Uses an urgent but professional tone
6. Includes immediate action items
""",
            'resolution': f"""
INSTRUCTIONS: Generate a resolution email that:
1. Confirms the ticket has been successfully resolved
2. Summarizes the solution: {ticket_data.get('resolution_summary', ticket_data.get('resolution_note', 'Issue resolved'))}
3. Provides any necessary follow-up instructions
4. Requests feedback and satisfaction rating
5. Uses a positive and helpful tone
"""
        }

        return instructions.get(notification_type, f"Generate a professional {notification_type} email with relevant ticket information.")

    def _get_recipient_tone(self, recipient_type: str) -> str:
        """Get appropriate tone for recipient type."""

        tones = {
            'customer': 'friendly, empathetic, and reassuring',
            'technician': 'professional, direct, and action-oriented',
            'manager': 'formal, concise, and informative',
            'team': 'collaborative and informative'
        }

        return tones.get(recipient_type, 'professional')

    def _generate_basic_template(self, notification_type: str, ticket_data: Dict, recipient_type: str) -> Dict[str, str]:
        """Generate basic email template when LLM is not available."""

        # Extract all required metadata
        ticket_number = ticket_data.get('ticket_number', 'N/A')
        title = ticket_data.get('title', 'N/A')
        customer_name = ticket_data.get('name', 'N/A')
        customer_email = ticket_data.get('user_email', 'N/A')
        date_created = f"{ticket_data.get('date', 'N/A')} {ticket_data.get('time', 'N/A')}"
        due_date = ticket_data.get('due_date', 'N/A')

        # Extract classification data
        classified_data = ticket_data.get('classified_data', {})
        priority = classified_data.get('PRIORITY', {}).get('Label', ticket_data.get('priority', 'N/A'))
        issue_type = classified_data.get('ISSUETYPE', {}).get('Label', 'N/A')
        ticket_type = classified_data.get('TICKETTYPE', {}).get('Label', 'N/A')

        # Extract technician information
        assignment_result = ticket_data.get('assignment_result', {})
        technician_name = assignment_result.get('assigned_technician', 'N/A')
        technician_email = assignment_result.get('technician_email', 'N/A')

        # Extract resolution information
        resolution_note = ticket_data.get('resolution_note', 'N/A')

        if notification_type == 'confirmation':
            return self._generate_customer_confirmation_template(
                ticket_number, title, customer_name, customer_email, date_created,
                due_date, priority, issue_type, ticket_type, technician_name, technician_email
            )
        elif notification_type == 'assignment':
            return self._generate_technician_assignment_template(
                ticket_number, title, customer_name, customer_email, date_created,
                due_date, priority, issue_type, ticket_type, technician_name, technician_email, resolution_note
            )
        else:
            return {
                'subject': f"Ticket #{ticket_number} - {notification_type.title()}",
                'html_content': f"<p>Ticket #{ticket_number} - {notification_type.title()}</p>",
                'text_content': f"Ticket #{ticket_number} - {notification_type.title()}"
            }

    def _generate_customer_confirmation_template(self, ticket_number: str, title: str, customer_name: str,
                                               customer_email: str, date_created: str, due_date: str,
                                               priority: str, issue_type: str, ticket_type: str,
                                               technician_name: str, technician_email: str) -> Dict[str, str]:
        """Generate enhanced customer confirmation template with all required metadata."""

        return {
            'subject': f"🎫 Ticket Confirmation - #{ticket_number}",
            'html_content': f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2c3e50;">🎫 Ticket Confirmation</h2>
                <p>Dear {customer_name},</p>
                <p>Thank you for contacting TeamLogic Support. Your support ticket has been successfully received and assigned the following details:</p>

                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #495057; margin-top: 0;">📋 Ticket Details</h3>
                    <p style="line-height: 1.6; margin: 0;">
                        <strong>Ticket Number:</strong> #{ticket_number}<br>
                        <strong>Title:</strong> {title}<br>
                        <strong>Submitted By:</strong> {customer_name} ({customer_email})<br>
                        <strong>Date Created:</strong> {date_created}<br>
                        <strong>Due Date:</strong> {due_date}<br>
                        <strong>Priority:</strong> {priority}<br>
                        <strong>Issue Type:</strong> {issue_type}<br>
                        <strong>Ticket Type:</strong> {ticket_type}<br>
                        <strong>Assigned Technician:</strong> {technician_name}
                    </p>
                </div>

                <p>Our team will review your ticket and respond within 2 business hours.</p>
                <p>If you have any urgent concerns, please contact us immediately.</p>

                <p>Best regards,<br>
                <strong>TeamLogic Support</strong></p>
            </div>
            """,
            'text_content': f"""
🎫 Ticket Confirmation

Dear {customer_name},

Thank you for contacting TeamLogic Support. Your support ticket has been successfully received and assigned the following details:

📋 Ticket Details
Ticket Number: #{ticket_number}
Title: {title}
Submitted By: {customer_name} ({customer_email})
Date Created: {date_created}
Due Date: {due_date}
Priority: {priority}
Issue Type: {issue_type}
Ticket Type: {ticket_type}
Assigned Technician: {technician_name}

Our team will review your ticket and respond within 2 business hours.
If you have any urgent concerns, please contact us immediately.

Best regards,
TeamLogic Support
            """
        }

    def _generate_technician_assignment_template(self, ticket_number: str, title: str, customer_name: str,
                                               customer_email: str, date_created: str, due_date: str,
                                               priority: str, issue_type: str, ticket_type: str,
                                               technician_name: str, technician_email: str, resolution_note: str) -> Dict[str, str]:
        """Generate enhanced technician assignment template with all required metadata including resolution."""

        return {
            'subject': f"🔧 New Ticket Assignment - #{ticket_number}",
            'html_content': f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2c3e50;">🔧 New Ticket Assignment</h2>
                <p>A new support ticket has been assigned to you. Please review the details below and begin working on this ticket.</p>

                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #495057; margin-top: 0;">📋 Ticket Details</h3>
                    <div style="line-height: 1.6;">
                        <strong>Ticket Number:</strong> #{ticket_number}<br>
                        <strong>Title:</strong> {title}<br>
                        <strong>Submitted By:</strong> {customer_name} ({customer_email})<br>
                        <strong>Date Created:</strong> {date_created}<br>
                        <strong>Due Date:</strong> {due_date}<br>
                        <strong>Priority:</strong> {priority}<br>
                        <strong>Issue Type:</strong> {issue_type}<br>
                        <strong>Ticket Type:</strong> {ticket_type}<br>
                        <strong>Assigned Technician:</strong> {technician_name} ({technician_email})
                    </div>
                </div>

                <div style="background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="color: #2d5a2d; margin-top: 0;">AI-Generated Resolution Steps</h3>
                    <div style="white-space: pre-wrap; font-family: 'Courier New', monospace; background-color: white; padding: 10px; border-radius: 3px;">
{resolution_note}
                    </div>
                </div>

                <p><strong>Next Steps:</strong></p>
                <ul>
                    <li>Review the ticket details and AI-generated resolution steps</li>
                    <li>Contact the customer if additional information is needed</li>
                    <li>Begin troubleshooting based on the suggested resolution</li>
                    <li>Update the ticket status as you progress</li>
                </ul>

                <p>Please ensure this ticket is resolved by the due date: <strong>{due_date}</strong></p>

                <p>Best regards,<br>
                <strong>TeamLogic Support System</strong></p>
            </div>
            """,
            'text_content': f"""
🔧 New Ticket Assignment

A new support ticket has been assigned to you. Please review the details below and begin working on this ticket.

📋 Ticket Details
Ticket Number: #{ticket_number}
Title: {title}
Submitted By: {customer_name} ({customer_email})
Date Created: {date_created}
Due Date: {due_date}
Priority: {priority}
Issue Type: {issue_type}
Ticket Type: {ticket_type}
Assigned Technician: {technician_name} ({technician_email})

🔧 AI-Generated Resolution Steps:
{resolution_note}

📝 Next Steps:
- Review the ticket details and AI-generated resolution steps
- Contact the customer if additional information is needed
- Begin troubleshooting based on the suggested resolution
- Update the ticket status as you progress

Please ensure this ticket is resolved by the due date: {due_date}

Best regards,
TeamLogic Support System
            """
        }

    def send_email(self, recipient_email: str, email_content: Dict[str, str]) -> bool:
        """
        Send email using SMTP.

        Args:
            recipient_email (str): Recipient's email address
            email_content (dict): Email content with subject, html_content, text_content

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email sending disabled - SMTP not configured")
            return False

        if not recipient_email or not recipient_email.strip():
            logger.warning("No recipient email provided")
            return False

        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_content['subject']
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email

            # Attach text and HTML versions
            text_part = MIMEText(email_content['text_content'], 'plain')
            html_part = MIMEText(email_content['html_content'], 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False

    # Convenience methods for backward compatibility and integration
    def send_ticket_confirmation(self, user_email: str, ticket_data: Dict, ticket_number: str) -> bool:
        """Send ticket confirmation email to customer."""
        ticket_data['ticket_number'] = ticket_number
        email_content = self.generate_email_notification('confirmation', ticket_data, 'customer')
        return self.send_email(user_email, email_content)

    def send_technician_assignment(self, technician_email: str, ticket_data: Dict, ticket_number: str) -> bool:
        """Send assignment notification to technician."""
        ticket_data['ticket_number'] = ticket_number
        email_content = self.generate_email_notification('assignment', ticket_data, 'technician')
        return self.send_email(technician_email, email_content)

    def send_assignment_notifications(self, ticket_data: Dict) -> Dict[str, bool]:
        """
        Send assignment notifications based on assignment result.
        Integrates with the assignment agent workflow.

        Args:
            ticket_data (dict): Complete ticket data with assignment_result

        Returns:
            dict: Results of notification attempts
        """
        results = {
            'customer_notified': False,
            'technician_notified': False,
            'manager_notified': False
        }

        assignment_result = ticket_data.get('assignment_result', {})
        ticket_number = ticket_data.get('ticket_number', 'N/A')

        # Notify customer about assignment
        customer_email = ticket_data.get('user_email')
        if customer_email and customer_email.strip():
            logger.info(f"Sending assignment update to customer: {customer_email}")
            try:
                # Add assignment info to ticket data for context
                enhanced_ticket_data = ticket_data.copy()
                enhanced_ticket_data['status_change'] = f"Your ticket has been assigned to {assignment_result.get('assigned_technician', 'a technician')}"

                email_content = self.generate_email_notification('status_update', enhanced_ticket_data, 'customer')
                results['customer_notified'] = self.send_email(customer_email, email_content)
            except Exception as e:
                logger.error(f"Failed to send customer assignment notification: {e}")

        # Notify assigned technician
        technician_email = assignment_result.get('technician_email')
        if technician_email and technician_email.strip():
            logger.info(f"Sending assignment notification to technician: {technician_email}")
            try:
                results['technician_notified'] = self.send_technician_assignment(
                    technician_email, ticket_data, ticket_number
                )
            except Exception as e:
                logger.error(f"Failed to send technician assignment notification: {e}")

        # Notify manager for high priority or fallback assignments
        priority = assignment_result.get('priority', '')
        status = assignment_result.get('status', '')

        # Check if notification should be escalated to manager
        should_escalate = (
            priority in HIGH_PRIORITY_NOTIFICATIONS or
            any(keyword in status.lower() for keyword in ESCALATION_KEYWORDS)
        )

        if should_escalate:
            logger.info(f"Sending escalation notification to manager: {MANAGER_EMAIL}")
            try:
                enhanced_ticket_data = ticket_data.copy()
                if any(keyword in status.lower() for keyword in ESCALATION_KEYWORDS):
                    enhanced_ticket_data['escalation_reason'] = f'Assignment issue: {status} - requires management attention'
                else:
                    enhanced_ticket_data['escalation_reason'] = f'High priority ticket ({priority}) requires management attention'

                email_content = self.generate_email_notification('escalation', enhanced_ticket_data, 'manager')
                results['manager_notified'] = self.send_email(MANAGER_EMAIL, email_content)
            except Exception as e:
                logger.error(f"Failed to send manager escalation notification: {e}")

        return results

    def send_status_update(self, recipient_email: str, ticket_data: Dict, ticket_number: str,
                          status_change: str, recipient_type: str = "customer") -> bool:
        """Send status update notification."""
        ticket_data['ticket_number'] = ticket_number
        ticket_data['status_change'] = status_change
        email_content = self.generate_email_notification('status_update', ticket_data, recipient_type)
        return self.send_email(recipient_email, email_content)

    def send_escalation_notification(self, recipient_email: str, ticket_data: Dict, ticket_number: str,
                                   escalation_reason: str, recipient_type: str = "manager") -> bool:
        """Send escalation notification."""
        ticket_data['ticket_number'] = ticket_number
        ticket_data['escalation_reason'] = escalation_reason
        email_content = self.generate_email_notification('escalation', ticket_data, recipient_type)
        return self.send_email(recipient_email, email_content)

    def send_resolution_notification(self, recipient_email: str, ticket_data: Dict, ticket_number: str,
                                   resolution_summary: str, recipient_type: str = "customer") -> bool:
        """Send resolution notification."""
        ticket_data['ticket_number'] = ticket_number
        ticket_data['resolution_summary'] = resolution_summary
        email_content = self.generate_email_notification('resolution', ticket_data, recipient_type)
        return self.send_email(recipient_email, email_content)

    def send_email_processing_summary(self, processed_tickets: list, recipient_email: str = None) -> bool:
        """
        Send summary of email processing results to administrators.

        Args:
            processed_tickets (list): List of processed ticket results
            recipient_email (str): Email to send summary to (defaults to MANAGER_EMAIL)

        Returns:
            bool: True if sent successfully
        """
        if not processed_tickets:
            return True  # No need to send empty summary

        recipient = recipient_email or MANAGER_EMAIL

        try:
            # Create summary data
            total_processed = len(processed_tickets)
            successful = len([t for t in processed_tickets if t and t.get('ticket_number') != 'N/A'])
            failed = total_processed - successful

            # Build summary content
            summary_data = {
                'ticket_number': 'EMAIL-PROCESSING-SUMMARY',
                'title': f'Email Processing Summary - {total_processed} emails processed',
                'description': f'Processed {total_processed} emails: {successful} successful, {failed} failed',
                'total_processed': total_processed,
                'successful': successful,
                'failed': failed,
                'processed_tickets': processed_tickets,
                'processing_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Generate and send summary email
            email_content = self._generate_email_processing_summary(summary_data)
            return self.send_email(recipient, email_content)

        except Exception as e:
            logger.error(f"Failed to send email processing summary: {e}")
            return False

    def _generate_email_processing_summary(self, summary_data: Dict) -> Dict[str, str]:
        """Generate email processing summary content."""

        total = summary_data['total_processed']
        successful = summary_data['successful']
        failed = summary_data['failed']
        processing_time = summary_data['processing_time']

        # Create ticket list
        ticket_list = []
        for ticket in summary_data['processed_tickets']:
            if ticket:
                ticket_num = ticket.get('ticket_number', 'N/A')
                from_addr = ticket.get('from', 'Unknown')
                subject = ticket.get('subject', 'No subject')
                status = "✅ Success" if ticket_num != 'N/A' else "❌ Failed"
                ticket_list.append(f"  {status} {ticket_num} - From: {from_addr} - Subject: {subject}")
            else:
                ticket_list.append("  ❌ Failed - Processing error")

        tickets_text = '\n'.join(ticket_list) if ticket_list else "No tickets processed"

        subject = f"Email Processing Summary - {total} emails processed ({successful} successful, {failed} failed)"

        html_content = f"""
        <h2>📧 Email Processing Summary</h2>
        <p><strong>Processing Time:</strong> {processing_time}</p>

        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <h3>📊 Summary Statistics</h3>
            <ul>
                <li><strong>Total Emails Processed:</strong> {total}</li>
                <li><strong>✅ Successful:</strong> {successful}</li>
                <li><strong>❌ Failed:</strong> {failed}</li>
                <li><strong>Success Rate:</strong> {(successful/total*100):.1f}% if total > 0 else 0%</li>
            </ul>
        </div>

        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <h3>📋 Processed Tickets</h3>
            <pre style="white-space: pre-wrap; font-family: monospace;">{tickets_text}</pre>
        </div>

        <p>This is an automated summary from the TeamLogic Support System.</p>
        """

        text_content = f"""
EMAIL PROCESSING SUMMARY

Processing Time: {processing_time}

SUMMARY STATISTICS:
- Total Emails Processed: {total}
- Successful: {successful}
- Failed: {failed}
- Success Rate: {(successful/total*100):.1f}% if total > 0 else 0%

PROCESSED TICKETS:
{tickets_text}

---
This is an automated summary from the TeamLogic Support System.
        """

        return {
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content.strip()
        }