"""
TeamLogic-AutoTask Application
Main entry point - now modular and streamlined.
"""

import warnings
warnings.filterwarnings("ignore", message="You have an incompatible version of 'pyarrow' installed")

import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from collections import Counter
from typing import List, Dict
import threading
import time
import schedule
import pytz
import re
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr

# Core imports
from login import login_page
from config import *
from src.database.ticket_db import TicketDB
from src.database.snowflake_db import SnowflakeConnection
from src.agents import IntakeClassificationAgent
from src.data import DataManager
from src.ui import apply_custom_css, format_time_elapsed, format_date_display, get_duration_icon
from src.core import EmailProcessor, TicketHandlers, PageControllers

# Email integration config (based on test.py)
EMAIL_ACCOUNT = 'rohankul2017@gmail.com'
EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD')
IMAP_SERVER = 'imap.gmail.com'
FOLDER = 'inbox'
DEFAULT_TZ = 'Asia/Kolkata'
MAX_EMAILS = 20  # Increased slightly for 5-minute window
RECENT_MINUTES = 5  # Only process emails from last 5 minutes
DEFAULT_DUE_OFFSET_HOURS = 48
IST = pytz.timezone(DEFAULT_TZ)

# Global variables for automatic email processing
AUTO_EMAIL_PROCESSOR = None
EMAIL_PROCESSING_STATUS = {
    "is_running": False,
    "last_processed": None,
    "total_processed": 0,
    "error_count": 0,
    "recent_logs": []
}

def validate_email(email_address: str) -> bool:
    """
    Validate email address format using regex.

    Args:
        email_address (str): Email address to validate

    Returns:
        bool: True if email format is valid, False otherwise
    """
    if not email_address or not email_address.strip():
        return True  # Empty email is allowed (optional field)

    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email_address.strip()) is not None

@st.cache_resource
def get_agent(account, user, warehouse, database, schema, role, data_ref, _db_connection=None):
    """Initializes and returns the IntakeClassificationAgent with SSO authentication."""
    try:
        agent = IntakeClassificationAgent(
            sf_account=account,
            sf_user=user,
            sf_warehouse=warehouse,
            sf_database=database,
            sf_schema=schema,
            sf_role=role,
            data_ref_file=data_ref,
            db_connection=_db_connection
        )
        if not agent.db_connection or not agent.db_connection.conn:
            st.error("Failed to establish Snowflake connection. Please ensure SSO is properly configured and you have network access.")
            return None
        return agent
    except Exception as e:
        st.error(f"An error occurred during agent initialization: {e}")
        st.exception(e)
        return None

# Email processing now handled by EmailProcessor class

def should_process_as_ticket(msg):
    """Determine if an email should be processed as a support ticket."""
    try:
        # Extract subject and sender
        subject, encoding = decode_header(msg.get("Subject"))[0]
        subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject or ""
        from_ = msg.get("From") or ""

        # Skip common non-support email patterns
        skip_patterns = [
            # Marketing/Newsletter patterns
            'unsubscribe', 'newsletter', 'promotion', 'offer', 'deal', 'sale', 'discount',
            'marketing', 'campaign', 'advertisement', 'noreply', 'no-reply',

            # Job/Career patterns
            'job alert', 'hiring', 'career', 'naukri', 'indeed', 'linkedin',
            'internship', 'placement', 'recruitment',

            # Social/Review patterns
            'google maps', 'review', 'rating', 'social', 'facebook', 'twitter',
            'instagram', 'youtube', 'notification',

            # Travel/Booking patterns
            'booking', 'travel', 'hotel', 'flight', 'vacation', 'trip',
            'redbus', 'makemytrip', 'goibibo',

            # Educational patterns (unless it's a technical issue)
            'course', 'training', 'certification', 'nptel', 'coursera',
            'udemy', 'internshala trainings'
        ]

        # Support ticket indicators
        support_patterns = [
            # Technical issues
            'error', 'issue', 'problem', 'bug', 'crash', 'fail', 'not working',
            'cannot', 'unable', 'help', 'support', 'assistance', 'urgent',

            # System/Network issues
            'vpn', 'network', 'connection', 'server', 'database', 'system',
            'login', 'password', 'access', 'permission', 'timeout',

            # Application issues
            'outlook', 'excel', 'word', 'teams', 'software', 'application',
            'program', 'install', 'update', 'sync',

            # Hardware issues
            'printer', 'computer', 'laptop', 'monitor', 'keyboard', 'mouse'
        ]

        # Check if email has image attachments (likely support tickets)
        has_images = False
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type().startswith("image/"):
                    has_images = True
                    break

        # If it has images, likely a support ticket (screenshots)
        if has_images:
            return True

        # Check subject and sender for patterns
        text_to_check = f"{subject} {from_}".lower()

        # Skip if matches skip patterns
        for pattern in skip_patterns:
            if pattern in text_to_check:
                return False

        # Process if matches support patterns
        for pattern in support_patterns:
            if pattern in text_to_check:
                return True

        # Default: skip emails that don't clearly look like support tickets
        return False

    except Exception:
        # When in doubt, process it
        return True

def fetch_and_process_emails(agent):
    """Fetch and process emails using the modular EmailProcessor."""
    email_processor = EmailProcessor(EMAIL_ACCOUNT, EMAIL_PASSWORD, IMAP_SERVER)
    data_manager = DataManager(DATA_REF_FILE, KNOWLEDGEBASE_FILE)
    return email_processor.process_recent_emails(agent, data_manager, RECENT_MINUTES)




def log_email_status(level, message):
    """Log email processing status"""
    global EMAIL_PROCESSING_STATUS
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    EMAIL_PROCESSING_STATUS["recent_logs"].append(log_entry)

    # Keep only last 20 log entries
    if len(EMAIL_PROCESSING_STATUS["recent_logs"]) > 20:
        EMAIL_PROCESSING_STATUS["recent_logs"] = EMAIL_PROCESSING_STATUS["recent_logs"][-20:]

