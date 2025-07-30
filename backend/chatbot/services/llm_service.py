"""LLM service using Snowflake Cortex Complete for AI-powered resolutions."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import snowflake.connector
from ..config import settings
from ..database import Ticket

logger = logging.getLogger(__name__)


class LLMService:
    """Service for AI-powered technical support using Snowflake Cortex Complete."""
    
    def __init__(self):
        self.cortex_available = False
        self.snowflake_connection = None
        self.connection_verified = False

        # Initialize Cortex connection (non-blocking)
        try:
            self._initialize_cortex_connection()
        except Exception as e:
            logger.warning(f"LLM Service initialization failed: {e}")
            self.cortex_available = False
    
    def _initialize_cortex_connection(self):
        """Initialize Snowflake Cortex connection."""
        try:
            if not self._should_try_cortex():
                logger.warning("Cortex configuration incomplete - skipping initialization")
                return
            
            logger.info("Initializing Snowflake Cortex connection...")
            
            connection_params = {
                'account': settings.snowflake_account,
                'user': settings.snowflake_user,
                'database': settings.snowflake_database,
                'schema': settings.snowflake_schema,
                'warehouse': settings.snowflake_warehouse,
                'authenticator': settings.snowflake_authenticator or 'snowflake'
            }
            
            # Add password if available
            if settings.snowflake_password:
                connection_params['password'] = settings.snowflake_password
            
            # Create connection with timeout
            self.snowflake_connection = snowflake.connector.connect(
                **connection_params,
                login_timeout=15,
                network_timeout=15
            )
            
            # Test Cortex availability
            cursor = self.snowflake_connection.cursor()
            test_query = "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', 'Hello') as response"
            cursor.execute(test_query)
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0]:
                self.cortex_available = True
                self.connection_verified = True
                logger.info("Snowflake Cortex LLM service initialized successfully")
            else:
                raise Exception("Cortex test query failed")
                
        except Exception as e:
            logger.warning(f"Cortex initialization failed: {e}")
            self.cortex_available = False
            if self.snowflake_connection:
                try:
                    self.snowflake_connection.close()
                except:
                    pass
                self.snowflake_connection = None
    
    def _should_try_cortex(self) -> bool:
        """Check if Cortex initialization should be attempted."""
        try:
            required_settings = [
                settings.snowflake_account,
                settings.snowflake_user,
                settings.snowflake_database,
                settings.snowflake_schema,
                settings.snowflake_warehouse
            ]
            return all(setting and setting.strip() for setting in required_settings)
        except Exception:
            return False
    
    def generate_resolution_for_issue(self, issue_description: str, similar_tickets: List[Ticket] = None, metadata: Dict = None) -> str:
        """Generate AI-powered resolution for a technical issue with enhanced context."""
        try:
            if not self.cortex_available:
                raise Exception("Snowflake Cortex is not available. Please check your Snowflake connection.")

            # Build enhanced context from similar tickets
            context = ""
            if similar_tickets:
                context = "\n\nSimilar resolved tickets for reference:\n"
                for i, ticket in enumerate(similar_tickets[:3], 1):
                    if ticket.resolution and ticket.resolution.strip():
                        context += f"{i}. Issue: {ticket.title}\n"
                        context += f"   Type: {ticket.issuetype or 'N/A'} - {ticket.subissuetype or 'N/A'}\n"
                        context += f"   Resolution: {ticket.resolution[:400]}...\n\n"

            # Add metadata context if available
            metadata_context = ""
            if metadata:
                metadata_context = f"\n\nIssue Analysis:\n"
                if metadata.get('issue_type'):
                    metadata_context += f"- Issue Type: {metadata['issue_type']}\n"
                if metadata.get('device_types'):
                    metadata_context += f"- Devices: {', '.join(metadata['device_types'])}\n"
                if metadata.get('software_mentioned'):
                    metadata_context += f"- Software: {', '.join(metadata['software_mentioned'])}\n"
                if metadata.get('urgency_indicators'):
                    metadata_context += f"- Urgency: {', '.join(metadata['urgency_indicators'])}\n"
                if metadata.get('action_requested'):
                    metadata_context += f"- Action Needed: {metadata['action_requested']}\n"
            
            # Create comprehensive prompt for Cortex
            prompt = f"""You are an expert IT support technician with 10+ years of experience. A user needs immediate, actionable help with this technical issue.

ISSUE TO RESOLVE:
{issue_description}

{metadata_context}

{context}

PROVIDE A COMPREHENSIVE RESOLUTION WITH:

## 🔍 **What's Happening**
Explain in 1-2 sentences what's likely causing this issue.

## 🛠️ **Step-by-Step Solution**
Provide 5-7 SPECIFIC, ACTIONABLE steps:

1. **[Action Title]** - Exact steps with specific commands or procedures
2. **[Action Title]** - Include menu paths like "Settings → Network → Advanced"
3. **[Action Title]** - Provide actual commands like "Run: cmd → type: ipconfig /release"
4. **[Action Title]** - Specify file locations like "C:\\Windows\\System32\\drivers\\etc\\hosts"
5. **[Action Title]** - Include verification: "You should see [specific result]"

## ✅ **How to Verify It Worked**
Tell the user exactly what they should see when the issue is fixed.

