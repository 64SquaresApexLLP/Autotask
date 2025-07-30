"""
Configuration module for TeamLogic-AutoTask application.
Contains all configuration constants and settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Snowflake Connection Configuration (loaded from .env)
# Using SSO authentication with externalbrowser
SF_ACCOUNT = os.getenv('SF_ACCOUNT', 'your_snowflake_account')
SF_USER = os.getenv('SF_USER', 'your_snowflake_user')
SF_WAREHOUSE = os.getenv('SF_WAREHOUSE', 'your_warehouse')
SF_DATABASE = os.getenv('SF_DATABASE', 'your_database')
SF_SCHEMA = os.getenv('SF_SCHEMA', 'your_schema')
SF_ROLE = os.getenv('SF_ROLE', 'your_role')


# File Paths
DATA_REF_FILE = 'data/reference_data.txt'
KNOWLEDGEBASE_FILE = 'data/knowledgebase.json'

# UI Configuration
PAGE_TITLE = "TeamLogic-AutoTask"
PAGE_ICON = "🎫"
LAYOUT = "wide"

# Pagination Settings
TICKETS_PER_PAGE = 10

# LLM Model Configuration
DEFAULT_EXTRACT_MODEL = 'llama3-8b'
DEFAULT_CLASSIFY_MODEL = 'mixtral-8x7b'

# Priority Options
PRIORITY_OPTIONS = ["Low", "Medium", "High", "Critical", "Desktop/User Down"]

# Status Options
STATUS_OPTIONS = ["Open", "In Progress", "Resolved", "Closed"]

# Duration Filter Options
DURATION_OPTIONS = [
    "Last hour",
    "Last 2 hours",
    "Last 6 hours",
    "Last 12 hours",
    "Today",
    "Yesterday",
    "Last 3 days",
    "Last week",
    "Last month",
    "All tickets"
]

# Priority Colors for UI
PRIORITY_COLORS = {
    "Low": "🟢",
    "Medium": "🟡",
    "High": "🟠",
    "Critical": "🔴",
    "Desktop/User Down": "🚨"
}

# Duration Icons
DURATION_ICONS = {
    "Last hour": "🚨",
    "Last 2 hours": "⏰",
    "Last 6 hours": "🕕",
    "Last 12 hours": "🕐",
    "Today": "📅",
    "Yesterday": "📆",
    "Last 3 days": "📊",
    "Last week": "📈",
    "Last month": "📉",
    "All tickets": "📋"
}

# Chart Colors
STATUS_COLORS = {
    "New": "#4e73df",
    "In Progress": "#f6c23e",
    "Resolved": "#36b9cc",
    "Closed": "#e74a3b"
}

CHART_PRIORITY_COLORS = {
    "Low": "#1cc88a",
    "Medium": "#36b9cc",
    "High": "#f6c23e",
    "Critical": "#e74a3b",
    "Desktop/User Down": "#6f42c1"
}

# Email Configuration (loaded from .env)
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT', 'rohankul2017@gmail.com')
EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD')
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
EMAIL_FOLDER = os.getenv('EMAIL_FOLDER', 'inbox')

# Contact Information (loaded from .env)
SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '9723100860')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'rohankul2017@gmail.com')

# Notification Configuration
MANAGER_EMAIL = os.getenv('MANAGER_EMAIL', 'itmanager@company.com')
FALLBACK_TECHNICIAN_EMAIL = os.getenv('FALLBACK_TECHNICIAN_EMAIL', 'support@company.com')

# Email Notification Types
EMAIL_NOTIFICATION_TYPES = [
    'confirmation',      # Customer ticket confirmation
    'assignment',        # Technician assignment notification
    'status_update',     # Status change notifications
    'escalation',        # Escalation notifications
    'resolution',        # Resolution notifications
    'reminder',          # Reminder notifications
    'feedback_request'   # Feedback request notifications
]

# Email Recipient Types
EMAIL_RECIPIENT_TYPES = [
    'customer',          # End user who submitted ticket
    'technician',        # Assigned technician
    'manager',           # IT manager or supervisor
    'team'               # Team notifications
]

# Notification Triggers
HIGH_PRIORITY_NOTIFICATIONS = ['Critical', 'High', 'Desktop/User Down']
ESCALATION_KEYWORDS = ['fallback', 'failed', 'error', 'escalated']