def automatic_email_processing_job(agent):
    """Job function that runs every 5 minutes to process emails from last 5 minutes only"""
    global EMAIL_PROCESSING_STATUS

    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🔄 [{current_time}] Auto processing emails from last {RECENT_MINUTES} minutes...")
        log_email_status("INFO", f"Processing emails from last {RECENT_MINUTES} minutes")

        # Process emails
        results = fetch_and_process_emails(agent)

        if isinstance(results, str):
            # Error occurred
            print(f"❌ Email processing error: {results}")
            EMAIL_PROCESSING_STATUS["error_count"] += 1
            log_email_status("ERROR", results)
        elif isinstance(results, list):
            # Success
            processed_count = len(results)
            EMAIL_PROCESSING_STATUS["total_processed"] += processed_count
            EMAIL_PROCESSING_STATUS["last_processed"] = current_time

            if processed_count > 0:
                print(f"✅ Auto-processed {processed_count} new emails")
                log_email_status("SUCCESS", f"Processed {processed_count} emails")

                # Update session state if available
                if 'auto_processed_emails' not in st.session_state:
                    st.session_state.auto_processed_emails = []
                st.session_state.auto_processed_emails.extend(results)

                # Keep only last 50 processed emails in session
                if len(st.session_state.auto_processed_emails) > 50:
                    st.session_state.auto_processed_emails = st.session_state.auto_processed_emails[-50:]
            else:
                print("📭 No new emails to auto-process")
                log_email_status("INFO", "No new emails found")

    except Exception as e:
        print(f"❌ Error in automatic email processing: {e}")
        EMAIL_PROCESSING_STATUS["error_count"] += 1
        log_email_status("ERROR", str(e))

def start_automatic_email_processing(agent):
    """Start automatic email processing every 5 minutes"""
    global AUTO_EMAIL_PROCESSOR, EMAIL_PROCESSING_STATUS

    if EMAIL_PROCESSING_STATUS["is_running"]:
        return "⚠️ Automatic email processing is already running"

    try:
        # Clear previous schedule
        schedule.clear()

        # Schedule the job to run every 5 minutes
        schedule.every(5).minutes.do(automatic_email_processing_job, agent)

        # Run once immediately
        automatic_email_processing_job(agent)

        EMAIL_PROCESSING_STATUS["is_running"] = True
        log_email_status("INFO", "Automatic email processing started")

        # Start the scheduler in a separate thread
        def run_scheduler():
            while EMAIL_PROCESSING_STATUS["is_running"]:
                schedule.run_pending()
                time.sleep(1)

        AUTO_EMAIL_PROCESSOR = threading.Thread(target=run_scheduler, daemon=True)
        AUTO_EMAIL_PROCESSOR.start()

        return "✅ Automatic email processing started! Will check for new emails every 5 minutes."

    except Exception as e:
        EMAIL_PROCESSING_STATUS["is_running"] = False
        log_email_status("ERROR", f"Failed to start automatic processing: {str(e)}")
        return f"❌ Failed to start automatic email processing: {str(e)}"

def stop_automatic_email_processing():
    """Stop automatic email processing"""
    global EMAIL_PROCESSING_STATUS

    if not EMAIL_PROCESSING_STATUS["is_running"]:
        return "⚠️ Automatic email processing is not running"

    try:
        EMAIL_PROCESSING_STATUS["is_running"] = False
        schedule.clear()
        log_email_status("INFO", "Automatic email processing stopped")
        return "✅ Automatic email processing stopped"

    except Exception as e:
        log_email_status("ERROR", f"Error stopping automatic processing: {str(e)}")
        return f"❌ Error stopping automatic email processing: {str(e)}"

def process_email_with_images(msg, agent, image_processor):
    """Process a single email with image attachment support based on test.py pattern."""
    import tempfile
    import os

    # Extract basic email info (following test.py pattern)
    subject, encoding = decode_header(msg.get("Subject"))[0]
    subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject
    from_ = msg.get("From")
    name, addr = parseaddr(from_)
    email_date = msg.get("Date")
    received_dt = parsedate_to_datetime(email_date).astimezone(IST)

    # Extract email body (following test.py pattern)
    body = ""
    image_attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = part.get("Content-Disposition", "")

            # Extract text content
            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(errors="ignore")

            # Extract image attachments
            elif content_type.startswith("image/") and image_processor:
                filename = part.get_filename()
                if filename:
                    try:
                        # Save attachment to temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                            temp_file.write(part.get_payload(decode=True))
                            temp_path = temp_file.name

                        image_attachments.append({
                            'filename': filename,
                            'path': temp_path
                        })
                        print(f"📎 Found image attachment: {filename}")
                    except Exception as e:
                        print(f"❌ Error processing attachment {filename}: {e}")
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    # Process images if any
    image_analysis = ""
    has_images = len(image_attachments) > 0

    if image_attachments and image_processor:
        print(f"🖼️ Processing {len(image_attachments)} image attachments...")

        for attachment in image_attachments:
            try:
                # Process image with the image processor
                image_result = image_processor.process_image(attachment['path'], model='mixtral-8x7b')

                if image_result and image_result.get('has_useful_content'):
                    metadata = image_result.get('metadata', {})

                    # Add image analysis to description
                    image_analysis += f"\n\n--- Image Analysis: {attachment['filename']} ---"

                    # Add extracted text if available
                    extracted_text = metadata.get('extracted_text', '')
                    if extracted_text:
                        image_analysis += f"\nExtracted Text: {extracted_text}"

                    # Add error detection info
                    if metadata.get('likely_error_screenshot'):
                        image_analysis += "\n⚠️ Error Screenshot Detected"

                    # Add technical keywords
                    technical_analysis = metadata.get('technical_analysis', {})
                    if technical_analysis:
                        keywords = [item for sublist in technical_analysis.values() for item in sublist]
                        if keywords:
                            image_analysis += f"\nTechnical Keywords: {', '.join(keywords)}"

                # Clean up temporary file
                os.unlink(attachment['path'])

            except Exception as e:
                print(f"❌ Error processing image {attachment['filename']}: {e}")
                try:
                    os.unlink(attachment['path'])
                except:
                    pass

    # Prepare full text for due date extraction
    full_text = f"{subject}\n{body}{image_analysis}"

    # Extract due date using NLP (following test.py pattern)
    due_date = extract_due_date_nlp(full_text, received_dt)

    # Enhanced description with image analysis
    enhanced_description = body.strip()
    if image_analysis:
        enhanced_description += image_analysis

    # Process ticket with agent (following test.py pattern)
    try:
        result = agent.process_new_ticket(
            ticket_name=name or addr,
            ticket_description=enhanced_description,
            ticket_title=subject.strip(),
            due_date=due_date,
            priority_initial='High' if has_images else 'Medium',
            user_email=addr  # Use sender's email for notifications
        )

        return {
            'from': name or addr,
            'subject': subject.strip(),
            'due_date': due_date,
            'has_images': has_images,
            'image_count': len(image_attachments),
            'ticket_number': result.get('ticket_number', 'N/A') if result else 'N/A'
        }

    except Exception as e:
        print(f"❌ Error creating ticket: {e}")
        return None

