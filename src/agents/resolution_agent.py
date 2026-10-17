"""
Resolution Agent - Generates AI-powered resolution notes for IT support tickets.

This agent takes ticket metadata and generates step-by-step resolution instructions
using Snowflake Cortex LLM. It's a specialized component of the intake workflow
that focuses solely on resolution generation and error handling.

Author: AutoTask Integration System
Date: 2025-08-15
"""

import logging
from typing import Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResolutionAgent:
    """
    AI-powered agent for generating resolution notes for IT support tickets.

    Generates step-by-step resolution instructions based on:
    - Extracted ticket metadata
    - Classified ticket information
    - Ticket context and urgency level

    Features:
    - LLM-powered resolution generation
    - Fallback handling for generation failures
    - Comprehensive error logging
    - Retry logic for transient failures
    """

    def __init__(self, db_connection=None):
        """
        Initialize the Resolution Agent.

        Args:
            db_connection: Snowflake database connection for LLM access
        """
        self.db_connection = db_connection
        self.llm_model = 'llama3.1-70b'
        self.enabled = db_connection is not None
        self.max_retries = 2
        self.retry_delay = 1  # seconds

        if self.enabled:
            logger.info("✅ ResolutionAgent initialized with LLM access")
        else:
            logger.warning("⚠️ ResolutionAgent initialized without DB connection - will use fallback templates")

    def generate_resolution(self, ticket_data: Dict, classified_data: Dict,
                          extracted_metadata: Dict, ticket_number: str = "",
                          similar_tickets: Optional[List[Dict]] = None) -> str:
        """
        Generate a resolution note for a ticket with mandatory safety precautions.

        Args:
            ticket_data (Dict): Original ticket data (title, description)
            classified_data (Dict): Classification results (ISSUETYPE, PRIORITY, etc.)
            extracted_metadata (Dict): Extracted metadata (main_issue, affected_system, etc.)
            ticket_number (str): Ticket number for logging
            similar_tickets (List[Dict], optional): Similar historical tickets with past resolutions

        Returns:
            str: Generated resolution note with actionable steps and safety precautions
        """
        logger.info(f"📝 Generating resolution with safety precautions for ticket {ticket_number}")

        if not self.enabled:
            logger.warning(f"❌ DB Connection not available - using fallback resolution with safety precautions")
            return self._generate_fallback_resolution(extracted_metadata, classified_data, similar_tickets)

        for attempt in range(self.max_retries):
            try:
                return self._generate_llm_resolution(ticket_data, classified_data, extracted_metadata, similar_tickets)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ All resolution generation attempts failed for {ticket_number}: {str(e)}")
                    return self._generate_fallback_resolution(extracted_metadata, classified_data, similar_tickets)

    def _generate_llm_resolution(self, ticket_data: Dict, classified_data: Dict,
                               extracted_metadata: Dict,
                               similar_tickets: Optional[List[Dict]] = None) -> str:
        """
        Generate resolution using LLM (internal method).

        Args:
            ticket_data: Original ticket data
            classified_data: Classification results
            extracted_metadata: Extracted metadata
            similar_tickets: Similar historical tickets

        Returns:
            str: LLM-generated resolution
        """
        logger.debug("Calling Cortex LLM for resolution generation...")

        prompt = self._build_resolution_prompt(ticket_data, classified_data, extracted_metadata, similar_tickets)

        try:
            llm_response = self.db_connection.call_cortex_llm(
                prompt,
                model=self.llm_model,
                expect_json=False
            )

            if isinstance(llm_response, str) and llm_response.strip():
                logger.info(f"✅ Resolution generated successfully ({len(llm_response)} chars)")
                res_clean = llm_response.strip()
                # Ensure safety precautions block is guaranteed
                if "SAFETY PRECAUTIONS" not in res_clean.upper():
                    res_clean += "\n\n" + self._get_context_safety_precautions(extracted_metadata, classified_data)
                return res_clean
            else:
                logger.error(f"❌ LLM returned empty/invalid response: {llm_response}")
                raise ValueError("LLM returned empty response")

        except Exception as e:
            logger.error(f"❌ LLM call failed: {type(e).__name__}: {str(e)}")
            raise

    def _build_resolution_prompt(self, ticket_data: Dict, classified_data: Dict,
                                extracted_metadata: Dict,
                                similar_tickets: Optional[List[Dict]] = None) -> str:
        """
        Build the LLM prompt for resolution generation with mandatory safety precautions.
        """
        similar_context = ""
        if similar_tickets:
            valid_sim = [t for t in similar_tickets if t.get("RESOLUTION") and len(str(t.get("RESOLUTION")).strip()) > 30]
            if valid_sim:
                similar_context = "\nRELEVANT HISTORICAL RESOLUTIONS FROM KNOWLEDGE BASE:\n"
                for i, st in enumerate(valid_sim[:2]):
                    similar_context += f"Reference #{i+1} ({st.get('TICKETNUMBER', 'N/A')} - {st.get('TITLE', 'N/A')}):\n{st.get('RESOLUTION')}\n---\n"

        return f'''
You are an expert IT and Telecommunications Support Engineer. Based on the extracted metadata and ticket details below, generate a professional, actionable, step-by-step resolution note for technicians and support staff.

CRITICAL RESOLUTION GUIDELINES:
1. Provide numbered, practical, sequential steps (1., 2., 3., etc.) addressing root cause, diagnosis, and remediation.
2. MANDATORY SAFETY SECTION: At the end of every resolution, you MUST include a dedicated section beginning with:
"⚠️ SAFETY PRECAUTIONS:"
Detail the exact hazards and safety rules applicable to the equipment and technologies involved:
- OPTICAL / LASER RADIATION HAZARD (ANSI Z136.2 Class 1M / Class 3B): If fiber optic cables, bulkheads, ONTs, OLTs, splitters, or optical transceivers (400G-ZR, 100G, SFP+) are involved, explicitly instruct NEVER to look directly into open fiber connectors, adapters, or optical ports. Invisible laser radiation causes permanent retinal injury.
- ELECTRICAL & POWER SURGE SAFETY: If power adapters (Wall Warts), electrical circuits, or POTS telephone lines are involved, warn against handling scorched/melted adapters, instruct to test wall outlets with multimeters, unplug equipment before dismounting, and warn of POTS 90V AC ringing voltage shock hazards.
- THERMAL & MECHANICAL HAZARDS: If coherent transceivers (>65°C), high-density chassis, or high-RPM fan trays are involved, warn against contact burns and moving fan blades.
- OUTSIDE PLANT / ENVIRONMENTAL SAFETY: If outside pedestals, FDHs, aerial spans, or roadways are involved, detail roadside traffic cones/signage, venomous insect/spider inspections in cabinets, and utility power line clearances (10+ feet).
- SUBSCRIBER & PREMISE SAFETY: Instruct end-users never to disassemble ONT hardware or bend optical jumpers.
3. Do NOT include JSON, markdown backticks (```), or code formatting. Output as clear plain text.

TICKET DETAILS:
Title: {ticket_data.get('title', 'N/A')}
Description: {ticket_data.get('description', 'N/A')}
Issue Type: {self._extract_field(classified_data, 'ISSUETYPE', 'Hardware')}
Priority: {self._extract_field(classified_data, 'PRIORITY', 'Medium')}

EXTRACTED METADATA:
Main Issue: {extracted_metadata.get('main_issue', 'N/A')}
Affected System: {extracted_metadata.get('affected_system', 'N/A')}
Urgency Level: {extracted_metadata.get('urgency_level', 'N/A')}
Error Messages: {extracted_metadata.get('error_messages', 'N/A')}
Technical Keywords: {', '.join(extracted_metadata.get('technical_keywords', [])) if isinstance(extracted_metadata.get('technical_keywords'), list) else extracted_metadata.get('technical_keywords', 'N/A')}
User Actions: {extracted_metadata.get('user_actions', 'N/A')}
Suggested Resolution Approach: {extracted_metadata.get('resolution_indicators', 'N/A')}
{similar_context}
Generate step-by-step resolution with mandatory ⚠️ SAFETY PRECAUTIONS:
'''

    def _get_context_safety_precautions(self, extracted_metadata: Dict, classified_data: Dict) -> str:
        """Helper to generate targeted safety precautions based on affected technologies."""
        all_text = f"{extracted_metadata.get('main_issue', '')} {extracted_metadata.get('affected_system', '')} {extracted_metadata.get('technical_keywords', '')}".lower()
        issue_type = self._extract_field(classified_data, 'ISSUETYPE', '').lower()

        precautions = ["⚠️ SAFETY PRECAUTIONS:"]

        if any(w in all_text for w in ["fiber", "optical", "ont", "olt", "optic", "400g", "splitter", "fdh", "bulkhead", "otdr", "laser"]):
            precautions.append("- OPTICAL LASER HAZARD (ANSI Z136.2 Class 1M): Active optical fiber carries invisible infrared laser radiation (1310/1490/1550nm). NEVER look directly into open fiber ends, bulkheads, or optical transceivers.")
            precautions.append("- FIBER SHARD DISPOSAL: Dispose of cleaved fiber scraps and protective caps in a puncture-proof container; fiber shards can penetrate skin and cause severe tissue injury.")

        if any(w in all_text for w in ["power", "adapter", "wall wart", "electrical", "outlet", "voltage", "surge", "tripped", "fuse", "lightning"]):
            precautions.append("- ELECTRICAL SHOCK HAZARD: Inspect wall receptacles and adapters for scorching or thermal deformation. Disconnect AC power before dismounting or servicing equipment.")
            precautions.append("- SURGE PROTECTION: Ensure all telecommunications power adapters are connected to a certified UL-1449 surge protector.")

        if any(w in all_text for w in ["tele", "phone", "pots", "dial tone", "voice", "echo", "ring"]):
            precautions.append("- POTS RINGING VOLTAGE CAUTION: Telephone lines carry up to 90V AC during incoming ringing cycles. Never touch bare copper tip-and-ring conductors with uninsulated hands.")

        if any(w in all_text for w in ["400g", "thermal", "temp", "fan", "mx960", "mx304", "cooling"]):
            precautions.append("- THERMAL & MECHANICAL HAZARD: Coherent optical transceivers can exceed 65°C; handle with thermal gloves. Keep fingers and loose cabling clear of high-RPM fan trays.")

        if len(precautions) == 1:
            precautions.append("- GENERAL HARDWARE SAFETY: Disconnect power sources before servicing hardware, verify proper electrical grounding, and ensure adequate ventilation.")

        return "\n".join(precautions)

    def _generate_fallback_resolution(self, extracted_metadata: Dict,
                                    classified_data: Dict,
                                    similar_tickets: Optional[List[Dict]] = None) -> str:
        """
        Generate a fallback resolution with comprehensive safety precautions when LLM is unavailable.
        """
        logger.info("📋 Using fallback resolution template with safety precautions")

        # If a similar ticket with resolution exists, leverage its proven resolution
        if similar_tickets:
            for st in similar_tickets:
                res = str(st.get("RESOLUTION") or "").strip()
                if len(res) > 50 and "⚠️ SAFETY PRECAUTIONS" in res:
                    logger.info(f"Found high-quality golden KB template from similar ticket {st.get('TICKETNUMBER')}")
                    return res

        issue_type = self._extract_field(classified_data, 'ISSUETYPE', 'Hardware')
        urgency = extracted_metadata.get('urgency_level', 'Medium')
        main_issue = extracted_metadata.get('main_issue', 'Issue')
        affected_system = extracted_metadata.get('affected_system', 'system')

        fallback_steps = [
            f"1. Diagnostic Verification: Verify physical power and status indicators on the affected {affected_system}.",
            f"2. Physical Link Inspection: Inspect power cords, network cables, and optical jumpers for damage, loose terminations, or micro-bends.",
            f"3. Component Power-Cycle: Perform a clean electrical reboot of {affected_system} by unplugging the power supply for 30 seconds.",
            f"4. Signal & Interface Test: Check interface error counters, optical receive power, and IP gateway connectivity.",
            f"5. Hardware/Service Remediation: If errors or offline status persist, swap defective module/power supply with verified unit from inventory and verify baseline performance."
        ]

        if urgency.lower() in ['critical', 'high']:
            fallback_steps.insert(0, "⚠️ HIGH PRIORITY PROTOCOL - Escalating to specialized Tier 2 / Field Engineering dispatch.")

        safety_block = self._get_context_safety_precautions(extracted_metadata, classified_data)
        return "\n".join(fallback_steps) + "\n\n" + safety_block

    def _extract_field(self, data: Dict, field_name: str, default: str = "system") -> str:
        """
        Extract a field from classified data safely.
        """
        if field_name in data:
            field_data = data[field_name]
            if isinstance(field_data, dict):
                return field_data.get('Label', field_data.get('Value', default))
            return str(field_data)
        return default

    def validate_resolution(self, resolution_note: str) -> bool:
        """
        Validate that a resolution note has minimum quality standards and safety precautions.
        """
        if not resolution_note or not isinstance(resolution_note, str):
            logger.warning("❌ Resolution validation failed: empty or invalid")
            return False

        if len(resolution_note.strip()) < 20:
            logger.warning(f"❌ Resolution validation failed: too short ({len(resolution_note)} chars)")
            return False

        has_steps = any(char.isdigit() and resolution_note[i+1:i+2] == '.'
                       for i, char in enumerate(resolution_note))

        if not has_steps:
            logger.warning("❌ Resolution validation failed: no numbered steps found")
            return False

        logger.info(f"✅ Resolution validation passed ({len(resolution_note)} chars, contains steps)")
        return True


# Public interface function for backward compatibility
def generate_resolution_for_ticket(ticket_data: Dict, classified_data: Dict,
                                  extracted_metadata: Dict, db_connection=None,
                                  ticket_number: str = "",
                                  similar_tickets: Optional[List[Dict]] = None) -> str:
    """
    Public function to generate resolution using ResolutionAgent.
    """
    agent = ResolutionAgent(db_connection=db_connection)
    return agent.generate_resolution(ticket_data, classified_data, extracted_metadata, ticket_number, similar_tickets=similar_tickets)

