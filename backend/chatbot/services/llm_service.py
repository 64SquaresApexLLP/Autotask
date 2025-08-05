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
        """Generate AI-powered resolution for a technical issue with enhanced context and ticket references."""
        try:
            if not self.cortex_available:
                # Fallback to rule-based resolution
                return self._generate_fallback_resolution(issue_description, similar_tickets, metadata)
            
            # Prepare context from similar tickets
            ticket_context = ""
            ticket_references = []
            
            if similar_tickets:
                ticket_context = "Based on similar historical tickets:\n"
                for i, ticket in enumerate(similar_tickets[:3], 1):  # Use top 3 similar tickets
                    ticket_context += f"Ticket {i}: {ticket.ticketnumber} - {ticket.title}\n"
                    ticket_context += f"Resolution: {ticket.resolution or 'No resolution recorded'}\n\n"
                    ticket_references.append(ticket.ticketnumber)
            
            # Create enhanced prompt for Cortex
            prompt = f"""You are an expert IT support technician. Generate a comprehensive resolution for the following technical issue.

ISSUE DESCRIPTION: {issue_description}

{ticket_context}

Please provide a detailed resolution that includes:
1. Step-by-step troubleshooting instructions
2. Specific commands or procedures if applicable
3. Preventive measures to avoid similar issues
4. References to similar tickets if available

Generate a professional, clear, and actionable resolution:"""

            # Call Cortex
            response = self._call_cortex(prompt)
            
            # Add ticket references if available
            if ticket_references:
                response += f"\n\n📋 References: Based on analysis of similar tickets: {', '.join(ticket_references)}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI resolution: {e}")
            return self._generate_fallback_resolution(issue_description, similar_tickets, metadata)
    
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
    
    def _generate_fallback_resolution(self, issue_description: str, similar_tickets: List[Ticket] = None, metadata: Dict = None) -> str:
        """Generate a fallback resolution when Cortex is not available."""
        try:
            # Extract key information from the issue
            issue_lower = issue_description.lower()
            
            # Check for common issue patterns
            if any(word in issue_lower for word in ['password', 'login', 'authentication']):
                return self._generate_login_resolution()
            elif any(word in issue_lower for word in ['network', 'internet', 'connection']):
                return self._generate_network_resolution()
            elif any(word in issue_lower for word in ['printer', 'print']):
                return self._generate_printer_resolution()
            elif any(word in issue_lower for word in ['slow', 'performance', 'lag']):
                return self._generate_performance_resolution()
            elif any(word in issue_lower for word in ['install', 'installation', 'setup']):
                return self._generate_installation_resolution()
            else:
                return self._generate_general_resolution(issue_description, metadata)
                
        except Exception as e:
            logger.error(f"Error in fallback resolution: {e}")
            return "I apologize, but I'm unable to generate a specific resolution at this time. Please contact your IT support team for assistance."
    
    def _generate_login_resolution(self) -> str:
        """Generate resolution for login/authentication issues."""
        return """🔐 **Login Issue Resolution**

## Step-by-Step Solution:

1. **Clear Browser Cache** - Open browser settings → Privacy → Clear browsing data
2. **Check Caps Lock** - Ensure Caps Lock is off when entering password
3. **Reset Password** - Use "Forgot Password" link if available
4. **Try Different Browser** - Test with Chrome, Firefox, or Edge
5. **Check Network** - Ensure stable internet connection
6. **Contact IT Support** - If issues persist, contact your IT team

## Verification:
You should be able to log in successfully after following these steps.

## Alternative Solutions:
- Try logging in from a different device
- Check if your account is locked due to multiple failed attempts
- Verify your username format (email vs username)"""

    def _generate_network_resolution(self) -> str:
        """Generate resolution for network issues."""
        return """🌐 **Network Issue Resolution**

## Step-by-Step Solution:

1. **Check Physical Connection** - Ensure cables are properly connected
2. **Restart Router/Modem** - Unplug for 30 seconds, then reconnect
3. **Run Network Troubleshooter** - Windows: Settings → Network → Troubleshoot
4. **Flush DNS** - Open Command Prompt as admin: `ipconfig /flushdns`
5. **Check Firewall** - Ensure firewall isn't blocking the connection
6. **Test Different Network** - Try connecting to mobile hotspot

## Verification:
You should have stable internet connection and be able to access websites.

## Alternative Solutions:
- Update network drivers
- Check for Windows updates
- Contact your ISP if issues persist"""

    def _generate_printer_resolution(self) -> str:
        """Generate resolution for printer issues."""
        return """🖨️ **Printer Issue Resolution**

## Step-by-Step Solution:

1. **Check Power & Cables** - Ensure printer is powered on and connected
2. **Clear Print Queue** - Open Printers & Scanners → Select printer → Open queue → Cancel all jobs
3. **Restart Printer** - Turn off printer, wait 30 seconds, turn back on
4. **Check Paper & Ink** - Ensure paper is loaded and ink cartridges are not empty
5. **Reinstall Printer Driver** - Remove printer from devices, reinstall driver
6. **Test Print** - Try printing a test page

## Verification:
Printer should respond to commands and print documents successfully.

## Alternative Solutions:
- Try printing from different application
- Check printer settings for correct paper size
- Update printer firmware"""

    def _generate_performance_resolution(self) -> str:
        """Generate resolution for performance issues."""
        return """⚡ **Performance Issue Resolution**

## Step-by-Step Solution:

1. **Restart Computer** - Save work and restart to clear memory
2. **Close Unnecessary Programs** - End tasks using Task Manager
3. **Check Disk Space** - Ensure at least 10GB free space on C: drive
4. **Run Disk Cleanup** - Windows: Disk Cleanup → Clean up system files
5. **Update Drivers** - Check for graphics, network, and chipset driver updates
6. **Scan for Malware** - Run Windows Defender or antivirus scan

## Verification:
Computer should respond faster and applications should load more quickly.

## Alternative Solutions:
- Increase virtual memory
- Upgrade RAM if possible
- Consider SSD upgrade for better performance"""

    def _generate_installation_resolution(self) -> str:
        """Generate resolution for installation issues."""
        return """📦 **Installation Issue Resolution**

## Step-by-Step Solution:

1. **Run as Administrator** - Right-click installer → Run as administrator
2. **Check System Requirements** - Verify your system meets minimum requirements
3. **Disable Antivirus** - Temporarily disable antivirus during installation
4. **Clear Temp Files** - Delete files in %temp% folder
5. **Check Disk Space** - Ensure sufficient free space (at least 2GB)
6. **Download Fresh Copy** - Re-download installer from official source

## Verification:
Software should install successfully without errors.

## Alternative Solutions:
- Try installing in Safe Mode
- Use compatibility mode for older software
- Contact software vendor for support"""

    def _generate_general_resolution(self, issue_description: str, metadata: Dict = None) -> str:
        """Generate general resolution for unknown issues."""
        return f"""🔧 **General Issue Resolution**

## Step-by-Step Solution:

1. **Restart the Application** - Close and reopen the program
2. **Restart Computer** - Save work and restart to clear any temporary issues
3. **Check for Updates** - Update the application and your operating system
4. **Clear Cache/Data** - Clear application cache and temporary files
5. **Check Permissions** - Ensure you have necessary permissions
6. **Contact Support** - If issues persist, contact IT support

## Issue Details:
{issue_description}

## Verification:
The issue should be resolved after following these steps.

## Alternative Solutions:
- Try using the application on a different device
- Check if others are experiencing similar issues
- Review application documentation or help files"""

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