def extract_due_date_nlp(text, received_dt):
    """Extract due date from text using NLP (based on test.py implementation)."""
    text = text.lower()

    # 1. Custom Handling: "tomorrow"
    if "tomorrow" in text:
        result = received_dt + timedelta(days=1)
        return result.strftime('%Y-%m-%d')

    # 2. Custom Handling: "next <weekday>"
    match_next_day = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', text)
    if match_next_day:
        weekday_str = match_next_day.group(1)
        weekday_target = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].index(weekday_str)
        days_ahead = (weekday_target - received_dt.weekday() + 7) % 7
        days_ahead = 7 if days_ahead == 0 else days_ahead
        result = received_dt + timedelta(days=days_ahead)
        return result.strftime('%Y-%m-%d')

    # 3. Custom Handling: "in 3 working days"
    match_working = re.search(r'(?:in|within)\s+(\d{1,2})\s+working\s+days?', text)
    if match_working:
        days = int(match_working.group(1))
        added = 0
        current = received_dt
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current.strftime('%Y-%m-%d')

    # 4. Simple date patterns: "by 2025-07-05" or "due 05/07/2025"
    date_patterns = [
        r'(?:by|due|before)\s+(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(?:by|due|before)\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                if len(match.group(1)) == 4:  # YYYY-MM-DD format
                    year, month, day = map(int, match.groups())
                else:  # DD/MM/YYYY format
                    day, month, year = map(int, match.groups())

                target_date = datetime(year, month, day, tzinfo=received_dt.tzinfo)
                if target_date > received_dt:
                    return target_date.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue

    # 5. Regex: 'after 4-7-2025 and before 7-7-2025'
    match_window = re.search(r'after\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})\s+and\s+before\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})', text)
    if match_window:
        d1, m1, y1, d2, m2, y2 = map(int, match_window.groups())
        try:
            start = datetime(y1, m1, d1, tzinfo=received_dt.tzinfo)
            end = datetime(y2, m2, d2, tzinfo=received_dt.tzinfo)
            mid = start + (end - start) / 2
            return mid.strftime('%Y-%m-%d')
        except:
            pass

    # 6. Final fallback: 48-hour default
    fallback = received_dt + timedelta(hours=DEFAULT_DUE_OFFSET_HOURS)
    return fallback.strftime('%Y-%m-%d')

# Note: main_page function moved to PageControllers class

# Note: Orphaned code from old main_page function removed

def filter_tickets_by_duration(kb_data, duration, now):
    from datetime import timedelta
    if duration == "Last hour":
        cutoff_time = now - timedelta(hours=1)
    elif duration == "Last 2 hours":
        cutoff_time = now - timedelta(hours=2)
    elif duration == "Last 6 hours":
        cutoff_time = now - timedelta(hours=6)
    elif duration == "Last 12 hours":
        cutoff_time = now - timedelta(hours=12)
    elif duration == "Today":
        cutoff_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif duration == "Yesterday":
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        filtered = []
        for entry in kb_data:
            t = entry['new_ticket']
            try:
                created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
                if start_time <= created_time <= end_time:
                    filtered.append(t)
            except:
                continue
        return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)
    elif duration == "Last 3 days":
        cutoff_time = now - timedelta(days=3)
    elif duration == "Last week":
        cutoff_time = now - timedelta(weeks=1)
    elif duration == "Last month":
        cutoff_time = now - timedelta(days=30)
    elif duration == "All tickets":
        return [entry['new_ticket'] for entry in sorted(kb_data, key=lambda x: x['new_ticket']["date"] + x['new_ticket']["time"], reverse=True)]
    else:
        cutoff_time = now - timedelta(hours=24)
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        try:
            created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
            if created_time >= cutoff_time:
                filtered.append(t)
        except:
            continue
    return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)

def filter_tickets_by_date_range(kb_data, start_date, end_date):
    from datetime import datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        try:
            created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
            if start_datetime <= created_time <= end_datetime:
                filtered.append(t)
        except:
            continue
    return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)

def filter_tickets_by_specific_date(kb_data, selected_date):
    from datetime import datetime
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        try:
            created_time = datetime.fromisoformat(t['date'] + 'T' + t['time'])
            if created_time.date() == selected_date:
                filtered.append(t)
        except:
            continue
    return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)

def search_tickets_by_number(kb_data, ticket_number):
    """Search for tickets by ticket number or partial match"""
    if not ticket_number or not ticket_number.strip():
        return []

    search_term = ticket_number.strip().upper()
    filtered = []

    for entry in kb_data:
        t = entry['new_ticket']
        ticket_num = t.get('ticket_number', '').upper()

        # Check if ticket has a ticket number and it matches
        if ticket_num and search_term in ticket_num:
            filtered.append(t)
        # Handle partial searches for new format (T20240916.0057)
        elif ticket_num and search_term.replace('.', '') in ticket_num.replace('.', ''):
            filtered.append(t)
        # Handle partial searches for old format (TL-20240916-XXXX)
        elif ticket_num and search_term.replace('-', '') in ticket_num.replace('-', ''):
            filtered.append(t)
        # Also search in title for backward compatibility
        elif search_term in t.get('title', '').upper():
            filtered.append(t)

    return sorted(filtered, key=lambda x: x["date"] + x["time"], reverse=True)