## 🔄 **If That Doesn't Work**
Provide 2-3 alternative approaches with specific steps.

REQUIREMENTS:
- Every step must be IMMEDIATELY actionable
- Use exact commands, not placeholders
- Include specific file paths and system locations
- Provide exact button names and menu sequences
- Be conversational and supportive
- End with encouragement to ask follow-up questions"""

            # Call Cortex Complete
            resolution = self._call_cortex(prompt)
            
            if resolution and len(resolution.strip()) > 50:
                return resolution
            else:
                raise Exception("Cortex returned empty or insufficient resolution")

        except Exception as e:
            logger.error(f"Error generating resolution: {e}")
            raise
    
    def generate_interactive_ai_resolution(self, user_problem: str, conversation_history: List[str] = None, similar_tickets: List[Ticket] = None, metadata: Dict = None) -> str:
        """Generate interactive AI resolution that asks clarifying questions and provides step-by-step help."""
        try:
            if not self.cortex_available:
                raise Exception("Snowflake Cortex is not available. Please check your Snowflake connection.")

            # Build context from conversation history
            history_context = ""
            if conversation_history:
                history_context = "\n\nConversation History:\n" + "\n".join(conversation_history[-6:])

            # Build context from similar tickets
            ticket_context = ""
            if similar_tickets:
                ticket_context = "\n\nSimilar resolved tickets for reference:\n"
                for ticket in similar_tickets[:3]:
                    if ticket.resolution and ticket.resolution.strip():
                        ticket_context += f"- {ticket.title}: {ticket.resolution[:200]}...\n"

            # Always provide direct solutions instead of asking clarifying questions
            # Build comprehensive prompt for immediate solution
            prompt = f"""You are an expert IT support technician with 10+ years of experience. Provide a COMPREHENSIVE, step-by-step solution for this technical issue.

ORIGINAL PROBLEM: {user_problem}
{history_context}
{ticket_context}

Now provide a DETAILED SOLUTION with:

## 🔍 **Problem Analysis**
Based on what you've told me, here's what's likely happening...

## 🛠️ **Step-by-Step Solution**
1. **[Specific Action]** - Exact steps with commands/procedures
2. **[Next Action]** - Include menu paths like "Settings → System → Advanced"
3. **[Verification Step]** - "You should see [specific result]"
4. **[Alternative if needed]** - "If that doesn't work, try..."

## ✅ **How to Know It's Fixed**
You'll know the problem is resolved when...

## 🔄 **If You Still Have Issues**
If these steps don't work, try:
- [Alternative approach 1]
- [Alternative approach 2]

Let me know how it goes! I'm here if you need any clarification on these steps. 😊

Response:"""

            response = self._call_cortex(prompt)

            if response and len(response.strip()) > 50:
                return response
            else:
                raise Exception("Cortex returned empty or insufficient response")

        except Exception as e:
            logger.error(f"Error generating interactive AI resolution: {e}")
            raise

    def generate_conversational_response(self, context_type: str, user_message: str, conversation_history: List[str] = None) -> str:
        """Generate conversational follow-up responses."""
        try:
            if not self.cortex_available:
                raise Exception("Snowflake Cortex is not available. Please check your Snowflake connection.")

            # Build conversation context
            history_context = ""
            if conversation_history:
                history_context = "\n\nConversation History:\n" + "\n".join(conversation_history[-4:])

            # Create conversational prompt
            prompt = f"""You are a helpful IT support assistant having a friendly conversation with a technician.

Context: {context_type}
User Message: {user_message}
{history_context}

Respond in a conversational, helpful manner. Be supportive and offer specific assistance. Keep responses concise but informative. If they're asking for help, provide actionable guidance. If they're giving feedback, acknowledge it appropriately and offer next steps.

Response:"""

            response = self._call_cortex(prompt)

            if response and len(response.strip()) > 10:
                return response
            else:
                raise Exception("Cortex returned empty or insufficient response")

        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            raise
    
    def _call_cortex(self, prompt: str) -> str:
        """Call Snowflake Cortex Complete."""
        try:
            self._ensure_connection()
            
            cursor = self.snowflake_connection.cursor()
            
            # Escape single quotes in prompt
            escaped_prompt = prompt.replace("'", "''")
            
            # Use Cortex Complete with mistral-7b model
            query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', '{escaped_prompt}') as response"
            
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0]:
                return result[0].strip()
            else:
                raise Exception("No response from Cortex")
                
        except Exception as e:
            logger.error(f"Cortex API error: {e}")
            raise
    
    def _ensure_connection(self):
        """Ensure Snowflake connection is active."""
        if not self.snowflake_connection or not self.connection_verified:
            logger.warning("Snowflake connection lost, attempting to reconnect...")
            self._initialize_cortex_connection()
            
        if not self.cortex_available:
            raise Exception("Cortex connection not available")
    


    def close_connection(self):
        """Close Snowflake connection."""
        if self.snowflake_connection:
            try:
                self.snowflake_connection.close()
                logger.info("Snowflake connection closed successfully")
            except Exception as e:
                logger.warning(f"Error closing Snowflake connection: {e}")
            finally:
                self.snowflake_connection = None
                self.connection_verified = False
                self.cortex_available = False
