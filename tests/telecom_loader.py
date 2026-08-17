"""
Telecom Dataset Loader and System Integration Module.
Parses CTTC Telecom Support Ticket Tracker and integrates records into AutoTask.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default Official Technicians Roster provided by Team
TECHNICIANS_ROSTER = [
    {
        "id": "T001",
        "name": "Anant Lad",
        "email": "ladanant09@gmail.com",
        "role": "Application Support",
        "skills": ["Application Support", "Software", "Bug Fixing", "App Troubleshooting"],
        "max_workload": 10,
        "current_workload": 0
    },
    {
        "id": "T002",
        "name": "Anant L",
        "email": "ladanant418@gmail.com",
        "role": "Identity & Access Mgmt",
        "skills": ["IAM", "Password Reset", "User Access", "Authentication", "MFA"],
        "max_workload": 10,
        "current_workload": 0
    },
    {
        "id": "T003",
        "name": "Vidhi Dave",
        "email": "vidhidaveautotask@gmail.com",
        "role": "IT Support",
        "skills": ["IT Support", "Hardware", "Device Setup", "Printer", "General IT"],
        "max_workload": 10,
        "current_workload": 0
    },
    {
        "id": "T004",
        "name": "Rohan K",
        "email": "rohankool2017@gmail.com",
        "role": "Network Administrator",
        "skills": ["Network", "Fiber", "ONT", "Router", "Wi-Fi", "Internet Outage", "Calix Cloud"],
        "max_workload": 15,
        "current_workload": 0
    },
    {
        "id": "T005",
        "name": "Shubh",
        "email": "shubh77589@gmail.com",
        "role": "System Administrator",
        "skills": ["System Administration", "Server", "Windows", "Linux", "Infrastructure"],
        "max_workload": 10,
        "current_workload": 0
    },
    {
        "id": "T006",
        "name": "Honey Bliss",
        "email": "honeybliss0504@gmail.com",
        "role": "Cybersecurity Specialist",
        "skills": ["Cybersecurity", "Phishing", "Security Incident", "Malware", "Account Compromise"],
        "max_workload": 10,
        "current_workload": 0
    }
]

USERS_ROSTER = [
    {"id": "U001", "name": "Anant Lad 66", "email": "ananatlad66@gmail.com"},
    {"id": "U002", "name": "Anant Lad 0628", "email": "anantlad0628@gmail.com"}
]


class TelecomDataLoader:
    """
    Parses Telecom Excel Ticket Tracker and provides structured integration objects.
    """

    def __init__(self, excel_path: str = "data/CTTC_Support_Ticket_Tracker_1.xlsx",
                 knowledgebase_path: str = "data/knowledgebase.json"):
        self.excel_path = excel_path
        self.knowledgebase_path = knowledgebase_path
        self.technicians = TECHNICIANS_ROSTER
        self.users = USERS_ROSTER

    def get_technician_by_role(self, role_name: str) -> Optional[Dict]:
        """Finds a technician by matching their role."""
        for tech in self.technicians:
            if tech["role"].lower() == role_name.lower():
                return tech
        return self.technicians[0]

    def match_technician_for_ticket(self, category: str, security_flag: str, notes: str) -> Dict:
        """
        Determines the best technician based on ticket category and security flags.
        """
        category_lower = str(category).lower()
        notes_lower = str(notes).lower()
        sec_flag = str(security_flag).strip().upper()

        if sec_flag == "Y" or "phishing" in notes_lower or "compromise" in notes_lower or "security" in category_lower:
            return self.get_technician_by_role("Cybersecurity Specialist")
        elif "password" in notes_lower or "access" in notes_lower or "iam" in category_lower:
            return self.get_technician_by_role("Identity & Access Mgmt")
        elif "internet" in category_lower or "wifi" in category_lower or "router" in notes_lower or "ont" in notes_lower or "buffering" in category_lower:
            return self.get_technician_by_role("Network Administrator")
        elif "device" in category_lower or "setup" in category_lower or "hardware" in category_lower:
            return self.get_technician_by_role("IT Support")
        elif "server" in category_lower or "system" in category_lower:
            return self.get_technician_by_role("System Administrator")
        else:
            return self.get_technician_by_role("Application Support")

    def parse_excel_tickets(self) -> List[Dict[str, Any]]:
        """
        Reads and parses all tickets from the Excel file.
        """
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Excel file not found at: {self.excel_path}")

        logger.info(f"Loading telecom dataset from: {self.excel_path}")
        # Sheet header is at row index 4 (0-indexed 3)
        df = pd.read_excel(self.excel_path, sheet_name="Ticket Log", skiprows=3)
        df.columns = [str(c).strip() for c in df.iloc[0]]
        df = df.iloc[1:].reset_index(drop=True)

        parsed_tickets = []
        for idx, row in df.iterrows():
            api_ticket = str(row.get("API ticket #", "")).strip()
            if not api_ticket or api_ticket.lower() == "nan":
                continue

            date_reported = str(row.get("Date reported", "")).strip()
            town = str(row.get("Town", "")).strip()
            customer = str(row.get("Customer", "")).strip()
            category = str(row.get("Category", "General Support")).strip()
            security_flag = str(row.get("Security /\nphishing flag", "N")).strip()
            status = str(row.get("Status", "Open")).strip()
            resolution = str(row.get("Resolution / outcome", "")).strip()
            system_priority = str(row.get("System priority", "Medium")).strip()
            recommended_priority = str(row.get("Recommended\npriority", "Medium")).strip()
            notes = str(row.get("Notes", "")).strip()

            # Assign smart technician based on category and security flag
            assigned_tech = self.match_technician_for_ticket(category, security_flag, notes)

            # Build full standardized ticket object
            ticket_obj = {
                "ticket_number": api_ticket,
                "title": f"[{town}] {category} - {customer}",
                "description": f"Customer: {customer} ({town}). Issue: {category}. Notes: {notes if notes and notes != 'nan' else 'None'}",
                "category": category,
                "town": town,
                "customer_name": customer,
                "date_reported": date_reported,
                "system_priority": system_priority,
                "priority": recommended_priority if recommended_priority and recommended_priority != "nan" else "Medium",
                "status": status,
                "security_flag": security_flag,
                "resolution_note": resolution if resolution and resolution != "nan" else "Pending investigation",
                "assigned_technician": assigned_tech["name"],
                "technician_email": assigned_tech["email"],
                "technician_role": assigned_tech["role"],
                "created_at": date_reported if date_reported and date_reported != "nan" else datetime.now().isoformat()
            }
            parsed_tickets.append(ticket_obj)

        logger.info(f"Successfully parsed {len(parsed_tickets)} tickets from Excel sheet.")
        return parsed_tickets

    def build_category_playbooks(self) -> List[Dict[str, Any]]:
        """
        Extracts and structures the 6 Master Category Playbooks from the Telecom Dataset.
        """
        playbooks = [
            {
                "ticket_number": "CAT-NET-01",
                "title": "Internet not working",
                "category": "Internet not working",
                "issue_type": "Network",
                "description": "Master resolution playbook for complete internet outages, WAN connection loss, and ONT optical faults. Steps: 1. Verify fiber ONT power/optical LEDs. 2. Power cycle router/gateway (30s). 3. Check town outage map. 4. Dispatch field technician if optical loss detected.",
                "priority": "High",
                "status": "Active",
                "assigned_technician": "Rohan K",
                "technician_email": "rohankool2017@gmail.com",
                "customer_name": "CTTC Master Knowledge Base",
                "town": "All Towns",
                "resolution_note": "Standard Router/Hub reboot and WAN ONT link check fixed 80% of reported outages."
            },
            {
                "ticket_number": "CAT-EML-02",
                "title": "Email trouble & Phishing Incidents",
                "category": "Email trouble",
                "issue_type": "Software/SaaS",
                "description": "Master resolution playbook for email lockouts, credential compromise, and fake scheduled maintenance phishing attacks. Steps: 1. Check Security Flag (Y). 2. Lock compromised account. 3. Verify CPNI identity. 4. Reset password securely. 5. Escalate to Cybersecurity.",
                "priority": "Medium",
                "status": "Active",
                "assigned_technician": "Honey Bliss",
                "technician_email": "honeybliss0504@gmail.com",
                "customer_name": "CTTC Master Knowledge Base",
                "town": "All Towns",
                "resolution_note": "Immediate password reset and CPNI identity verification resolve credential compromises."
            },
            {
                "ticket_number": "CAT-DEV-03",
                "title": "Need help setting up device",
                "category": "Need help setting up device",
                "issue_type": "Hardware",
                "description": "Master resolution playbook for new router setup, CommandIQ mobile app onboarding, and Wi-Fi pairing. Steps: 1. Identify router model & serial. 2. Guide customer through CommandIQ app setup. 3. Configure 2.4GHz & 5GHz SSIDs. 4. Test connectivity.",
                "priority": "Low",
                "status": "Active",
                "assigned_technician": "Vidhi Dave",
                "technician_email": "vidhidaveautotask@gmail.com",
                "customer_name": "CTTC Master Knowledge Base",
                "town": "All Towns",
                "resolution_note": "Customer assisted with CommandIQ app download, SSID configuration, and router pairing."
            },
            {
                "ticket_number": "CAT-INT-04",
                "title": "Internet going on/off (Intermittent)",
                "category": "Internet going on/off",
                "issue_type": "Network",
                "description": "Master resolution playbook for unstable connection and frequent drops. Steps: 1. Inspect physical cable & fiber patch integrity. 2. Check line noise / attenuation logs. 3. Reboot ONT and router. 4. Replace degraded router if flapping continues.",
                "priority": "Medium",
                "status": "Active",
                "assigned_technician": "Rohan K",
                "technician_email": "rohankool2017@gmail.com",
                "customer_name": "CTTC Master Knowledge Base",
                "town": "All Towns",
                "resolution_note": "Cable check, line noise test, and ONT power cycle resolve intermittent connection drops."
            },
            {
                "ticket_number": "CAT-SPD-05",
                "title": "Internet slow",
                "category": "Internet slow",
                "issue_type": "Network",
                "description": "Master resolution playbook for low bandwidth and speed test failures. Steps: 1. Perform wired Ethernet speed test. 2. Check Wi-Fi channel interference (switch to 5GHz). 3. Inspect connected background devices. 4. Reprovision bandwidth profile.",
                "priority": "Low",
                "status": "Active",
                "assigned_technician": "Rohan K",
                "technician_email": "rohankool2017@gmail.com",
                "customer_name": "CTTC Master Knowledge Base",
                "town": "All Towns",
                "resolution_note": "Speed test verification and 5GHz band optimization restore full subscription speeds."
            },
            {
                "ticket_number": "CAT-BUF-06",
                "title": "Device buffering",
                "category": "Device buffering",
                "issue_type": "Hardware",
                "description": "Master resolution playbook for Smart TV video buffering and streaming lag. Steps: 1. Test streaming service across devices. 2. Enable QoS prioritization in gateway. 3. Restart streaming adapter / Smart TV Wi-Fi. 4. Relocate mesh node closer.",
                "priority": "Medium",
                "status": "Active",
                "assigned_technician": "Vidhi Dave",
                "technician_email": "vidhidaveautotask@gmail.com",
                "customer_name": "CTTC Master Knowledge Base",
                "town": "All Towns",
                "resolution_note": "WAN/ONT check, streaming device restart, and QoS optimization eliminate video buffering."
            }
        ]
        return playbooks

    def integrate_into_knowledgebase(self) -> Dict[str, Any]:
        """
        Integrates the 6 Category Master Playbooks and Technicians into knowledgebase.json.
        """
        playbooks = self.build_category_playbooks()

        kb_data = {
            "tickets": playbooks,
            "categories": [
                {
                    "category": p["category"],
                    "issue_type": p["issue_type"],
                    "playbook_id": p["ticket_number"],
                    "priority": p["priority"],
                    "assigned_technician": p["assigned_technician"],
                    "technician_email": p["technician_email"],
                    "standard_resolution": p["resolution_note"]
                }
                for p in playbooks
            ],
            "technicians": self.technicians,
            "users": self.users,
            "quick_wins_rules": [
                "1. Check Security/Phishing flag on every intake ticket.",
                "2. Apply recommended priority (Low/Medium/High/Critical) instead of default Medium.",
                "3. Flag repeat contacts contacting within 48 hours for quality check.",
                "4. Require valid customer contact email at intake.",
                "5. Start daily aging escalations check for tickets open > 24 hours."
            ],
            "last_updated": datetime.now().isoformat()
        }

        os.makedirs(os.path.dirname(self.knowledgebase_path), exist_ok=True)
        with open(self.knowledgebase_path, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, indent=4)

        logger.info(f"Knowledgebase updated with {len(playbooks)} Category Master Playbooks.")
        return {
            "total_parsed": len(playbooks),
            "added_to_kb": len(playbooks),
            "updated_in_kb": 0,
            "total_kb_tickets": len(playbooks),
            "technicians_count": len(self.technicians)
        }

    def upload_categories_to_snowflake(self, snowflake_conn, clean_individual_tickets: bool = True) -> Dict[str, Any]:
        """
        Safely removes the 141 individual tickets (starting with 10013) from Snowflake,
        keeping all original team data intact, and inserts the 6 Category Master Playbooks.
        """
        if not snowflake_conn or not snowflake_conn.conn:
            raise ConnectionError("Snowflake database connection is not active.")

        cursor = snowflake_conn.conn.cursor()

        if clean_individual_tickets:
            cursor.execute("DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE '10013%'")
            logger.info("Removed individual 10013 tickets from Snowflake.")

        cursor.execute("DESCRIBE TABLE TEST_DB.PUBLIC.TICKETS")
        desc_rows = cursor.fetchall()
        existing_columns = {row[0].upper() for row in desc_rows}

        playbooks = self.build_category_playbooks()
        inserted = 0

        for p in playbooks:
            ticket_data = {
                "TICKETNUMBER": p["ticket_number"],
                "TITLE": p["title"],
                "DESCRIPTION": p["description"],
                "PRIORITY": p["priority"],
                "STATUS": p["status"],
                "TECHNICIANEMAIL": p["technician_email"],
                "USEREMAIL": "knowledgebase@cttc.com",
                "DUEDATETIME": datetime.now().strftime("%Y-%m-%d"),
                "USERID": "CTTC-KB",
                "CUSTOMER_NAME": p["customer_name"],
                "TOWN": p["town"],
                "CATEGORY": p["category"],
                "RESOLUTION_NOTE": p["resolution_note"]
            }

            cols = [c for c in ticket_data if c in existing_columns]
            vals = [ticket_data[c] for c in cols]
            placeholders = ", ".join(["%s"] * len(cols))
            cols_str = ", ".join(cols)

            try:
                cursor.execute("DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s", (p["ticket_number"],))
                cursor.execute(f"INSERT INTO TEST_DB.PUBLIC.TICKETS ({cols_str}) VALUES ({placeholders})", tuple(vals))
                inserted += 1
            except Exception as e:
                logger.warning(f"Could not insert playbook {p['ticket_number']}: {e}")

        snowflake_conn.conn.commit()
        cursor.close()
        logger.info(f"Successfully uploaded {inserted} Category Master Playbooks to Snowflake.")
        return {"total_uploaded": inserted, "playbooks": len(playbooks)}