def recent_tickets_page(data_manager):
    """Dynamic recent tickets page with multiple filtering options (now optimized)"""
    kb_data = load_kb_data()
    now = datetime.now()
    with st.container():
        if st.button("← Back to Home", key="rt_back"):
            st.session_state.page = "main"
            st.rerun()
        st.title("🕑 Recent Raised Tickets")
        tab1, tab2, tab3, tab4 = st.tabs(["⏰ Duration Filter", "📅 Date Range Filter", "📆 Specific Date Filter", "🔍 Search Tickets"])
        tickets_to_display = []
        filter_description = ""
        with tab1:
            st.markdown("### Select Time Duration")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                selected_duration = st.selectbox(
                    "📅 Select Time Duration:",
                    options=DURATION_OPTIONS,
                    index=0,
                    key="duration_selector"
                )
            with col2:
                if st.button("Apply Duration Filter", key="apply_duration"):
                    tickets_to_display = filter_tickets_by_duration(kb_data, selected_duration, now)
                    filter_description = f"{get_duration_icon(selected_duration)} {selected_duration}"
                    st.session_state.active_filter = "duration"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display
            with col3:
                preview_tickets = filter_tickets_by_duration(kb_data, selected_duration, now)
                st.metric("Tickets Found", len(preview_tickets))
        with tab2:
            st.markdown("### Select Date Range")
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                start_date = st.date_input(
                    "From Date:",
                    value=datetime.now().date() - timedelta(days=7),
                    key="start_date"
                )
            with col2:
                end_date = st.date_input(
                    "To Date:",
                    value=datetime.now().date(),
                    key="end_date"
                )
            with col3:
                if st.button("Apply Date Range", key="apply_date_range"):
                    if start_date <= end_date:
                        tickets_to_display = filter_tickets_by_date_range(kb_data, start_date, end_date)
                        filter_description = f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                        st.session_state.active_filter = "date_range"
                        st.session_state.filter_description = filter_description
                        st.session_state.tickets_to_display = tickets_to_display
                    else:
                        st.error("Start date must be before or equal to end date!")
            with col4:
                preview_tickets = filter_tickets_by_date_range(kb_data, st.session_state.get('start_date', datetime.now().date()), st.session_state.get('end_date', datetime.now().date()))
                st.metric("Tickets Found", len(preview_tickets))

        with tab3:
            st.markdown("### Select Specific Date")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                specific_date = st.date_input(
                    "Select Date:",
                    value=datetime.now().date(),
                    key="specific_date"
                )
            with col2:
                if st.button("Apply Date Filter", key="apply_specific_date"):
                    tickets_to_display = filter_tickets_by_specific_date(kb_data, specific_date)
                    filter_description = f"📆 {specific_date.strftime('%Y-%m-%d')}"
                    st.session_state.active_filter = "specific_date"
                    st.session_state.filter_description = filter_description
                    st.session_state.tickets_to_display = tickets_to_display
            with col3:
                preview_tickets = filter_tickets_by_specific_date(kb_data, specific_date)
                st.metric("Tickets Found", len(preview_tickets))

        with tab4:
            st.markdown("### Search by Ticket Number or Title")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search_query = st.text_input(
                    "Search Query:",
                    placeholder="e.g., T20250704.0057 or 'network issue'",
                    key="search_query",
                    help="Search by ticket number (e.g., T20250704.0057) or keywords in title"
                )
            with col2:
                if st.button("🔍 Search", key="search_tickets"):
                    if search_query and search_query.strip():
                        tickets_to_display = search_tickets_by_number(kb_data, search_query)
                        filter_description = f"🔍 Search: '{search_query}'"
                        st.session_state.active_filter = "search"
                        st.session_state.filter_description = filter_description
                        st.session_state.tickets_to_display = tickets_to_display
                    else:
                        st.warning("Please enter a search query")
            with col3:
                if search_query and search_query.strip():
                    preview_tickets = search_tickets_by_number(kb_data, search_query)
                    st.metric("Tickets Found", len(preview_tickets))
                else:
                    st.metric("Tickets Found", 0)
        if 'tickets_to_display' in st.session_state and 'filter_description' in st.session_state:
            tickets_to_display = st.session_state.tickets_to_display
            filter_description = st.session_state.filter_description
        else:
            tickets_to_display = filter_tickets_by_duration(kb_data, "Last hour", now)
            filter_description = "🚨 Last hour"

        # Display current filter and refresh option
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Current Filter:** {filter_description}")
        with col2:
            if st.button("🔄 Refresh", key="refresh_tickets"):
                st.rerun()

        # Display filtered tickets
        st.markdown(f"""
        <div class="card">
        <h3>{filter_description}</h3>
        </div>
        """, unsafe_allow_html=True)

        if tickets_to_display:
            # Add special styling for urgent tickets
            if "Last hour" in filter_description:
                st.markdown("""
                <div style="
                    background-color: #2d2d2d;
                    border-left: 6px solid #ffcc00;
                    color: #ffe066;
                    border-radius: 8px;
                    padding: 14px 18px;
                    margin-bottom: 18px;
                    font-size: 1.1em;
                    font-weight: 500;
                    display: flex;
                    align-items: center;
                ">
                    <span style="font-size:1.5em; margin-right: 12px;">⚠️</span>
                    <span>
                        <strong>Urgent Attention Required:</strong>
                        These tickets were raised in the last hour and may need immediate response.
                    </span>
                </div>
                """, unsafe_allow_html=True)

            # Add pagination for large result sets
            tickets_per_page = TICKETS_PER_PAGE
            total_pages = (len(tickets_to_display) + tickets_per_page - 1) // tickets_per_page

            if total_pages > 1:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    page_number = st.selectbox(
                        f"Page (showing {tickets_per_page} tickets per page):",
                        options=list(range(1, total_pages + 1)),
                        key="page_selector"
                    )

                start_idx = (page_number - 1) * tickets_per_page
                end_idx = start_idx + tickets_per_page
                tickets_to_show = tickets_to_display[start_idx:end_idx]
            else:
                tickets_to_show = tickets_to_display

            # Display tickets
            for i, ticket in enumerate(tickets_to_show):
                # Construct created_at from date and time
                created_at = f"{ticket.get('date', '')}T{ticket.get('time', '')}"
                time_elapsed = format_time_elapsed(created_at)
                date_created = format_date_display(created_at)
                # Construct id if missing
                ticket_id = ticket.get('id') or (ticket.get('title', '') + ticket.get('date', '') + ticket.get('time', ''))
                ticket_number = ticket.get('ticket_number', 'N/A')

                # Special highlighting for critical/urgent tickets
                is_urgent = (ticket.get('priority') in ['Critical', 'Desktop/User Down'] or
                           "Last hour" in filter_description)

                expand_key = f"ticket_{ticket_id}_{i}"

                # Display ticket number if available, otherwise use old format
                display_title = f"#{ticket_number}" if ticket_number != 'N/A' else ticket_id

                with st.expander(
                    f"{'🔥' if is_urgent else '📋'} {display_title} - {ticket.get('title', '')} ({time_elapsed})",
                    expanded=False
                ):
                    # Ticket header with date
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**📅 Created:** {date_created}")
                    with col2:
                        st.markdown(f"**⏰ Time Elapsed:** {time_elapsed}")

                    # Ticket details
                    if ticket_number != 'N/A':
                        st.markdown(f"**🎫 Ticket Number:** #{ticket_number}")

                    cols = st.columns([1, 1, 1, 1])
                    cols[0].markdown(f"**Category:** {ticket.get('category', 'General')}")
                    cols[1].markdown(f"**Priority:** {ticket.get('priority', 'Medium')}")
                    cols[2].markdown(f"**Status:** {ticket.get('status', 'Open')}")
                    cols[3].markdown(f"**Requester:** {ticket.get('requester_name', '')}")

                    st.markdown(f"**Email:** {ticket.get('requester_email', '')}")

                    # Assignment information
                    assignment_result = ticket.get('assignment_result', {})
                    if assignment_result and assignment_result.get('assigned_technician'):
                        st.markdown(f"**👨‍💻 Assigned to:** {assignment_result.get('assigned_technician', 'N/A')}")
                        if assignment_result.get('technician_email'):
                            st.markdown(f"**📧 Technician Email:** {assignment_result.get('technician_email', 'N/A')}")
                    if ticket.get('requester_phone'):
                        st.markdown(f"**Phone:** {ticket.get('requester_phone', '')}")
                    st.markdown(f"**Company ID:** {ticket.get('company_id', '')}")

                    # Description with expand/collapse
                    if len(ticket.get('description', '')) > 200:
                        if st.button(f"Show Full Description", key=f"desc_{ticket_id}_{i}"):
                            st.markdown(f"**Description:** {ticket.get('description', '')}")
                        else:
                            st.markdown(f"**Description:** {ticket.get('description', '')[:200]}...")
                    else:
                        st.markdown(f"**Description:** {ticket.get('description', '')}")

                    # Technical details if available
                    if ticket.get('device_model') or ticket.get('os_version') or ticket.get('error_message'):
                        st.markdown("**Technical Details:**")
                        if ticket.get('device_model'):
                            st.markdown(f"• Device: {ticket.get('device_model', '')}")
                        if ticket.get('os_version'):
                            st.markdown(f"• OS: {ticket.get('os_version', '')}")
                        if ticket.get('error_message'):
                            st.markdown(f"• Error: {ticket.get('error_message', '')}")

                    # Status update section
                    st.markdown("---")
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        new_status = st.selectbox(
                            "Update Status:",
                            ["Open", "In Progress", "Resolved", "Closed"],
                            index=["Open", "In Progress", "Resolved", "Closed"].index(ticket.get('status', 'Open')) if ticket.get('status', 'Open') in ["Open", "In Progress", "Resolved", "Closed"] else 0,
                            key=f"status_{ticket_id}_{i}"
                        )
                    with col2:
                        if st.button("Update Status", key=f"update_{ticket_id}_{i}"):
                            data_manager.update_ticket_status(ticket_id, new_status)
                            st.success(f"Status updated to {new_status}")
                            st.rerun()
                    with col3:
                        # Priority indicator
                        priority_colors = {
                            "Low": "🟢",
                            "Medium": "🟡",
                            "High": "🟠",
                            "Critical": "🔴",
                            "Desktop/User Down": "🚨"
                        }
                        st.markdown(f"**Priority:** {priority_colors.get(ticket.get('priority', 'Medium'), '⚪')} {ticket.get('priority', 'Medium')}")

            # Show pagination info
            if total_pages > 1:
                st.info(f"Showing page {page_number} of {total_pages} ({len(tickets_to_display)} total tickets)")

        else:
            st.info(f"No tickets found for the selected filter: {filter_description}")

        # Summary statistics for filtered tickets
        if tickets_to_display:
            st.markdown("---")
            st.markdown("### 📊 Summary Statistics")

            # Calculate stats for the filtered tickets
            status_counts = {}
            priority_counts = {}
            category_counts = {}

            for ticket in tickets_to_display:
                # Status counts
                status = ticket.get('status', 'Open')
                status_counts[status] = status_counts.get(status, 0) + 1

                # Priority counts
                priority = ticket.get('priority', 'Medium')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

                # Category counts
                category = ticket.get('category', 'General')
                category_counts[category] = category_counts.get(category, 0) + 1

            # Main metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total", len(tickets_to_display))
            col2.metric("Open", status_counts.get('Open', 0))
            col3.metric("In Progress", status_counts.get('In Progress', 0))
            col4.metric("Resolved", status_counts.get('Resolved', 0))

            # Detailed breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**📂 Categories:**")
                for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(tickets_to_display)) * 100
                    st.write(f"• {category}: {count} ({percentage:.1f}%)")

            with col2:
                st.markdown("**⚡ Priorities:**")
                priority_order = ["Critical", "Desktop/User Down", "High", "Medium", "Low"]
                for priority in priority_order:
                    if priority in priority_counts:
                        count = priority_counts[priority]
                        percentage = (count / len(tickets_to_display)) * 100
                        icon = PRIORITY_COLORS.get(priority, "⚪")
                        st.write(f"• {icon} {priority}: {count} ({percentage:.1f}%)")

            # Show urgent tickets alert if any
            urgent_count = priority_counts.get('Critical', 0) + priority_counts.get('Desktop/User Down', 0)
            if urgent_count > 0:
                st.warning(f"⚠️ {urgent_count} urgent ticket(s) require immediate attention!")

