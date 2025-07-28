"""
Configuration module for TeamLogic-AutoTask application.
Contains all configuration constants and settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Snowflake Database Configuration (loaded from .env)
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
SNOWFLAKE_AUTHENTICATOR = os.getenv('SNOWFLAKE_AUTHENTICATOR')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')
SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE')
SNOWFLAKE_ROLE = os.getenv('SNOWFLAKE_ROLE')


# File Paths
DATA_REF_FILE = 'data/reference_data.txt'
KNOWLEDGEBASE_FILE = 'data/knowledgebase.json'

# Application Configuration
APP_TITLE = "TeamLogic-AutoTask"

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




# Email Configuration (loaded from .env)
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT', 'rohankul2017@gmail.com')
EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD')
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
EMAIL_FOLDER = os.getenv('EMAIL_FOLDER', 'inbox')

# Contact Information (loaded from .env)
SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '9723100860')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'rohankul2017@gmail.com')