"""
Client Demo Script - Creates a set of professional support tickets via the
live /tickets API so the AI intake -> classification -> assignment pipeline
runs end-to-end and can be shown to the client/cofounder in real time.

Each ticket is written to visibly route to a specific technician based on
their specialization, so the demo makes the AI's routing decision obvious:

    Pratik    (Network Administration)      -> Ticket 1
    Mayur     (Identity & Access Management) -> Ticket 2
    Sahil     (Cybersecurity Support)        -> Ticket 3
    Prathmesh (Application Support)          -> Ticket 4
    Bhavesh   (System Administration)        -> Ticket 5

Usage:
    python examples/client_demo_tickets.py
    python examples/client_demo_tickets.py --base-url http://localhost:8001
"""

import argparse
import sys
import time

import requests

DEMO_TICKETS = [
    {
        "title": "Office WiFi Network Down – Multiple Branch Locations Affected",
        "description": (
            "Employees across 2 branch offices report complete loss of network "
            "connectivity since 9 AM. Router configuration appears unstable — WiFi "
            "access points are dropping every few minutes and VPN connections to "
            "the remote office are failing. DNS resolution is also intermittently "
            "failing on wired connections. Approximately 40 staff are unable to "
            "work, and the sales team cannot access the CRM."
        ),
        "priority": "Critical",
        "due_date": "2026-08-18",
        "requester_name": "Vidhi Dave",
        "user_email": "anantlad66@gmail.com",
        "phone_number": "9876543210",
    },
    {
        "title": "Employee Locked Out of SSO Portal – Urgent Access Restoration Needed",
        "description": (
            "A new hire in Finance is unable to log into the SSO portal after "
            "multiple failed attempts; the account appears locked in Active "
            "Directory. Needs an access control review and password/MFA reset "
            "before end of day so payroll processing is not delayed. Also flag "
            "for review of group permissions — the access request for the shared "
            "Finance drive was never provisioned."
        ),
        "priority": "High",
        "due_date": "2026-08-19",
        "requester_name": "Vidhi Dave",
        "user_email": "anantlad66@gmail.com",
        "phone_number": "9876543210",
    },
    {
        "title": "Phishing Email Detected – Possible Credential Compromise",
        "description": (
            "An employee reported clicking a link in a suspicious email "
            "impersonating IT support and entering their credentials. Immediate "
            "threat detection and containment is required — needs a password "
            "reset, security monitoring on the account, and a check of "
            "firewall/antivirus logs for related indicators of compromise across "
            "the network."
        ),
        "priority": "Critical",
        "due_date": "2026-08-17",
        "requester_name": "Vidhi Dave",
        "user_email": "anantlad66@gmail.com",
        "phone_number": "9876543210",
    },
    {
        "title": "CRM Application Crashing During Report Generation",
        "description": (
            "The sales team's CRM application consistently crashes when "
            "generating quarterly reports with more than 500 records. The issue "
            "started after last week's software update. Needs application "
            "troubleshooting and a configuration review — this is blocking the "
            "sales team from submitting end-of-month reports."
        ),
        "priority": "Medium",
        "due_date": "2026-08-20",
        "requester_name": "Vidhi Dave",
        "user_email": "anantlad66@gmail.com",
        "phone_number": "9876543210",
    },
    {
        "title": "Production Server Performance Degradation",
        "description": (
            "The Windows production server hosting internal tools has been "
            "running at 95%+ CPU since last night, with response times 5x "
            "normal. Needs a server administration review — likely a runaway "
            "process or resource leak. Affects all internal tool users "
            "(~60 employees) company-wide."
        ),
        "priority": "High",
        "due_date": "2026-08-18",
        "requester_name": "Vidhi Dave",
        "user_email": "anantlad66@gmail.com",
        "phone_number": "9876543210",
    },
]


def create_ticket(base_url: str, ticket: dict) -> dict:
    response = requests.post(f"{base_url}/tickets", json=ticket, timeout=120)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Create client demo tickets via the live API")
    parser.add_argument("--base-url", default="http://localhost:8001", help="Backend API base URL")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds to wait between ticket creations")
    args = parser.parse_args()

    print("=" * 70)
    print("CLIENT DEMO — CREATING TICKETS VIA AI ASSIGNMENT PIPELINE")
    print("=" * 70)

    created = []
    for i, ticket in enumerate(DEMO_TICKETS, start=1):
        print(f"\n[{i}/{len(DEMO_TICKETS)}] Creating: {ticket['title']}")
        try:
            result = create_ticket(args.base_url, ticket)
            created.append(result)
            print(f"  Ticket Number : {result.get('ticket_number')}")
            print(f"  Issue Type    : {result.get('issue_type')} / {result.get('sub_issue_type')}")
            print(f"  Priority      : {result.get('priority')}")
            print(f"  Assigned To   : {result.get('assigned_technician')} ({result.get('technician_email')})")
        except requests.exceptions.RequestException as e:
            print(f"  FAILED: {e}")

        if i < len(DEMO_TICKETS):
            time.sleep(args.delay)

    print("\n" + "=" * 70)
    print(f"DONE — {len(created)}/{len(DEMO_TICKETS)} tickets created successfully")
    print("=" * 70)

    if len(created) < len(DEMO_TICKETS):
        sys.exit(1)


if __name__ == "__main__":
    main()
