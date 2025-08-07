#!/usr/bin/env python3
"""
Debug script to check email notification configuration
"""

import os
import sys
sys.path.append('.')

print('=== DEBUGGING EMAIL NOTIFICATION ISSUE ===')
print()

# Check environment variables
print('Environment Variables:')
print(f'SMTP_USERNAME: {os.getenv("SMTP_USERNAME", "Not set")}')
print(f'SMTP_PASSWORD: {os.getenv("SMTP_PASSWORD", "Not set")}')
print(f'SUPPORT_EMAIL: {os.getenv("SUPPORT_EMAIL", "Not set")}')
print(f'SUPPORT_EMAIL_PASSWORD: {os.getenv("SUPPORT_EMAIL_PASSWORD", "Not set")}')
print()

# Check if Gmail app password file exists and is readable
app_password_file = '.gmail_app_password'
print(f'Gmail App Password File: {app_password_file}')
print(f'File exists: {os.path.exists(app_password_file)}')
if os.path.exists(app_password_file):
    with open(app_password_file, 'r') as f:
        password = f.read().strip()
        print(f'Password length: {len(password)} characters')
        print(f'Password starts with: {password[:4]}...')
print()

# Test NotificationAgent initialization
try:
    from src.agents.notification_agent import NotificationAgent
    agent = NotificationAgent()
    print('NotificationAgent Configuration:')
    print(f'SMTP Server: {agent.smtp_server}:{agent.smtp_port}')
    print(f'SMTP Username: {agent.smtp_username}')
    print(f'SMTP Password loaded: {"Yes" if agent.smtp_password else "No"}')
    if agent.smtp_password:
        print(f'Password length: {len(agent.smtp_password)} characters')
        print(f'Password starts with: {agent.smtp_password[:4]}...')
    print(f'From Email: {agent.from_email}')
    print(f'Enabled: {agent.enabled}')
    print()
    
    # Test SMTP connection
    if agent.enabled:
        print('Testing SMTP connection...')
        import smtplib
        try:
            with smtplib.SMTP(agent.smtp_server, agent.smtp_port) as server:
                server.starttls()
                server.login(agent.smtp_username, agent.smtp_password)
                print('✅ SMTP connection successful!')
        except Exception as e:
            print(f'❌ SMTP connection failed: {e}')
    else:
        print('❌ Email notifications disabled - no password loaded')
        
except Exception as e:
    print(f'Error initializing NotificationAgent: {e}')
    import traceback
    traceback.print_exc()