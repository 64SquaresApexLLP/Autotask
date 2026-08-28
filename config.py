"""
Configuration file for TeamLogic AutoTask System
Contains database and service configuration settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env and .env.local files
_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, '.env.local'))
load_dotenv(os.path.join(_base_dir, '.env'))
load_dotenv()

# Snowflake Database Configuration (loaded from .env or .env.local)
SF_ACCOUNT = os.getenv('SF_ACCOUNT', os.getenv('SNOWFLAKE_ACCOUNT', 'FXJQRBY-GF76563'))
SF_USER = os.getenv('SF_USER', os.getenv('SNOWFLAKE_USER', 'RUCHIR'))
SF_PASSWORD = os.getenv('SF_PASSWORD', os.getenv('SNOWFLAKE_PASSWORD', ''))
SF_AUTHENTICATOR = os.getenv('SF_AUTHENTICATOR', os.getenv('SNOWFLAKE_AUTHENTICATOR', 'externalbrowser'))
SF_DATABASE = os.getenv('SF_DATABASE', os.getenv('SNOWFLAKE_DATABASE', 'TEST_DB'))
SF_SCHEMA = os.getenv('SF_SCHEMA', os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'))
SF_WAREHOUSE = os.getenv('SF_WAREHOUSE', os.getenv('SNOWFLAKE_WAREHOUSE', 'S_WHH'))
SF_ROLE = os.getenv('SF_ROLE', os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'))
SF_PASSCODE = os.getenv('SF_PASSCODE', os.getenv('SNOWFLAKE_PASSCODE', ''))

# Email Configuration (loaded from .env)
GMAIL_USER = os.getenv('GMAIL_USER', 'venkatehp12@gmail.com')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', os.getenv('SUPPORT_EMAIL_PASSWORD', 'xuzzbgdwqwzrklrj'))
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', GMAIL_USER)
SUPPORT_EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD', GMAIL_APP_PASSWORD)
if not SUPPORT_EMAIL_PASSWORD:
    _pwd_path = os.path.join(_base_dir, '.gmail_app_password')
    if os.path.exists(_pwd_path):
        try:
            with open(_pwd_path, 'r') as _f:
                SUPPORT_EMAIL_PASSWORD = _f.read().strip()
        except Exception:
            pass

# Manager and escalation email configuration
MANAGER_EMAIL = os.getenv('MANAGER_EMAIL', 'anantlad66@gmail.com')
FALLBACK_TECHNICIAN_EMAIL = os.getenv('FALLBACK_TECHNICIAN_EMAIL', 'support@company.com')
SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '9723100860')

# Priority and escalation configuration
HIGH_PRIORITY_NOTIFICATIONS = ['Critical', 'High', 'Desktop/User Down']
ESCALATION_KEYWORDS = ['fallback', 'failed', 'error', 'escalated', 'due date exceeded']

# SMTP Configuration for notifications (loaded from .env)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = SUPPORT_EMAIL
SMTP_PASSWORD = SUPPORT_EMAIL_PASSWORD

# API Configuration (loaded from .env)
API_HOST = os.getenv('APP_HOST', '0.0.0.0')
API_PORT = int(os.getenv('APP_PORT', '8001'))

# Webhook URLs
GMAIL_WEBHOOK_URL = f"http://localhost:{API_PORT}/webhooks/gmail/simple"

# File paths
DATA_DIR = "data"
LOGS_DIR = "logs"
CREDENTIALS_DIR = "credentials"

# Data file paths (for backward compatibility)
DATA_REF_FILE = "data/reference_data.txt"
KNOWLEDGEBASE_FILE_PATH = "data/knowledgebase.json"

# LLM Configuration (loaded from .env)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# Application Settings (loaded from .env)
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Ticket Configuration
TICKET_SEQUENCE_FILE = os.path.join(DATA_DIR, "ticket_sequence.json")
REFERENCE_DATA_FILE = os.path.join(DATA_DIR, "reference_data.txt")
KNOWLEDGEBASE_FILE = os.path.join(DATA_DIR, "knowledgebase.json")
