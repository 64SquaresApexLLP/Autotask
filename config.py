"""
Configuration file for TeamLogic AutoTask System
Contains database and service configuration settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Snowflake Database Configuration (loaded from .env)
SF_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT', 'FOQUKCW-AITEAM_64SQUARES')
SF_USER = os.getenv('SNOWFLAKE_USER', 'anant.lad@64-squares.com')
SF_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD', '')  # Using SSO authentication
SF_AUTHENTICATOR = os.getenv('SNOWFLAKE_AUTHENTICATOR', 'externalbrowser')  # SSO authentication
SF_DATABASE = os.getenv('SNOWFLAKE_DATABASE', 'TEST_DB')
SF_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')
SF_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE', 'S_WHH')
SF_ROLE = os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')

# Email Configuration (loaded from .env)
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'rohankool2021@gmail.com')
SUPPORT_EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD', '')

# Manager and escalation email configuration
MANAGER_EMAIL = os.getenv('MANAGER_EMAIL', 'anantlad66@gmail.com')
FALLBACK_TECHNICIAN_EMAIL = os.getenv('FALLBACK_TECHNICIAN_EMAIL', 'support@company.com')
SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '1-800-SUPPORT')

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
