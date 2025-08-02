"""
Configuration file for TeamLogic AutoTask System
Contains database and service configuration settings
"""

import os

# Snowflake Database Configuration
SF_ACCOUNT = "FOQUKCW-AITEAM_64SQUARES"
SF_USER = "anant.lad@64-squares.com"
SF_PASSWORD = ""  # Using SSO authentication
SF_AUTHENTICATOR = "externalbrowser"  # SSO authentication
SF_DATABASE = "TEST_DB"
SF_SCHEMA = "PUBLIC"
SF_WAREHOUSE = "S_WHH"
SF_ROLE = "ACCOUNTADMIN"

# Email Configuration
SUPPORT_EMAIL = "rohankool2021@gmail.com"
SUPPORT_EMAIL_PASSWORD = os.getenv('SUPPORT_EMAIL_PASSWORD', '')

# SMTP Configuration for notifications
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = SUPPORT_EMAIL
SMTP_PASSWORD = SUPPORT_EMAIL_PASSWORD

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8001

# Webhook URLs
GMAIL_WEBHOOK_URL = f"http://localhost:{API_PORT}/webhooks/gmail/simple"

# File paths
DATA_DIR = "data"
LOGS_DIR = "logs"
CREDENTIALS_DIR = "credentials"

# Data file paths (for backward compatibility)
DATA_REF_FILE = "data/reference_data.txt"
KNOWLEDGEBASE_FILE_PATH = "data/knowledgebase.json"

# LLM Configuration (optional)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# Application Settings
DEBUG = True
LOG_LEVEL = "INFO"

# Ticket Configuration
TICKET_SEQUENCE_FILE = os.path.join(DATA_DIR, "ticket_sequence.json")
REFERENCE_DATA_FILE = os.path.join(DATA_DIR, "reference_data.txt")
KNOWLEDGEBASE_FILE = os.path.join(DATA_DIR, "knowledgebase.json")
