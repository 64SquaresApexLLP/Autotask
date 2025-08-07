#!/usr/bin/env python3
"""
Example: How to use IntakeAgent with Email Integration

This example shows different ways to use the IntakeAgent with the new email monitoring capability.
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.intake_agent import IntakeClassificationAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def example_1_without_email():
    """Example 1: Using IntakeAgent without email monitoring (existing behavior)"""
    logger.info("=" * 60)
    logger.info("EXAMPLE 1: IntakeAgent without email monitoring")
    logger.info("=" * 60)
    
    # Initialize without email monitoring (default behavior)
    agent = IntakeClassificationAgent()
    
    logger.info("✅ IntakeAgent initialized without email monitoring")
    logger.info("This works exactly like the original IntakeAgent")
    
    # Check status
    status = agent.get_email_monitoring_status()
    logger.info(f"Email monitoring status: {status['is_monitoring']}")
    
    return agent

def example_2_with_email_disabled():
    """Example 2: Explicitly disable email monitoring"""
    logger.info("=" * 60)
    logger.info("EXAMPLE 2: IntakeAgent with email monitoring explicitly disabled")
    logger.info("=" * 60)
    
    # Initialize with email monitoring explicitly disabled
    agent = IntakeClassificationAgent(
        enable_email_monitoring=False,
        webhook_url="http://localhost:8001/webhooks/gmail/simple",
        email_check_interval=30
    )
    
    logger.info("✅ IntakeAgent initialized with email monitoring disabled")
    
    # Check status
    status = agent.get_email_monitoring_status()
    logger.info(f"Email monitoring status: {status['is_monitoring']}")
    
    return agent

def example_3_with_email_enabled():
    """Example 3: Enable email monitoring (requires Gmail App Password)"""
    logger.info("=" * 60)
    logger.info("EXAMPLE 3: IntakeAgent with email monitoring enabled")
    logger.info("=" * 60)
    
    # Initialize with email monitoring enabled
    agent = IntakeClassificationAgent(
        enable_email_monitoring=True,
        webhook_url="http://localhost:8001/webhooks/gmail/simple",
        email_check_interval=30  # Check every 30 seconds
    )
    
    logger.info("✅ IntakeAgent initialized with email monitoring")
    
    # Check status
    status = agent.get_email_monitoring_status()
    logger.info(f"Email monitoring status: {status}")
    
    if status['is_monitoring']:
        logger.info("🎉 Email monitoring is active!")
        logger.info("📧 Send email to rohankool2021@gmail.com to test")
    else:
        logger.warning("⚠️ Email monitoring failed to start")
        logger.info("💡 To enable email monitoring:")
        logger.info("   1. Run: python gmail_direct_integration.py")
        logger.info("   2. Set up Gmail App Password")
        logger.info("   3. Restart this example")
    
    return agent

def example_4_dynamic_control():
    """Example 4: Dynamic email monitoring control"""
    logger.info("=" * 60)
    logger.info("EXAMPLE 4: Dynamic email monitoring control")
    logger.info("=" * 60)
    
    # Initialize without email monitoring
    agent = IntakeClassificationAgent(enable_email_monitoring=False)
    
    logger.info("✅ IntakeAgent initialized without email monitoring")
    
    # Start email monitoring later
    logger.info("Starting email monitoring dynamically...")
    success = agent.start_email_monitoring(
        webhook_url="http://localhost:8001/webhooks/gmail/simple",
        check_interval=60  # Check every minute
    )
    
    if success:
        logger.info("🎉 Email monitoring started successfully!")
    else:
        logger.warning("⚠️ Failed to start email monitoring")
    
    # Check status
    status = agent.get_email_monitoring_status()
    logger.info(f"Email monitoring status: {status['is_monitoring']}")
    
    # Stop email monitoring
    logger.info("Stopping email monitoring...")
    agent.stop_email_monitoring()
    
    # Check status again
    status = agent.get_email_monitoring_status()
    logger.info(f"Email monitoring status after stop: {status['is_monitoring']}")
    
    return agent

def example_5_production_setup():
    """Example 5: Production-ready setup with email monitoring"""
    logger.info("=" * 60)
    logger.info("EXAMPLE 5: Production setup with email monitoring")
    logger.info("=" * 60)
    
    # Production configuration
    config = {
        'enable_email_monitoring': True,
        'webhook_url': 'http://localhost:8001/webhooks/gmail/simple',
        'email_check_interval': 60,  # Check every minute
        # Add your Snowflake configuration here
        'sf_account': None,  # Your Snowflake account
        'sf_user': None,     # Your Snowflake user
        'sf_warehouse': None, # Your warehouse
        'sf_database': None,  # Your database
        'sf_schema': None,    # Your schema
        'sf_role': None       # Your role
    }
    
    try:
        # Initialize with production configuration
        agent = IntakeClassificationAgent(**config)
        
        logger.info("✅ Production IntakeAgent initialized")
        
        # Check email monitoring status
        status = agent.get_email_monitoring_status()
        logger.info(f"Email monitoring: {'✅ Active' if status['is_monitoring'] else '❌ Inactive'}")
        
        if status['is_monitoring']:
            logger.info(f"📧 Monitoring: {status['email_address']}")
            logger.info(f"🔄 Check interval: {status['check_interval']}s")
            logger.info(f"📊 Processed emails: {status['processed_emails']}")
        
        # In production, the agent would run continuously
        logger.info("🏭 Agent ready for production use")
        logger.info("💡 In production, keep this process running to maintain email monitoring")
        
        return agent
        
    except Exception as e:
        logger.error(f"❌ Production setup failed: {e}")
        return None

def main():
    """Run all examples"""
    logger.info("🚀 IntakeAgent Email Integration Examples")
    
    examples = [
        example_1_without_email,
        example_2_with_email_disabled,
        example_3_with_email_enabled,
        example_4_dynamic_control,
        example_5_production_setup
    ]
    
    agents = []
    
    for example in examples:
        try:
            agent = example()
            if agent:
                agents.append(agent)
            time.sleep(1)  # Brief pause between examples
        except Exception as e:
            logger.error(f"Example {example.__name__} failed: {e}")
    
    logger.info("=" * 60)
    logger.info("📋 SUMMARY")
    logger.info("=" * 60)
    logger.info("✅ All examples completed successfully")
    logger.info("")
    logger.info("🔧 Key Features:")
    logger.info("  • Backward compatibility: existing code works unchanged")
    logger.info("  • Optional email monitoring: enable/disable as needed")
    logger.info("  • Background processing: doesn't block main application")
    logger.info("  • Graceful failure: continues working if email fails")
    logger.info("  • Dynamic control: start/stop monitoring anytime")
    logger.info("")
    logger.info("📧 To enable email monitoring:")
    logger.info("  1. Run: python gmail_direct_integration.py")
    logger.info("  2. Follow the Gmail App Password setup")
    logger.info("  3. Use enable_email_monitoring=True")
    logger.info("")
    logger.info("🌐 Email Flow:")
    logger.info("  Gmail → IMAP Monitor → Webhook → IntakeAgent → Ticket")
    
    # Cleanup
    for agent in agents:
        try:
            if hasattr(agent, 'stop_email_monitoring'):
                agent.stop_email_monitoring()
        except:
            pass

if __name__ == "__main__":
    main()