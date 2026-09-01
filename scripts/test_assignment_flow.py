"""
Test Assignment Agent with Skill Matching and Shift Schedules
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.database.snowflake_db import SnowflakeConnection
from src.agents.assignment_agent import AssignmentAgentIntegration

def run_test():
    print("Connecting to Snowflake...")
    conn = SnowflakeConnection(
        sf_account=config.SF_ACCOUNT,
        sf_user=config.SF_USER,
        sf_warehouse=config.SF_WAREHOUSE,
        sf_database=config.SF_DATABASE,
        sf_schema=config.SF_SCHEMA,
        sf_role=config.SF_ROLE,
        sf_password=config.SF_PASSWORD,
        sf_authenticator=config.SF_AUTHENTICATOR,
        sf_passcode=config.SF_PASSCODE,
        sf_private_key_file=getattr(config, 'SF_PRIVATE_KEY_PATH', None),
        sf_private_key_pwd=getattr(config, 'SF_PRIVATE_KEY_PWD', None)
    )

    agent = AssignmentAgentIntegration(conn)

    # Test Ticket 1: Network / Firewall issue (Matches Alex Morgan - TECH001)
    ticket_1 = {
        'new_ticket': {
            'ticket_number': 'TKT-NET-101',
            'description': 'Cisco firewall rules blocking VPN and routing',
            'due_date': '2026-09-02T18:00:00Z',
            'name': 'Sarah Connor',
            'user_email': 'sarah@cyberdyne.com',
            'classified_data': {
                'ISSUETYPE': {'Label': 'Network'},
                'SUBISSUETYPE': {'Label': 'VPN'},
                'TICKETCATEGORY': {'Label': 'Network'},
                'PRIORITY': {'Label': 'High'}
            }
        }
    }

    print("\n==========================================")
    print("TEST 1: Assigning Network / VPN Ticket")
    print("==========================================")
    res_1 = agent.process_ticket_assignment(ticket_1)
    print("Assignment Result:")
    print(json.dumps(res_1, indent=2))

    # Test Ticket 2: Hardware / Laptop issue (Matches Brian Davis - TECH002)
    ticket_2 = {
        'new_ticket': {
            'ticket_number': 'TKT-HW-102',
            'description': 'Laptop screen flickering and motherboard replacement required',
            'due_date': '2026-09-02T18:00:00Z',
            'name': 'Kyle Reese',
            'user_email': 'kyle@resistance.com',
            'classified_data': {
                'ISSUETYPE': {'Label': 'Hardware'},
                'SUBISSUETYPE': {'Label': 'Laptop'},
                'TICKETCATEGORY': {'Label': 'Hardware'},
                'PRIORITY': {'Label': 'Medium'}
            }
        }
    }

    print("\n==========================================")
    print("TEST 2: Assigning Hardware / Laptop Ticket")
    print("==========================================")
    res_2 = agent.process_ticket_assignment(ticket_2)
    print("Assignment Result:")
    print(json.dumps(res_2, indent=2))

if __name__ == "__main__":
    run_test()