def dashboard_page(data_manager):
    """Dashboard page with analytics and charts (now uses caching)"""
    st.title("📊 Dashboard")
    kb_data = load_kb_data()
    if not kb_data:
        st.info("No tickets found in the knowledge base.")
        return
    # --- FILTERS ---
    st.markdown("### Filters")
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        date_min = None
        date_max = None
        dates = []
        for entry in kb_data:
            t = entry['new_ticket']
            try:
                dt = datetime.fromisoformat(t.get('date', '') + 'T' + t.get('time', ''))
                dates.append(dt)
            except:
                continue
        if dates:
            date_min = min(dates).date()
            date_max = max(dates).date()
        else:
            date_min = date_max = datetime.now().date()
        date_range = st.date_input("Date Range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
    with col2:
        all_statuses = sorted(set(entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A') for entry in kb_data if 'new_ticket' in entry))
        status_filter = st.multiselect("Status", options=["New", "In Progress", "Resolved", "Closed"] + [s for s in all_statuses if s not in ["New", "In Progress", "Resolved", "Closed"]], default=["New", "In Progress", "Resolved", "Closed"])
    with col3:
        all_priorities = sorted(set(entry['new_ticket'].get('classified_data', {}).get('PRIORITY', {}).get('Label', 'N/A') for entry in kb_data if 'new_ticket' in entry))
        priority_filter = st.multiselect("Priority", options=all_priorities, default=all_priorities)
    # --- FILTER DATA ---
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        c = t.get('classified_data', {})
        try:
            dt = datetime.fromisoformat(t.get('date', '') + 'T' + t.get('time', ''))
        except:
            continue
        status = c.get('STATUS', {}).get('Label', 'N/A')
        priority = c.get('PRIORITY', {}).get('Label', 'N/A')
        if (date_range[0] <= dt.date() <= date_range[1]) and (status in status_filter) and (priority in priority_filter):
            filtered.append(entry)
    total_tickets = len(filtered)
    open_tickets = sum(1 for entry in filtered if entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A').lower() == 'open')
    resolved_tickets = sum(1 for entry in filtered if entry['new_ticket'].get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A').lower() == 'resolved')
    last_24h = 0
    now = datetime.now()
    cutoff_24h = now - timedelta(hours=24)
    for entry in filtered:
        try:
            created_time = datetime.fromisoformat(entry['new_ticket'].get('date', '') + 'T' + entry['new_ticket'].get('time', ''))
            if created_time >= cutoff_24h:
                last_24h += 1
        except:
            continue
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total_tickets)
    col2.metric("Last 24 Hours", last_24h)
    col3.metric("Open Tickets", open_tickets)
    col4.metric("Resolved", resolved_tickets)
    # --- Prepare data for grouped bar chart ---
    status_counts = Counter()
    priority_counts = Counter()
    category_counts = Counter()
    for entry in filtered:
        classified = entry['new_ticket'].get('classified_data', {})
        status = classified.get('STATUS', {}).get('Label', 'N/A')
        priority = classified.get('PRIORITY', {}).get('Label', 'N/A')
        category = classified.get('TICKETCATEGORY', {}).get('Label', 'N/A')
        status_counts[status] += 1
        priority_counts[priority] += 1
        category_counts[category] += 1
    # Ensure all main statuses are present in order
    status_order = ["New", "In Progress", "Resolved", "Closed"]
    for s in status_order:
        if s not in status_counts:
            status_counts[s] = 0
    # --- Plotly Bar Chart ---
    df_status = pd.DataFrame({"Status": list(status_counts.keys()), "Count": list(status_counts.values())})
    df_priority = pd.DataFrame({"Priority": list(priority_counts.keys()), "Count": list(priority_counts.values())})
    df_category = pd.DataFrame({"Category": list(category_counts.keys()), "Count": list(category_counts.values())})
    # Custom color maps
    status_colors = STATUS_COLORS
    priority_colors = CHART_PRIORITY_COLORS
    category_colors = {cat: px.colors.qualitative.Plotly[i % 10] for i, cat in enumerate(df_category['Category'])}
    # Plot
    st.subheader("Tickets by Status, Priority, and Category")
    fig = px.bar(df_status, x="Status", y="Count", color="Status", category_orders={"Status": status_order}, color_discrete_map=status_colors, barmode="group", title="Status")
    fig.add_bar(x=df_priority['Priority'], y=df_priority['Count'], name="Priority", marker_color=[priority_colors.get(p, '#888') for p in df_priority['Priority']])
    fig.add_bar(x=df_category['Category'], y=df_category['Count'], name="Category", marker_color=[category_colors.get(c, '#888') for c in df_category['Category']])
    fig.update_layout(
        plot_bgcolor="#181818",
        paper_bgcolor="#181818",
        font_color="#f8f9fa",
        legend=dict(bgcolor="#23272f", bordercolor="#444", borderwidth=1),
        xaxis=dict(title="", tickfont=dict(color="#f8f9fa")),
        yaxis=dict(title="", tickfont=dict(color="#f8f9fa")),
        barmode="group",
        bargap=0.18,
        bargroupgap=0.12
    )
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Recent Tickets")
    if filtered:
        recent_rows = []
        for entry in filtered[-10:][::-1]:
            ticket = entry['new_ticket']
            classified = ticket.get('classified_data', {})
            recent_rows.append({
                "Title": ticket.get('title', 'N/A'),
                "Category": classified.get('TICKETCATEGORY', {}).get('Label', 'N/A'),
                "Priority": classified.get('PRIORITY', {}).get('Label', 'N/A'),
                "Status": classified.get('STATUS', {}).get('Label', 'N/A'),
                "Date": ticket.get('date', 'N/A'),
                "Time": ticket.get('time', 'N/A'),
                "ID": ticket.get('title', 'N/A') + ticket.get('date', 'N/A') + ticket.get('time', 'N/A')
            })
        df_recent = pd.DataFrame(recent_rows)
        for entry in filtered[-10:][::-1]:
            ticket = entry['new_ticket']
            classified = ticket.get('classified_data', {})
            ticket_id = ticket.get('title', 'N/A') + ticket.get('date', 'N/A') + ticket.get('time', 'N/A')
            with st.expander(f"{ticket.get('title', 'N/A')} ({ticket.get('date', 'N/A')} {ticket.get('time', 'N/A')})", expanded=False):
                st.markdown(f"**Category:** {classified.get('TICKETCATEGORY', {}).get('Label', 'N/A')}")
                st.markdown(f"**Priority:** {classified.get('PRIORITY', {}).get('Label', 'N/A')}")
                st.markdown(f"**Status:** {classified.get('STATUS', {}).get('Label', 'N/A')}")
                st.markdown(f"**Requester:** {ticket.get('name', 'N/A')}")
                st.markdown(f"**Created At:** {ticket.get('date', 'N/A')} {ticket.get('time', 'N/A')}")

                # Assignment information
                assignment_result = ticket.get('assignment_result', {})
                if assignment_result and assignment_result.get('assigned_technician'):
                    st.markdown(f"**👨‍💻 Assigned to:** {assignment_result.get('assigned_technician', 'N/A')}")
                    if assignment_result.get('technician_email'):
                        st.markdown(f"**📧 Technician Email:** {assignment_result.get('technician_email', 'N/A')}")

                st.markdown(f"**Description:** {ticket.get('description', 'N/A')}")
    else:
        st.info("No tickets found for the selected filters.")

def resolutions_page():
    """Page for technicians to view tickets and their resolutions."""
    st.title("📝 Ticket Resolutions")
    kb_data = load_kb_data()
    search_query = st.text_input("Search by title, description, or resolution:", "")
    # Filter tickets by search
    filtered = []
    for entry in kb_data:
        t = entry['new_ticket']
        res_note = t.get('resolution_note', '')
        if search_query.strip():
            q = search_query.lower()
            if (q in t.get('title', '').lower() or
                q in t.get('description', '').lower() or
                q in res_note.lower()):
                filtered.append(t)
        else:
            filtered.append(t)
    # Sort by most recent
    filtered = sorted(filtered, key=lambda x: x.get('date', '') + x.get('time', ''), reverse=True)
    st.markdown(f"Showing {len(filtered)} tickets.")
    for i, t in enumerate(filtered):
        with st.expander(f"{t.get('title', 'N/A')} ({t.get('date', 'N/A')} {t.get('time', 'N/A')})", expanded=False):
            st.markdown(f"**Status:** {t.get('classified_data', {}).get('STATUS', {}).get('Label', 'N/A')}")
            st.markdown(f"**Priority:** {t.get('classified_data', {}).get('PRIORITY', {}).get('Label', 'N/A')}")
            st.markdown(f"**Requester:** {t.get('name', 'N/A')}")
            st.markdown(f"**Due Date:** {t.get('due_date', 'N/A')}")
            st.markdown(f"**Description:** {t.get('description', 'N/A')}")
            st.markdown("---")
            st.markdown("**Resolution Note:**")
            st.code(t.get('resolution_note', 'No resolution note generated'), language=None)

def create_user_sidebar(data_manager):
    """Create sidebar for regular users."""
    with st.sidebar:
        # User info and logout
        user_info = st.session_state.get('user', {})
        st.markdown(f"### Welcome, {user_info.get('name', 'User')}!")
        st.caption(f"User ID: {user_info.get('id', 'N/A')}")

        if st.button("🚪 Logout", key="user_logout"):
            for key in ['user', 'technician', 'role', 'page']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        st.markdown("---")
        st.markdown("## Navigation")

        # User Dashboard navigation
        user_pages = {
            "🏠 Home": "main",
            "📋 My Tickets": "user_my_tickets",
            "📊 Ticket Status": "user_ticket_status",
            "❓ Help": "user_help"
        }

        current_page = st.session_state.get('page', 'main')

        for label, page_key in user_pages.items():
            if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                st.session_state.page = page_key
                st.rerun()

        st.markdown(f"""
        <div style="margin: 20px 0; padding: 10px; background-color: var(--accent); border-radius: 6px;">
        <small>Current page:</small><br>
        <strong>{current_page.replace('_', ' ').title()}</strong>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Quick Stats")
        try:
            if os.path.exists('Knowledgebase.json'):
                with open('Knowledgebase.json', 'r') as f:
                    kb_data = json.load(f)
                total_tickets = len(kb_data)
            else:
                total_tickets = 0
        except:
            total_tickets = 0
        st.metric("Total Tickets", total_tickets)

        st.markdown("---")
        st.markdown("""
        <div style="padding: 10px;">
        <h4>Need Help?</h4>
        <p>Contact IT Support:</p>
        <p>📞 9723100860<br>
        ✉️ inquire@64-squares.com</p>
        </div>
        """, unsafe_allow_html=True)

def create_technician_sidebar(data_manager):
    """Create sidebar for technicians."""
    with st.sidebar:
        # Technician info and logout
        tech_info = st.session_state.get('technician', {})
        st.markdown(f"### Welcome, {tech_info.get('name', 'Technician')}!")
        st.caption(f"Tech ID: {tech_info.get('id', 'N/A')}")

        if st.button("🚪 Logout", key="tech_logout"):
            for key in ['user', 'technician', 'role', 'page']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        st.markdown("---")
        st.markdown("## Navigation")

        # Technician Dashboard navigation
        technician_pages = {
            "🔧 Dashboard": "technician_dashboard",
            "📋 My Tickets": "technician_my_tickets",
            "🚨 Urgent Tickets": "technician_urgent_tickets",
            "📊 Analytics": "technician_analytics",
            "📋 All Tickets": "technician_all_tickets"
        }

        current_page = st.session_state.get('page', 'technician_dashboard')

        for label, page_key in technician_pages.items():
            if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                st.session_state.page = page_key
                st.rerun()

        st.markdown(f"""
        <div style="margin: 20px 0; padding: 10px; background-color: var(--accent); border-radius: 6px;">
        <small>Current page:</small><br>
        <strong>{current_page.replace('_', ' ').title()}</strong>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### Quick Actions")
        if st.button("🔄 Refresh Data", key="tech_refresh"):
            st.rerun()

        st.markdown("---")
        st.markdown("### Today's Performance")
        # Get technician's tickets for metrics
        try:
            if os.path.exists('Knowledgebase.json'):
                with open('Knowledgebase.json', 'r') as f:
                    kb_data = json.load(f)
                tech_email = f"{tech_info.get('name', '').lower()}@company.com"  # Placeholder
                my_tickets = [entry['new_ticket'] for entry in kb_data
                            if entry['new_ticket'].get('assignment_result', {}).get('technician_email') == tech_email]
                assigned_count = sum(1 for t in my_tickets if t.get('status', '').lower() in ['assigned', 'open'])
                completed_count = sum(1 for t in my_tickets if t.get('status', '').lower() in ['resolved', 'closed'])
                in_progress_count = sum(1 for t in my_tickets if t.get('status', '').lower() == 'in progress')
                completion_rate = int((completed_count / len(my_tickets)) * 100) if my_tickets else 0
            else:
                assigned_count = completed_count = in_progress_count = completion_rate = 0
        except:
            assigned_count = completed_count = in_progress_count = completion_rate = 0

        st.metric("Assigned", assigned_count)
        st.metric("In Progress", in_progress_count)
        st.metric("Completed", completed_count)
        st.metric("Completion Rate", f"{completion_rate}%")

@st.cache_resource
def get_snowflake_conn():
    conn = SnowflakeConnection(
        sf_account=SF_ACCOUNT,
        sf_user=SF_USER,
        sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE,
        sf_schema=SF_SCHEMA,
        sf_role=SF_ROLE
    )
    return conn

def show_sso_reconnection_sidebar(snowflake_conn):
    """Show SSO reconnection options in sidebar if connection failed."""
    if not snowflake_conn or not snowflake_conn.is_connected():
        with st.sidebar:
            st.error("🔐 Snowflake Connection Issue")
            st.write("**Common causes:**")
            st.write("• SSO session expired")
            st.write("• Network connectivity")
            st.write("• Invalid credentials")

            with st.expander("🔄 Reconnect with SSO"):
                st.write("Click the button below to reconnect using SSO authentication.")
                if st.button("Reconnect with SSO"):
                    with st.spinner("Reconnecting..."):
                        if snowflake_conn.reconnect():
                            st.success("✅ Reconnected successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Reconnection failed. Please check your SSO access and try again.")

# --- Main App Logic ---
def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title=PAGE_TITLE,
        layout=LAYOUT,
        page_icon=PAGE_ICON,
        initial_sidebar_state="expanded"
    )

    # Apply custom CSS
    apply_custom_css()

    # Check authentication status
    if 'user' not in st.session_state and 'technician' not in st.session_state:
        # Show login page if not authenticated
        login_page()
        return

    # Initialize data manager
    data_manager = DataManager(DATA_REF_FILE, KNOWLEDGEBASE_FILE)

    # Use singleton Snowflake connection
    snowflake_conn = get_snowflake_conn()

    # Show SSO reconnection sidebar if needed
    show_sso_reconnection_sidebar(snowflake_conn)

    # Check connection health
    if snowflake_conn and snowflake_conn.is_connected():
        try:
            snowflake_conn.conn.cursor().execute("SELECT 1")
        except Exception as e:
            st.warning(f"Snowflake keep-alive failed: {e}")

    # Initialize agent
    agent = get_agent(SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE, DATA_REF_FILE, _db_connection=snowflake_conn)

    # Initialize DB (for TicketDB)
    ticket_db = TicketDB(conn=snowflake_conn)

    # Determine user role and show appropriate interface
    user_role = st.session_state.get('role', None)

    if user_role == 'user':
        # User Dashboard Interface
        show_user_dashboard(agent, data_manager, ticket_db)
    elif user_role == 'technician':
        # Technician Dashboard Interface
        show_technician_dashboard(agent, data_manager, ticket_db)
    else:
        st.error("Invalid user role. Please log in again.")
        if st.button("Logout"):
            for key in ['user', 'technician', 'role']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def show_user_dashboard(agent, data_manager, ticket_db):
    """Show user dashboard using modular PageControllers."""
    PageControllers.show_user_dashboard(agent, data_manager, ticket_db)

def show_technician_dashboard(agent, data_manager, ticket_db):
    """Show technician dashboard using modular PageControllers."""
    PageControllers.show_technician_dashboard(agent, data_manager, ticket_db)

def technician_dashboard_all_tickets_page(ticket_db):
    """Show all tickets from the database for the technician dashboard (admin/global view)."""
    st.title("Technician Dashboard - All Tickets")
    all_tickets = []
    try:
        # Try to fetch all tickets from the database using the existing connection
        query = 'SELECT * FROM TEST_DB.PUBLIC.TICKETS'
        all_tickets = ticket_db.conn.execute_query(query)
    except Exception as e:
        st.error(f"Error fetching tickets: {e}")

    if all_tickets:
        for t in all_tickets:
            with st.expander(f"{t['TICKETNUMBER']} - {t['TITLE']}"):
                st.write(f"Description: {t['DESCRIPTION']}")
                st.write(f"Type: {t['TICKETTYPE']}")
                st.write(f"Category: {t['TICKETCATEGORY']}")
                st.write(f"Issue Type: {t['ISSUETYPE']}")
                st.write(f"Sub-Issue Type: {t['SUBISSUETYPE']}")
                st.write(f"Due: {t['DUEDATETIME']}")
                st.write(f"Status: {t.get('STATUS', 'Open')}")
                st.write(f"Assigned Technician: {t.get('TECHNICIANEMAIL', 'Unassigned')}")
                # Status update
                new_status = st.selectbox("Update Status", ["Assigned", "In Progress", "Resolved", "Closed"], key=f"status_{t['TICKETNUMBER']}")
                if st.button("Update Status", key=f"update_{t['TICKETNUMBER']}"):
                    ticket_db.update_ticket_status(t['TICKETNUMBER'], new_status)
                    st.success(f"Status updated to {new_status}")
                    st.rerun()
                # Add note
                note = st.text_area("Add Work Note", key=f"note_{t['TICKETNUMBER']}")
                if st.button("Save Note", key=f"save_note_{t['TICKETNUMBER']}"):
                    ticket_db.add_work_note(t['TICKETNUMBER'], note)
                    st.success("Note added.")
                    st.rerun()
    else:
        st.info("No tickets found.")

if __name__ == "__main__":
    main()