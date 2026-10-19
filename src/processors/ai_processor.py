"""
AI/LLM processing module for TeamLogic-AutoTask application.
Handles metadata extraction, ticket classification, and resolution generation using Snowflake Cortex LLM.
"""

import json
import re
from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database import SnowflakeConnection


class AIProcessor:
    """
    Handles AI/LLM operations including metadata extraction, classification, and resolution generation.
    """

    def __init__(self, db_connection: SnowflakeConnection, reference_data: Dict):
        """
        Initialize the AI processor.

        Args:
            db_connection (SnowflakeConnection): Database connection for LLM calls
            reference_data (dict): Reference data for classification mappings
        """
        self.db_connection = db_connection
        self.reference_data = reference_data

    def _find_value_by_label(self, field_name: str, label: str) -> str:
        """
        Find the value (ID) for a given label in the reference data.
        
        Args:
            field_name (str): The field name (e.g., "issuetype", "subissuetype")
            label (str): The label to search for
            
        Returns:
            str: The value (ID) for the label, or "N/A" if not found
        """
        if field_name in self.reference_data:
            for value, ref_label in self.reference_data[field_name].items():
                if ref_label.lower() == label.lower():
                    return value
        return "N/A"

    def _resolve_reference(self, field_name: str, raw_value) -> Optional[Dict[str, str]]:
        """
        Resolve a raw classification value to its {"Value", "Label"} reference pair.

        Similar historical tickets may store either the numeric reference Value
        (e.g. "2") or the Label itself (e.g. "Medium") depending on how the row
        was written, so both forms must be handled here. Previously, a Label
        string was looked up against the Value-keyed reference map and fell
        back to "Unknown", which then got persisted as the ticket priority and
        rendered as UNKNOWN on every ticket page.

        Returns None when the value cannot be matched to the reference data.
        """
        if raw_value is None:
            return None
        field_map = self.reference_data.get(field_name, {})
        raw_str = str(raw_value).strip()
        if not raw_str:
            return None
        # Direct hit: raw value is a numeric reference Value (e.g. "2").
        if raw_str in field_map:
            return {"Value": raw_str, "Label": field_map[raw_str]}
        # Otherwise treat the raw value as (or as containing) a Label.
        raw_lower = raw_str.lower()
        for value, label in field_map.items():
            if str(label).strip().lower() == raw_lower:
                return {"Value": value, "Label": label}
        return None

    def _resolve_priority(self, ticket_data: Dict, summary: Dict) -> Dict[str, str]:
        """
        Resolve PRIORITY to a valid {"Value", "Label"} pair.

        Resolution order:
        1. The user-set priority from the creation form (priority_initial), so
           an explicitly chosen priority is never lost or degraded.
        2. The most common priority among similar historical tickets (handles
           rows that store either the Value ID or the Label).
        3. The "Medium" default from the reference data.
        """
        # 1. The user explicitly chose a priority when creating the ticket.
        user_priority = self._resolve_reference("priority", ticket_data.get("priority", ""))
        if user_priority:
            return user_priority

        # 2. Most common priority among similar tickets.
        if "PRIORITY" in summary:
            resolved = self._resolve_reference("priority", summary["PRIORITY"].get("Value"))
            if resolved:
                return resolved

        # 3. Sensible default.
        priority_value = self._find_value_by_label("priority", "Medium")
        if priority_value == "N/A":
            priority_value = "2"
        return {"Value": priority_value,
                "Label": self.reference_data.get("priority", {}).get(priority_value, "Medium")}

    def extract_metadata(self, title: str, description: str, model: str = 'llama3.1-70b') -> Optional[Dict]:
        """
        Extracts structured metadata from the ticket title and description using LLM.

        Args:
            title (str): Ticket title
            description (str): Ticket description
            model (str): LLM model to use

        Returns:
            dict: Extracted metadata or None if failed
        """
        prompt = f"""
        Analyze the following IT support ticket title and description and extract the specified metadata in JSON format.
        Ensure all fields are present. For urgency_level, analyze the impact and urgency based on the issue described.

        Ticket Title: "{title}"
        Ticket Description: "{description}"

        Guidelines for urgency_level assessment (same scale as ticket PRIORITY):
        - "Critical": outage affecting many customers or a site (area outage, OLT/PON port down,
          cabinet damage, core link down), security breach, or a business/medical service fully down
        - "High": one customer with NO service at all (no internet, red/LOS ONT light, cut fiber,
          dead ONT or router)
        - "Medium": service works but is degraded or intermittent (slowness, drops, echo)
        - "Low": no fault: questions, configuration changes, moves/installs, billing

        Guidelines for error_messages extraction:
        - Look for specific error codes, error numbers, or exact error text in quotes
        - Include popup messages, dialog box text, or system-generated messages
        - Examples: "Error 404", "Connection timeout", "Access denied", "File not found"
        - If no specific error message is mentioned, extract any symptoms or failure descriptions

        JSON Schema:
        {{
            "main_issue": "What is the main issue or problem described?",
            "affected_system": "What system or application is affected?",
            "urgency_level": "Assess urgency based on impact and business criticality (Critical, High, Medium, or Low)",
            "error_messages": "Extract any specific error messages, codes, or failure symptoms mentioned in the ticket",
            "technical_keywords": ["list", "of", "technical", "terms", "separated", "by", "comma"],
            "user_actions": "What actions was the user trying to perform when the issue occurred?",
            "resolution_indicators": "What type of resolution approach or common fix might address this issue?",
            "STATUS": "Open"
        }}
        """
        print("Extracting metadata with LLM...")
        extracted_data = None
        if self.db_connection and self.db_connection.is_connected():
            try:
                extracted_data = self.db_connection.call_cortex_llm(prompt, model=model)
            except Exception as e:
                print(f"⚠️ Cortex LLM call failed: {e}")
                extracted_data = None

        if extracted_data:
            extracted_data["STATUS"] = "Open"
            return extracted_data

        # Robust Heuristic Fallback when LLM is offline or Snowflake SSO is disconnected
        print("ℹ️ Using intelligent rule-based metadata extraction fallback...")
        text_combined = f"{title} {description}".lower()

        # Determine affected system
        affected_system = "Workstation / OS"
        if any(w in text_combined for w in ['vpn', 'wifi', 'wi-fi', 'network', 'internet', 'dns', 'gateway', 'dhcp', 'ip']):
            affected_system = "Network / VPN"
        elif any(w in text_combined for w in ['outlook', 'email', 'mail', 'exchange', 'inbox', 'spam', 'phishing']):
            affected_system = "Email / Outlook"
        elif any(w in text_combined for w in ['printer', 'print', 'spooler', 'paper', 'jam', 'toner']):
            affected_system = "Printer"
        elif any(w in text_combined for w in ['active directory', 'password', 'lockout', 'login', 'account', 'credential', 'access denied', 'permission']):
            affected_system = "Active Directory / Identity"
        elif any(w in text_combined for w in ['excel', 'teams', 'slack', 'chrome', 'browser', 'salesforce', 'adobe', 'app', 'crash', 'freeze']):
            affected_system = "Software / SaaS"
        elif any(w in text_combined for w in ['mac', 'macbook', 'apple', 'macos', 'jamf', 'ios']):
            affected_system = "macOS / Apple"
        elif any(w in text_combined for w in ['server', 'backup', 'datto', 'veeam', 'hyper-v', 'virtual']):
            affected_system = "Server / Backup"
        elif any(w in text_combined for w in ['screen', 'monitor', 'keyboard', 'mouse', 'battery', 'overheating', 'laptop', 'hardware', 'dock']):
            affected_system = "Hardware"

        # Determine urgency
        urgency = "Medium"
        if any(w in text_combined for w in ['urgent', 'critical', 'immediately', 'outage', 'down', 'locked out', 'blocked', 'emergency']):
            urgency = "High"
        elif any(w in text_combined for w in ['low', 'minor', 'cosmetic', 'question']):
            urgency = "Low"

        # Extract keywords
        raw_words = re.findall(r'\b[a-zA-Z0-9_\-\.]{3,}\b', text_combined)
        stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'user', 'have', 'been', 'cannot', 'unable', 'please', 'help', 'not', 'issue', 'problem', 'reported'}
        keywords = [w for w in raw_words if w not in stop_words][:8]

        return {
            "main_issue": title.strip() or "Reported IT Issue",
            "affected_system": affected_system,
            "urgency_level": urgency,
            "error_messages": "See description for error signatures and symptoms",
            "technical_keywords": keywords if keywords else ["IT Support", "Workstation"],
            "user_actions": "Standard workplace operations",
            "resolution_indicators": "Systematic diagnostic troubleshooting and standard IT procedure",
            "STATUS": "Open"
        }

    def classify_ticket(self, new_ticket_data: Dict, extracted_metadata: Dict,
                       similar_tickets: List[Dict], model: str = 'llama3.1-70b') -> Optional[Dict]:
        """
        Classifies the new ticket (ISSUETYPE, SUBISSUETYPE, TICKETCATEGORY, TICKETTYPE, PRIORITY)
        based on extracted metadata and similar tickets using LLM.

        Args:
            new_ticket_data (dict): New ticket data
            extracted_metadata (dict): Extracted metadata
            similar_tickets (list): List of similar tickets
            model (str): LLM model to use

        Returns:
            dict: Classification data or None if failed
        """
        from collections import Counter

        # Summarize similar tickets
        summary = {}
        for field in ["ISSUETYPE", "SUBISSUETYPE", "TICKETCATEGORY", "TICKETTYPE", "PRIORITY"]:
            values = [ticket.get(field) for ticket in similar_tickets if ticket.get(field) not in [None, "N/A"]]
            if values:
                most_common, count = Counter(values).most_common(1)[0]
                summary[field] = {"Value": most_common, "Count": count}

        summary_str = "\nMost common classification values among similar tickets:\n"
        for field, info in summary.items():
            # Priority is decided from this ticket's impact, not copied from history
            # (summary["PRIORITY"] is still used by the _resolve_priority fallback).
            if field == "PRIORITY":
                continue
            # Similar-ticket values may be Value IDs or Labels; resolve both so
            # the prompt never advertises an "Unknown" label for a valid field.
            resolved = self._resolve_reference(field.lower(), info["Value"])
            label = resolved["Label"] if resolved else str(info["Value"])
            summary_str += f"{field}: {info['Value']} (Label: {label}, appeared {info['Count']} times)\n"

        classification_prompt = f"""
        You are an expert IT and Telecommunications support ticket classifier. Analyze the ticket content carefully and classify it based on technical domain, affected system, and standard Autotask reference data.

        **CRITICAL CLASSIFICATION MAPPINGS (Conform strictly to reference data):**
        1. **ISSUETYPE (What technology domain is impacted?):**
           - Premise ONT, Power Adapter (Wall Wart), Wi-Fi Controller, Router hardware, PC, Printer → ISSUETYPE: Hardware
           - Fiber optics, 400G optic, Core Router (MX960), Aggregation (MX304, ACX), BGP, ERPS, Internet connectivity, OLT, VLAN/QinQ → ISSUETYPE: Network
           - Landline dead, No dial tone, POTS line, Voice echo, VoIP delay, Jitter, SIP → ISSUETYPE: Telephony
           - Business applications, TR-069 ACS server, operating system, software → ISSUETYPE: Software/SaaS
           - Outlook, Exchange, email issues → ISSUETYPE: Email
           - Security incidents, unauthorized access, breaches → ISSUETYPE: Cybersecurity Intrusion

        2. **SUBISSUETYPE (Specific sub-domain):**
           - Total outage, internet down, packet loss, fiber cuts, carrier dropouts → SUBISSUETYPE: Connectivity/Outages
           - Optical drop jumper, bulkhead, cabling, wiring faults → SUBISSUETYPE: Cabling
           - Wi-Fi extender, mesh satellite, AP coverage, WPS pairing → SUBISSUETYPE: Wireless
           - POTS telephone dead, dial tone loss, line static/hum → SUBISSUETYPE: Phone Issue
           - Voice latency, audio echo, VoIP jitter, SIP codec → SUBISSUETYPE: VOIP Connection/Latency
           - Premise ONT equipment unit, modem → SUBISSUETYPE: Modem
           - Core chassis, fan trays, cooling, workstations → SUBISSUETYPE: Workstation

        3. **TICKETCATEGORY:**
           - General operational and field dispatch tickets → TICKETCATEGORY: Standard
           - Automated network monitoring telemetry alarms → TICKETCATEGORY: Standard or AEM Alert

        4. **TICKETTYPE:**
           - Broken service, outage, equipment failure, degraded quality → TICKETTYPE: Incident
           - New equipment setup, static IP request, provisioning assistance → TICKETTYPE: Service Request
           - Recurring architectural vulnerability, SPOF, chronic defects → TICKETTYPE: Problem
           - Scheduled software upgrade, firmware maintenance window → TICKETTYPE: Change Request

        5. **PRIORITY:** decide from the impact described in THIS ticket (how many
           customers are affected and whether service is completely down). Do not
           copy the priority of similar tickets or the user-given initial priority
           when the description clearly indicates a different impact.
           - **Critical:** outage affecting MANY customers or a site: neighborhood/area
             outage, OLT or PON port down, splitter/cabinet damage, core/transport link
             down, cell tower down, or a business/medical/emergency service completely down.
           - **High:** ONE customer with NO service at all: no internet, red/LOS light on
             the ONT, fiber drop cut, dead ONT or router, no dial tone and no internet.
           - **Medium:** service works but is degraded or intermittent: slowness, occasional
             drops, packet loss, voice echo, a single feature not working.
           - **Low:** no fault: how-to questions, configuration changes, relocation or
             installation requests, billing questions, scheduled maintenance.

        ---
 
        **New Ticket Information**  
        - **Title:** "{new_ticket_data.get('title', '')}"  
        - **Description:** "{new_ticket_data.get('description', '')}"  
        - **Extracted Metadata:** {json.dumps(extracted_metadata, indent=2)}  
        - **Initial Priority (user-given):** "{new_ticket_data.get('priority', new_ticket_data.get('priority_initial', 'Medium'))}"  
 
        ---
 
        **Similar Historical Tickets for Context:**  
        (Use these as references for classification consistency)  

        Consider the following similar historical tickets for classification context:
        """

        MAX_SIMILAR_TICKETS_FOR_PROMPT = 15
        if similar_tickets:
            for i, ticket in enumerate(similar_tickets[:MAX_SIMILAR_TICKETS_FOR_PROMPT]):
                # Safely handle None values in ticket data
                title = ticket.get('TITLE') or 'N/A'
                title_truncated = title[:100] if isinstance(title, str) else 'N/A'

                classification_prompt += f"""
                --- Similar Ticket {i+1} ---
                Title: {title_truncated}
                ISSUE_TYPE: {ticket.get('ISSUETYPE', 'N/A')}
                SUBISSUE_TYPE: {ticket.get('SUBISSUETYPE', 'N/A')}
                CATEGORY: {ticket.get('TICKETCATEGORY', 'N/A')}
                TYPE: {ticket.get('TICKETTYPE', 'N/A')}
                """
        else:
            classification_prompt += "\nNo similar historical tickets found to provide additional context."

        classification_prompt += summary_str
        classification_prompt += """
\n\nAvailable Classification Options (Field: {Value: Label, ...}):\n"""
        classification_fields = ["issuetype", "subissuetype", "ticketcategory", "tickettype", "priority", "status"]

        for field_name in classification_fields:
            if field_name in self.reference_data:
                options_str = ", ".join([f'"{val}": "{label}"' for val, label in self.reference_data[field_name].items()])
                classification_prompt += f"  {field_name.upper()}: {{{options_str}}}\n"
            else:
                classification_prompt += f"  {field_name.upper()}: No specific options provided.\n"

        classification_prompt += """

**OUTPUT FORMAT**: Provide classification in JSON format with both Value (numerical ID) and Label from the available options.

JSON Schema:
{{
    "ISSUETYPE": {{ "Value": "numerical_id", "Label": "Descriptive Label" }},
    "SUBISSUETYPE": {{ "Value": "numerical_id", "Label": "Descriptive Label" }},
    "TICKETCATEGORY": {{ "Value": "numerical_id", "Label": "Descriptive Label" }},
    "TICKETTYPE": {{ "Value": "numerical_id", "Label": "Descriptive Label" }},
    "STATUS": {{ "Value": "numerical_id", "Label": "Descriptive Label" }},
    "PRIORITY": {{ "Value": "numerical_id", "Label": "Descriptive Label" }}
}}
"""

        print("Classifying ticket with LLM...")
        classified_data = self.db_connection.call_cortex_llm(classification_prompt, model=model)

        # Handle case where LLM returns None
        if not classified_data:
            print("LLM classification failed, using intelligent content-based fallback classification")
            classified_data = self._intelligent_fallback_classification(new_ticket_data, extracted_metadata, summary)
        else:
            llm_priority = classified_data.get("PRIORITY")
            resolved_priority = None
            if isinstance(llm_priority, dict):
                resolved_priority = (self._resolve_reference("priority", llm_priority.get("Label"))
                                     or self._resolve_reference("priority", llm_priority.get("Value")))
            elif llm_priority is not None:
                resolved_priority = self._resolve_reference("priority", llm_priority)

            if resolved_priority:
                classified_data["PRIORITY"] = resolved_priority
            else:
                print(f"LLM returned invalid PRIORITY ({llm_priority!r}); recovering via priority resolution chain")
                classified_data["PRIORITY"] = self._resolve_priority(new_ticket_data, summary)

        return classified_data

    def _intelligent_fallback_classification(self, ticket_data: Dict, extracted_metadata: Dict, summary: Dict) -> Dict:
        """
        Intelligent fallback classification based on telecom/IT content analysis when LLM fails
        """
        title = ticket_data.get('title', '').lower()
        description = ticket_data.get('description', '').lower()
        main_issue = str(extracted_metadata.get('main_issue', '')).lower()
        affected_system = str(extracted_metadata.get('affected_system', '')).lower()
        keywords = str(extracted_metadata.get('technical_keywords', '')).lower()

        all_text = f"{title} {description} {main_issue} {affected_system} {keywords}"
        classified_data = {}

        # 1. Determine ISSUETYPE
        if any(w in all_text for w in ['tele', 'phone', 'pots', 'dial tone', 'voice', 'echo', 'delay', 'call']):
            val = self._find_value_by_label("issuetype", "Telephony") or "10"
            classified_data["ISSUETYPE"] = {"Value": val, "Label": "Telephony"}
        elif any(w in all_text for w in ['fiber', 'optic', '400g', 'core', 'uplink', 'erps', 'bgp', 'qinq', 'evpn', 'olt', 'network', 'outage', 'circuit']):
            val = self._find_value_by_label("issuetype", "Network") or "6"
            classified_data["ISSUETYPE"] = {"Value": val, "Label": "Network"}
        elif any(w in all_text for w in ['ont', 'wall wart', 'power supply', 'adapter', 'hardware', 'controller', 'router', 'printer', 'laptop', 'device']):
            val = self._find_value_by_label("issuetype", "Hardware") or "4"
            classified_data["ISSUETYPE"] = {"Value": val, "Label": "Hardware"}
        elif any(w in all_text for w in ['email', 'outlook', 'exchange', 'mail']):
            val = self._find_value_by_label("issuetype", "Email") or "15"
            classified_data["ISSUETYPE"] = {"Value": val, "Label": "Email"}
        else:
            val = self._find_value_by_label("issuetype", "Hardware") or "4"
            classified_data["ISSUETYPE"] = {"Value": val, "Label": "Hardware"}

        # 2. Determine SUBISSUETYPE
        if any(w in all_text for w in ['dial tone', 'dead phone', 'line static', 'noisy line', 'cuts off']):
            val = self._find_value_by_label("subissuetype", "Phone Issue") or "55"
            classified_data["SUBISSUETYPE"] = {"Value": val, "Label": "Phone Issue"}
        elif any(w in all_text for w in ['voice delay', 'echo', 'voip', 'jitter', 'latency']):
            val = self._find_value_by_label("subissuetype", "VOIP Connection/Latency") or "181"
            classified_data["SUBISSUETYPE"] = {"Value": val, "Label": "VOIP Connection/Latency"}
        elif any(w in all_text for w in ['wifi', 'wireless', 'extender', 'mesh', 'ssid', 'wps']):
            val = self._find_value_by_label("subissuetype", "Wireless") or "21"
            classified_data["SUBISSUETYPE"] = {"Value": val, "Label": "Wireless"}
        elif any(w in all_text for w in ['cable', 'cabling', 'bulkhead', 'connector', 'jumper', 'drop wire', 'sc/apc']):
            val = self._find_value_by_label("subissuetype", "Cabling") or "19"
            classified_data["SUBISSUETYPE"] = {"Value": val, "Label": "Cabling"}
        elif any(w in all_text for w in ['ont', 'modem', 'gateway']):
            val = self._find_value_by_label("subissuetype", "Modem") or "200"
            classified_data["SUBISSUETYPE"] = {"Value": val, "Label": "Modem"}
        elif any(w in all_text for w in ['outage', 'down', 'fiber cut', 'break', 'severed', 'flapping']):
            val = self._find_value_by_label("subissuetype", "Connectivity/Outages") or "64"
            classified_data["SUBISSUETYPE"] = {"Value": val, "Label": "Connectivity/Outages"}
        else:
            val = self._find_value_by_label("subissuetype", "Connectivity/Outages") or "64"
            classified_data["SUBISSUETYPE"] = {"Value": val, "Label": "Connectivity/Outages"}

        # 3. Determine TICKETCATEGORY (Standard = 3)
        cat_val = self._find_value_by_label("ticketcategory", "Standard") or "3"
        classified_data["TICKETCATEGORY"] = {"Value": cat_val, "Label": "Standard"}

        # 4. Determine TICKETTYPE
        if any(w in all_text for w in ['setup', 'help setting up', 'configure', 'request', 'install', 'static ip']):
            type_val = self._find_value_by_label("tickettype", "Service Request") or "1"
            classified_data["TICKETTYPE"] = {"Value": type_val, "Label": "Service Request"}
        elif any(w in all_text for w in ['spof', 'single point of failure', 'vulnerability', 'chronic']):
            type_val = self._find_value_by_label("tickettype", "Problem") or "3"
            classified_data["TICKETTYPE"] = {"Value": type_val, "Label": "Problem"}
        else:
            type_val = self._find_value_by_label("tickettype", "Incident") or "2"
            classified_data["TICKETTYPE"] = {"Value": type_val, "Label": "Incident"}

        # 5. PRIORITY
        classified_data["PRIORITY"] = self._resolve_priority(ticket_data, summary)

        # 6. STATUS (Open = 1)
        status_val = self._find_value_by_label("status", "New") or "1"
        classified_data["STATUS"] = {"Value": status_val, "Label": "New"}

        print("Applied intelligent content-based fallback classification:")
        for field, value in classified_data.items():
            print(f"  {field}: {value['Value']} ({value['Label']})")

        return classified_data


    def generate_resolution_note(self, ticket_data: Dict, classified_data: Dict,
                                extracted_metadata: Dict) -> str:
        """
        Generates a resolution note using Cortex LLM, based solely on the extracted metadata of the ticket.

        Args:
            ticket_data (dict): Original ticket data
            classified_data (dict): Classification results
            extracted_metadata (dict): Extracted metadata

        Returns:
            str: Generated resolution note
        """
        print("Generating resolution using Cortex LLM based on extracted metadata...")

        title = ticket_data.get('title', '')
        description = ticket_data.get('description', '')

        # Prepare a focused prompt for the LLM
        prompt = f'''
        You are an expert IT support analyst. Based on the following extracted metadata from an IT support ticket, generate a concise, actionable resolution note with clear, numbered steps for the end-user to follow. The resolution should directly address the main issue and context provided by the metadata. Do not include any generic or irrelevant steps. Do not reference unavailable information. Do not include any JSON or code formatting in your response—just the step-by-step resolution as plain text.

        Extracted Metadata:
        - Main Issue: {extracted_metadata.get('main_issue', 'N/A')}
        - Affected System: {extracted_metadata.get('affected_system', 'N/A')}
        - Urgency Level: {extracted_metadata.get('urgency_level', 'N/A')}
        - Error Messages: {extracted_metadata.get('error_messages', 'N/A')}
        - Technical Keywords: {', '.join(extracted_metadata.get('technical_keywords', []))}
        - User Actions: {extracted_metadata.get('user_actions', 'N/A')}
        - Suggested Resolution Approach: {extracted_metadata.get('resolution_indicators', 'N/A')}

        Instructions:
        1. Generate a step-by-step resolution plan tailored to the main issue and context above.
        2. The steps should be practical for an end-user to perform.
        3. Do not include any JSON, code blocks, or explanations—just the resolution steps as plain text.
        4. Number each step clearly.
        5. If information is missing, focus only on the available metadata.
        '''

        print("Calling Cortex LLM for resolution generation...")
        llm_response = self.db_connection.call_cortex_llm(prompt, model='llama3.1-70b', expect_json=False)

        if isinstance(llm_response, str) and llm_response.strip():
            return llm_response.strip()
        else:
            return "Resolution could not be generated at this time. Please try again later."