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

        Guidelines for urgency_level assessment:
        - "Critical": System down, security breach, data loss, business-critical functions unavailable
        - "High": Major functionality impaired, multiple users affected, workarounds difficult
        - "Medium": Single user affected, workarounds available, non-critical functions impaired
        - "Low": Minor issues, cosmetic problems, feature requests, general questions

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
            label = self.reference_data.get(field.lower(), {}).get(str(info["Value"]), "Unknown")
            summary_str += f"{field}: {info['Value']} (Label: {label}, appeared {info['Count']} times)\n"

        classification_prompt = f"""
        You are an expert IT support ticket classifier. Analyze the ticket content carefully and classify it based on what the issue is actually about.

        **CRITICAL CLASSIFICATION RULES:**
        1. **Content-First Analysis**: Base your classification PRIMARILY on the ticket title, description, and extracted metadata
        2. **Logical Categorization**:
           - Software applications (Teams, Office, browsers, etc.) → TICKETCATEGORY: Software/SaaS
           - Hardware devices (printers, computers, phones) → TICKETCATEGORY: Hardware
           - Network connectivity, WiFi, internet → TICKETCATEGORY: Network
           - Email, Exchange, Outlook → TICKETCATEGORY: Email/Communication
           - Security, passwords, access → TICKETCATEGORY: Security
        3. **Ignore Misleading Patterns**: Do NOT be influenced by potentially incorrect historical classifications

        **Classification Fields:**
        - **ISSUETYPE** → Type of request (Incident=something broken, Request=asking for something, Problem=recurring issue, Change=modification)
        - **SUBISSUETYPE** → Specific sub-category within the issue type
        - **TICKETCATEGORY** → What system/area is affected (Software, Hardware, Network, Security, etc.)
        - **TICKETTYPE** → Service Request, Incident, Problem, Change Request, or Task
        - **PRIORITY** → Urgency level based on business impact and user-specified priority
        - **STATUS** → Always "Open" for new tickets

        **ANALYSIS STEPS:**
        1. Read the ticket title and description carefully
        2. Identify what system/application/hardware is mentioned
        3. Determine if it's broken (Incident) or a request for something (Request)
        4. Choose the category that matches the affected system
        5. Set appropriate priority based on impact and urgency
 
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
                PRIORITY: {ticket.get('PRIORITY', 'N/A')}
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

**CLASSIFICATION INSTRUCTIONS:**

1. **ANALYZE THE TICKET CONTENT FIRST**: Look at the title, description, and extracted metadata to understand what the issue is actually about.

2. **CHOOSE THE CORRECT CATEGORY**: Based on the content analysis:
   - If it mentions software applications (Teams, Office, browsers, etc.) → TICKETCATEGORY should be "Software/SaaS"
   - If it mentions hardware (printers, computers, phones) → TICKETCATEGORY should be "Hardware"
   - If it mentions network/connectivity → TICKETCATEGORY should be "Network"
   - If it mentions email/communication → TICKETCATEGORY should be "Email" or similar

3. **DETERMINE ISSUE TYPE**:
   - If something is broken/not working → ISSUETYPE: "Incident"
   - If user is requesting something → ISSUETYPE: "Request"

4. **USE AVAILABLE OPTIONS**: Select from the provided classification options that best match your analysis.

5. **HISTORICAL CONTEXT**: Use similar tickets only as secondary reference, not as the primary decision factor.

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
            classified_data = {}

            # Intelligent fallback based on ticket content analysis
            classified_data = self._intelligent_fallback_classification(new_ticket_data, extracted_metadata, summary)

        return classified_data

    def _intelligent_fallback_classification(self, ticket_data: Dict, extracted_metadata: Dict, summary: Dict) -> Dict:
        """
        Intelligent fallback classification based on content analysis when LLM fails
        """
        # Analyze ticket content
        title = ticket_data.get('title', '').lower()
        description = ticket_data.get('description', '').lower()
        main_issue = extracted_metadata.get('main_issue', '').lower()
        affected_system = extracted_metadata.get('affected_system', '').lower()

        # Combine all text for analysis
        all_text = f"{title} {description} {main_issue} {affected_system}"

        # Content-based classification logic
        classified_data = {}

        # Determine TICKETCATEGORY based on content
        if any(keyword in all_text for keyword in ['teams', 'office', 'software', 'application', 'app', 'saas', 'browser', 'outlook']):
            category_value = self._find_value_by_label("ticketcategory", "Software/SaaS") or self._find_value_by_label("ticketcategory", "Software")
            classified_data["TICKETCATEGORY"] = {"Value": category_value, "Label": "Software/SaaS"}
        elif any(keyword in all_text for keyword in ['printer', 'computer', 'laptop', 'hardware', 'device', 'phone']):
            category_value = self._find_value_by_label("ticketcategory", "Hardware") or self._find_value_by_label("ticketcategory", "Printer")
            classified_data["TICKETCATEGORY"] = {"Value": category_value, "Label": "Hardware"}
        elif any(keyword in all_text for keyword in ['network', 'wifi', 'internet', 'connectivity', 'connection']):
            category_value = self._find_value_by_label("ticketcategory", "Network")
            classified_data["TICKETCATEGORY"] = {"Value": category_value, "Label": "Network"}
        elif any(keyword in all_text for keyword in ['email', 'exchange', 'mail']):
            category_value = self._find_value_by_label("ticketcategory", "Email")
            classified_data["TICKETCATEGORY"] = {"Value": category_value, "Label": "Email"}
        else:
            # Use most common from similar tickets or default
            if "TICKETCATEGORY" in summary:
                label = self.reference_data.get('ticketcategory', {}).get(str(summary["TICKETCATEGORY"]["Value"]), "Unknown")
                classified_data["TICKETCATEGORY"] = {"Value": summary["TICKETCATEGORY"]["Value"], "Label": label}
            else:
                # Default to Software/SaaS for unknown issues
                category_value = self._find_value_by_label("ticketcategory", "Software/SaaS") or "5"
                classified_data["TICKETCATEGORY"] = {"Value": category_value, "Label": "Software/SaaS"}

        # Determine ISSUETYPE (Incident vs Request)
        if any(keyword in all_text for keyword in ['not working', 'broken', 'error', 'issue', 'problem', 'down', 'failed', 'not responding']):
            issue_value = self._find_value_by_label("issuetype", "Incident") or "1"
            classified_data["ISSUETYPE"] = {"Value": issue_value, "Label": "Incident"}
        else:
            issue_value = self._find_value_by_label("issuetype", "Request") or "2"
            classified_data["ISSUETYPE"] = {"Value": issue_value, "Label": "Request"}

        # Set other fields with intelligent defaults
        for field in ["SUBISSUETYPE", "TICKETTYPE", "PRIORITY"]:
            if field in summary:
                label = self.reference_data.get(field.lower(), {}).get(str(summary[field]["Value"]), "Unknown")
                classified_data[field] = {"Value": summary[field]["Value"], "Label": label}
            else:
                # Set reasonable defaults
                if field == "SUBISSUETYPE":
                    classified_data[field] = {"Value": "N/A", "Label": "N/A"}
                elif field == "TICKETTYPE":
                    type_value = self._find_value_by_label("tickettype", "Incident") or "2"
                    classified_data[field] = {"Value": type_value, "Label": "Incident"}
                elif field == "PRIORITY":
                    priority_value = self._find_value_by_label("priority", "Medium") or "2"
                    classified_data[field] = {"Value": priority_value, "Label": "Medium"}

        # Always set STATUS to Open
        status_value = self._find_value_by_label("status", "Open") or "1"
        classified_data["STATUS"] = {"Value": status_value, "Label": "Open"}

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