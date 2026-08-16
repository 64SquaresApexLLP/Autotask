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
        self.llm_model = 'llama3-70b'
        self.enabled = db_connection is not None
        self.max_retries = 2
        self.retry_delay = 1  # seconds

        if self.enabled:
            logger.info("✅ ResolutionAgent initialized with LLM access")
        else:
            logger.warning("⚠️ ResolutionAgent initialized without DB connection - will use fallback templates")

    def generate_resolution(self, ticket_data: Dict, classified_data: Dict,
                          extracted_metadata: Dict, ticket_number: str = "") -> str:
        """
        Generate a resolution note for a ticket.

        Args:
            ticket_data (Dict): Original ticket data (title, description)
            classified_data (Dict): Classification results (ISSUETYPE, PRIORITY, etc.)
            extracted_metadata (Dict): Extracted metadata (main_issue, affected_system, etc.)
            ticket_number (str): Ticket number for logging

        Returns:
            str: Generated resolution note with actionable steps
        """
        logger.info(f"📝 Generating resolution for ticket {ticket_number}")

        if not self.enabled:
            logger.warning(f"❌ DB Connection not available - using fallback resolution")
            return self._generate_fallback_resolution(extracted_metadata, classified_data)

        for attempt in range(self.max_retries):
            try:
                return self._generate_llm_resolution(ticket_data, classified_data, extracted_metadata)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ All resolution generation attempts failed for {ticket_number}: {str(e)}")
                    return self._generate_fallback_resolution(extracted_metadata, classified_data)

    def _generate_llm_resolution(self, ticket_data: Dict, classified_data: Dict,
                               extracted_metadata: Dict) -> str:
        """
        Generate resolution using LLM (internal method).

        Args:
            ticket_data: Original ticket data
            classified_data: Classification results
            extracted_metadata: Extracted metadata

        Returns:
            str: LLM-generated resolution

        Raises:
            Exception: If LLM call fails
        """
        logger.debug("Calling Cortex LLM for resolution generation...")

        prompt = self._build_resolution_prompt(extracted_metadata)

        try:
            llm_response = self.db_connection.call_cortex_llm(
                prompt,
                model=self.llm_model,
                expect_json=False
            )

            if isinstance(llm_response, str) and llm_response.strip():
                logger.info(f"✅ Resolution generated successfully ({len(llm_response)} chars)")
                return llm_response.strip()
            else:
                logger.error(f"❌ LLM returned empty/invalid response: {llm_response}")
                raise ValueError("LLM returned empty response")

        except Exception as e:
            logger.error(f"❌ LLM call failed: {type(e).__name__}: {str(e)}")
            raise

    def _build_resolution_prompt(self, extracted_metadata: Dict) -> str:
        """
        Build the LLM prompt for resolution generation.

        Args:
            extracted_metadata: Extracted ticket metadata

        Returns:
            str: Formatted LLM prompt
        """
        return f'''
You are an expert IT support analyst. Based on the following extracted metadata from an IT support ticket, generate a concise, actionable resolution note with clear, numbered steps for the end-user to follow. The resolution should directly address the main issue and context provided by the metadata.

IMPORTANT GUIDELINES:
- Do NOT include any generic or irrelevant steps
- Do NOT reference unavailable information
- Do NOT include any JSON or code formatting
- Only provide step-by-step resolution as plain text
- Number each step clearly (1., 2., 3., etc.)
- Focus on practical, user-actionable steps

EXTRACTED METADATA:
Main Issue: {extracted_metadata.get('main_issue', 'N/A')}
Affected System: {extracted_metadata.get('affected_system', 'N/A')}
Urgency Level: {extracted_metadata.get('urgency_level', 'N/A')}
Error Messages: {extracted_metadata.get('error_messages', 'N/A')}
Technical Keywords: {', '.join(extracted_metadata.get('technical_keywords', []))}
User Actions: {extracted_metadata.get('user_actions', 'N/A')}
Resolution Approach: {extracted_metadata.get('resolution_indicators', 'N/A')}

Generate step-by-step resolution:
'''

    def _generate_fallback_resolution(self, extracted_metadata: Dict,
                                    classified_data: Dict) -> str:
        """
        Generate a fallback resolution based on templates when LLM is unavailable.

        Args:
            extracted_metadata: Extracted ticket metadata
            classified_data: Classification results

        Returns:
            str: Template-based resolution
        """
        logger.info("📋 Using fallback resolution template")

        issue_type = self._extract_field(classified_data, 'ISSUETYPE')
        urgency = extracted_metadata.get('urgency_level', 'Medium')
        main_issue = extracted_metadata.get('main_issue', 'Issue')
        affected_system = extracted_metadata.get('affected_system', 'system')

        fallback_steps = [
            f"1. Verify the affected {affected_system} is turned on and properly connected.",
            f"2. Check if there are any error messages or indicators for the {affected_system}.",
            f"3. Try restarting the {affected_system} if applicable.",
            f"4. Review system logs for any recent errors related to {main_issue}.",
            f"5. If the issue persists after these steps, please contact technical support with details of steps taken.",
        ]

        # Add urgency-specific guidance
        if urgency.lower() in ['critical', 'high']:
            fallback_steps.insert(0, "⚠️ HIGH PRIORITY TICKET - Escalating to specialized support team immediately.")

        return "\n".join(fallback_steps)

    def _extract_field(self, data: Dict, field_name: str, default: str = "system") -> str:
        """
        Extract a field from classified data safely.

        Args:
            data: Dictionary to extract from
            field_name: Field name
            default: Default value if field not found

        Returns:
            str: Field value or default
        """
        if field_name in data:
            field_data = data[field_name]
            if isinstance(field_data, dict):
                return field_data.get('Label', field_data.get('Value', default))
            return str(field_data)
        return default

    def validate_resolution(self, resolution_note: str) -> bool:
        """
        Validate that a resolution note has minimum quality standards.

        Args:
            resolution_note: Resolution text to validate

        Returns:
            bool: True if resolution meets minimum standards
        """
        if not resolution_note or not isinstance(resolution_note, str):
            logger.warning("❌ Resolution validation failed: empty or invalid")
            return False

        # Check minimum length
        if len(resolution_note.strip()) < 20:
            logger.warning(f"❌ Resolution validation failed: too short ({len(resolution_note)} chars)")
            return False

        # Check for numbered steps
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
                                  ticket_number: str = "") -> str:
    """
    Public function to generate resolution using ResolutionAgent.

    This is the recommended way to generate resolutions in the ticket workflow.

    Args:
        ticket_data (Dict): Original ticket data
        classified_data (Dict): Classification results
        extracted_metadata (Dict): Extracted metadata
        db_connection: Snowflake database connection
        ticket_number (str): Ticket number for logging

    Returns:
        str: Generated resolution note
    """
    agent = ResolutionAgent(db_connection=db_connection)
    return agent.generate_resolution(ticket_data, classified_data, extracted_metadata, ticket_number)
