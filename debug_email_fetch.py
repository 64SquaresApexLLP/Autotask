#!/usr/bin/env python3
"""
Debug script to investigate why email wasn't fetched.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.agents.intake_agent import IntakeClassificationAgent
from src.database.snowflake_db import SnowflakeConnection
import config
from datetime import datetime, timedelta
import pytz

def debug_email_fetch():
    """Debug why email wasn't fetched"""
    print("🔍 Debugging email fetch issues...")
    
    try:
        # Initialize database connection
        db_connection = SnowflakeConnection(
            sf_account=config.SF_ACCOUNT, sf_user=config.SF_USER, sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE, sf_schema=config.SF_SCHEMA, sf_role=config.SF_ROLE
        )
        print("✅ Database connection successful")
        
        # Initialize agent with email credentials
        print("🔄 Initializing IntakeClassificationAgent...")
        agent = IntakeClassificationAgent(
            sf_account=config.SF_ACCOUNT, sf_user=config.SF_USER, sf_warehouse=config.SF_WAREHOUSE,
            sf_database=config.SF_DATABASE, sf_schema=config.SF_SCHEMA, sf_role=config.SF_ROLE,
            data_ref_file='data/reference_data.txt', db_connection=db_connection,
            email_account='rohankul2017@gmail.com', email_password=os.getenv('SUPPORT_EMAIL_PASSWORD'),
            imap_server='imap.gmail.com'
        )
        print("✅ Agent initialized")
        
        # Check email processing status
        status = agent.get_email_processing_status()
        print(f"📧 Email processing status: {status}")
        
        # Test email connection
        print("\n🔍 Testing email connection...")
        mail = agent.connect_email()
        if mail:
            print("✅ Email connection successful")
            
            # Check recent emails manually
            print("\n📧 Checking recent emails manually...")
            cutoff_time = datetime.now() - timedelta(minutes=10)  # Check last 10 minutes
            cutoff_date = cutoff_time.strftime("%d-%b-%Y")
            print(f"🔍 Looking for emails since: {cutoff_date}")
            
            status, messages = mail.search(None, f'(SINCE {cutoff_date})')
            email_ids = messages[0].split()
            
            print(f"📧 Found {len(email_ids)} emails since {cutoff_date}")
            
            if email_ids:
                print("\n📋 Recent emails found:")
                for i, email_id in enumerate(reversed(email_ids[-5:])):  # Show last 5 emails
                    try:
                        status, msg_data = mail.fetch(email_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                import email
                                msg = email.message_from_bytes(response_part[1])
                                
                                subject, encoding = email.header.decode_header(msg.get("Subject"))[0]
                                subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject or ""
                                from_ = msg.get("From") or ""
                                date = msg.get("Date") or ""
                                
                                print(f"  📧 Email {i+1}:")
                                print(f"     Subject: {subject}")
                                print(f"     From: {from_}")
                                print(f"     Date: {date}")
                                
                                # Check if it would be processed as ticket
                                should_process = agent.should_process_as_ticket(msg)
                                print(f"     Would process as ticket: {'✅ YES' if should_process else '❌ NO'}")
                                
                                if should_process:
                                    # Try to process it
                                    print("     🔄 Attempting to process...")
                                    ticket_result = agent.process_email_with_images(msg)
                                    if ticket_result:
                                        print(f"     ✅ Successfully processed! Ticket: {ticket_result.get('ticket_number', 'Unknown')}")
                                    else:
                                        print("     ❌ Failed to process")
                                
                                print()
                                
                    except Exception as e:
                        print(f"  ❌ Error processing email {email_id}: {e}")
                        continue
            else:
                print("📭 No emails found in the specified time range")
            
            mail.logout()
        else:
            print("❌ Email connection failed")
        
        # Test the automatic processing job
        print("\n🔄 Testing automatic email processing job...")
        agent.automatic_email_processing_job()
        
        # Check final status
        final_status = agent.get_email_processing_status()
        print(f"\n📊 Final email processing status: {final_status}")
        
        print("\n🎯 Debug Summary:")
        print("1. Check if email password is configured correctly")
        print("2. Verify email was sent to the correct address (rohankul2017@gmail.com)")
        print("3. Check if email subject/content matches support ticket patterns")
        print("4. Verify email was sent within the last 5 minutes")
        print("5. Check if automatic processing is running")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_email_fetch() 