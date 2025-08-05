"""Conversational chatbot service with ticket caching and similar ticket recommendations."""

import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from ..database import TechnicianDummyData, Ticket
from ..models import ChatResponse, TicketResponse
import json

logger = logging.getLogger(__name__)


class TicketCache:
    """In-memory cache for technician tickets and similar tickets."""
    
    def __init__(self):
        self.technician_tickets = {}  # technician_id -> {tickets, timestamp}
        self.similar_tickets_cache = {}  # cache_key -> {tickets, timestamp}
        self.cache_duration = timedelta(minutes=30)  # Cache for 30 minutes
    
    def get_technician_tickets(self, technician_id: str) -> Optional[List[Ticket]]:
        """Get cached tickets for a technician."""
        if technician_id in self.technician_tickets:
            cache_entry = self.technician_tickets[technician_id]
            if datetime.utcnow() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['tickets']
        return None
    
    def cache_technician_tickets(self, technician_id: str, tickets: List[Ticket]):
        """Cache tickets for a technician."""
        self.technician_tickets[technician_id] = {
            'tickets': tickets,
            'timestamp': datetime.utcnow()
        }
    
    def get_similar_tickets(self, cache_key: str) -> Optional[List[Ticket]]:
        """Get cached similar tickets."""
        if cache_key in self.similar_tickets_cache:
            cache_entry = self.similar_tickets_cache[cache_key]
            if datetime.utcnow() - cache_entry['timestamp'] < self.cache_duration:
                return cache_entry['tickets']
        return None
    
    def cache_similar_tickets(self, cache_key: str, tickets: List[Ticket]):
        """Cache similar tickets."""
        self.similar_tickets_cache[cache_key] = {
            'tickets': tickets,
            'timestamp': datetime.utcnow()
        }


class ConversationalChatbotService:
    """Conversational chatbot with ticket caching and recommendations."""
    
    def __init__(self, db: Session, llm_service=None):
        self.db = db
        self.llm_service = llm_service
        self.ticket_cache = TicketCache()
        
        # Conversation history storage
        self.conversation_history = {}  # session_id -> list of messages
        self.conversation_context = {}  # session_id -> current context
    
    def process_message(
        self,
        message: str,
        technician: TechnicianDummyData,
        session_id: Optional[str] = None
    ) -> ChatResponse:
        """Process incoming chat message and generate conversational response."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        try:
            # Check if this is a follow-up conversation
            conversation_context = self._get_conversation_context(session_id)
            conversation_history = self._get_conversation_history(session_id)
            
            if conversation_context and self._is_followup_message(message, conversation_context):
                response = self._handle_conversational_followup(
                    message, conversation_context, conversation_history, technician, session_id
                )
            else:
                # Process as new conversation
                intent, entities = self._analyze_message(message)
                response = self._generate_response(intent, entities, technician, message, session_id)
            
            # Add to conversation history
            self._add_to_conversation_history(session_id, message, response.response)
            
            response.session_id = session_id
            response.timestamp = datetime.utcnow()
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return self._create_response(
                "I'm sorry, I encountered an error. Please try again.",
                session_id=session_id
            )
    
    def _create_response(self, response: str, session_id: str = "", **kwargs) -> ChatResponse:
        """Helper method to create ChatResponse."""
        return ChatResponse(
            response=response,
            message_type="bot",
            timestamp=datetime.utcnow(),
            session_id=session_id,
            **kwargs
        )
    
    def _add_to_conversation_history(self, session_id: str, user_message: str, bot_response: str):
        """Add messages to conversation history."""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].extend([
            f"User: {user_message}",
            f"Bot: {bot_response[:200]}..."
        ])
        
        # Keep only last 10 exchanges
        if len(self.conversation_history[session_id]) > 20:
            self.conversation_history[session_id] = self.conversation_history[session_id][-20:]
    
    def _get_conversation_history(self, session_id: str) -> List[str]:
        """Get conversation history for a session."""
        return self.conversation_history.get(session_id, [])
    
    def _set_conversation_context(self, session_id: str, context_type: str, data: Dict):
        """Set conversation context."""
        self.conversation_context[session_id] = {
            'type': context_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_conversation_context(self, session_id: str) -> Dict:
        """Get conversation context."""
        return self.conversation_context.get(session_id, {})
    
    def _is_followup_message(self, message: str, conversation_context: Dict) -> bool:
        """Determine if this is a follow-up message."""
        if not conversation_context:
            return False
        
        message_lower = message.lower()
        followup_indicators = [
            'yes', 'no', 'thanks', 'thank you', 'that worked', 'that didn\'t work',
            'still not working', 'tried that', 'what else', 'anything else',
            'more details', 'tell me more', 'show me', 'explain'
        ]
        
        return any(indicator in message_lower for indicator in followup_indicators)
    
    def _analyze_message(self, message: str) -> Tuple[str, Dict]:
        """Analyze message to determine intent and extract entities with enhanced NLP."""
        message_lower = message.lower().strip()
        
        # Initialize entities
        entities = {
            'query': '',
            'ticket_number': None,
            'issue_type': None,
            'urgency': None
        }
        
        # Check for ticket number patterns (e.g., T20250804.0001, T2025.0001, etc.)
        ticket_patterns = [
            r'T\d{8}\.\d{4}',  # T20250804.0001
            r'T\d{4}\.\d{4}',  # T2025.0001
            r'T\d{6}\.\d{4}',  # T202504.0001
            r'T\d{7}\.\d{4}',  # T2025040.0001
        ]
        
        for pattern in ticket_patterns:
            import re
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                entities['ticket_number'] = match.group()
                break
        
        # Intent classification with enhanced patterns
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return 'greeting', entities
        
        elif any(word in message_lower for word in ['my tickets', 'show my tickets', 'my assigned tickets', 'tickets assigned to me']):
            return 'show_my_tickets', entities
        
        elif any(word in message_lower for word in ['ai resolution', 'ai help', 'ai support', 'artificial intelligence', 'ai assistance']):
            # Extract the actual query after AI resolution keywords
            ai_keywords = ['ai resolution', 'ai help', 'ai support', 'artificial intelligence', 'ai assistance']
            query_start = message_lower
            for keyword in ai_keywords:
                if keyword in message_lower:
                    query_start = message_lower.split(keyword, 1)[1].strip()
                    break
            
            # Clean up the query by removing leading colon and spaces
            if query_start.startswith(':'):
                query_start = query_start[1:].strip()
            
            if query_start:
                entities['query'] = query_start
            return 'ai_resolution', entities
        
        elif any(word in message_lower for word in ['similar tickets', 'find similar', 'similar to', 'like this', 'same issue', 'find similar ticket']):
            # Extract query for similar tickets
            similar_keywords = ['similar tickets', 'find similar', 'similar to', 'like this', 'same issue', 'find similar ticket']
            query_start = message_lower
            for keyword in similar_keywords:
                if keyword in message_lower:
                    query_start = message_lower.split(keyword, 1)[1].strip()
                    break
            
            # Clean up the query by removing leading "to " and spaces
            if query_start.startswith('to '):
                query_start = query_start[3:].strip()
            
            if query_start:
                entities['query'] = query_start
            return 'find_similar_tickets', entities
        
        elif any(word in message_lower for word in ['resolution', 'solution', 'how to fix', 'how to resolve', 'troubleshoot']):
            # Extract the issue description
            resolution_keywords = ['resolution', 'solution', 'how to fix', 'how to resolve', 'troubleshoot']
            query_start = message_lower
            for keyword in resolution_keywords:
                if keyword in message_lower:
                    query_start = message_lower.split(keyword, 1)[1].strip()
                    break
            
            if query_start:
                entities['query'] = query_start
            return 'get_resolution', entities
        
        elif entities['ticket_number'] or any(word in message_lower for word in ['ticket', 'issue', 'problem', 'bug']):
            # If we found a ticket number or ticket-related keywords, treat as ticket info request
            if not entities['ticket_number']:
                # Extract ticket-related query
                ticket_keywords = ['ticket', 'issue', 'problem', 'bug']
                query_start = message_lower
                for keyword in ticket_keywords:
                    if keyword in message_lower:
                        query_start = message_lower.split(keyword, 1)[1].strip()
                        break
                
                if query_start:
                    entities['query'] = query_start
            
            return 'ticket_info', entities
        
        else:
            # Default to general query
            entities['query'] = message
            return 'general_query', entities
    
    def _generate_response(
        self,
        intent: str,
        entities: Dict,
        technician: TechnicianDummyData,
        original_message: str,
        session_id: str
    ) -> ChatResponse:
        """Generate response based on intent."""
        
        if intent == "greeting":
            return self._handle_greeting(technician, session_id)
        elif intent == "show_my_tickets":
            return self._handle_show_my_tickets(technician, session_id)
        elif intent == "find_similar_tickets":
            return self._handle_find_similar_tickets(entities, technician, session_id)
        elif intent == "ai_resolution":
            return self._handle_ai_resolution(entities, technician, session_id)
        elif intent == "get_resolution":
            return self._handle_get_resolution(entities, technician, session_id)
        elif intent == "ticket_info":
            return self._handle_ticket_info(entities, technician, session_id)
        else:
            return self._handle_general_query(entities, technician, session_id)
    
    def _handle_greeting(self, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle greeting with personalized response."""
        # Get recent tickets count
        recent_tickets = self._get_technician_recent_tickets(technician.technician_id)
        ticket_count = len(recent_tickets)
        
        greeting = f"Hello {technician.name}! 👋\n\n"
        
        if ticket_count > 0:
            greeting += f"You have {ticket_count} recent tickets to work on.\n\n"
        else:
            greeting += "You're all caught up with your tickets! 🎉\n\n"
        
        greeting += """I can help you with:
• 📋 Show your recent tickets
• 🔍 Find similar tickets for any issue
• 💡 Get AI-powered resolutions for problems
• 🎫 Get details about specific tickets

What would you like to do today?"""
        
        return self._create_response(greeting, session_id=session_id)
    
    def _handle_show_my_tickets(self, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Show technician's recent tickets with 4 cards."""
        logger.info(f"Fetching tickets for technician: {technician.technician_id} (email: {technician.email})")

        # Try both technician_id and email for ticket lookup
        tickets = self._get_technician_recent_tickets(technician.email or technician.technician_id, limit=4)

        if not tickets:
            # Also try with technician_id if email didn't work
            if technician.email != technician.technician_id:
                tickets = self._get_technician_recent_tickets(technician.technician_id, limit=4)

        if not tickets:
            return self._create_response(
                f"You don't have any recent tickets assigned to {technician.email or technician.technician_id}. Great job staying on top of things! 🎉\n\n💡 If you expect to see tickets, please check that your email matches the TECHNICIANEMAIL field in the database.",
                session_id=session_id
            )

        # Create ticket cards
        ticket_responses = [TicketResponse.from_orm(ticket) for ticket in tickets]

        response_text = f"## 📋 Your Recent Tickets ({len(tickets)} cards)\n"
        response_text += f"**Assigned to:** {technician.email or technician.technician_id}\n\n"

        for i, ticket in enumerate(tickets, 1):
            status_emoji = "✅" if ticket.status == "resolved" else "🔄" if ticket.status == "in_progress" else "🆕"
            priority_emoji = "🔴" if ticket.priority == "high" else "🟡" if ticket.priority == "medium" else "🟢"

            response_text += f"""**Card {i}: {ticket.ticketnumber}** {status_emoji}
📝 **Title:** {ticket.title}
🏷️ **Type:** {ticket.issuetype}
{priority_emoji} **Priority:** {ticket.priority}
📧 **User:** {ticket.useremail}
📅 **Due:** {ticket.duedatetime or 'Not set'}
🎯 **Status:** {ticket.status}

"""

        response_text += "\n💬 Ask me about any specific ticket or say 'find similar tickets' to get recommendations!"

        # Set context for follow-up
        self._set_conversation_context(session_id, "ticket_list", {"tickets": [t.ticketnumber for t in tickets]})

        return self._create_response(
            response_text,
            session_id=session_id,
            related_tickets=ticket_responses
        )

    def _handle_ai_resolution(self, entities: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle AI resolution requests with enhanced LLM integration and ticket references."""
        try:
            query = entities.get('query', '').strip()
            
            if not query:
                return self._create_response(
                    "I'd be happy to help you with AI-powered resolution! Please describe the technical issue you're experiencing. "
                    "For example: 'My computer is running slow' or 'I can't connect to the printer'",
                    session_id,
                    message_type="clarification"
                )
            
            # Find similar tickets for context
            similar_tickets = self._find_similar_tickets_by_query(query, limit=3)
            
            # Extract metadata from the query
            metadata = self._extract_query_metadata(query)
            
            # Generate AI resolution using LLM service
            if self.llm_service and hasattr(self.llm_service, 'generate_resolution_for_issue'):
                try:
                    resolution = self.llm_service.generate_resolution_for_issue(
                        query, 
                        similar_tickets=similar_tickets, 
                        metadata=metadata
                    )
                except Exception as llm_error:
                    logger.warning(f"LLM service failed, using fallback: {llm_error}")
                    resolution = self._generate_ai_resolution_fallback(query, similar_tickets, metadata)
            else:
                resolution = self._generate_ai_resolution_fallback(query, similar_tickets, metadata)
            
            # Create response with ticket references
            response_text = f"🤖 **AI Resolution for: {query}**\n\n"
            response_text += resolution
            
            # Add similar tickets context if available
            if similar_tickets:
                response_text += f"\n\n📋 **Similar Historical Tickets:**\n"
                for i, ticket in enumerate(similar_tickets[:3], 1):
                    response_text += f"{i}. **{ticket.ticketnumber}** - {ticket.title}\n"
                    if ticket.resolution:
                        response_text += f"   Resolution: {ticket.resolution[:150]}...\n"
                    response_text += "\n"
            
            response_text += "\n💡 **Need more help?** Ask me to find more similar tickets or get specific details about any ticket mentioned above."
            
            # Set context for follow-up questions
            self._set_conversation_context(session_id, "ai_resolution", {
                "original_query": query,
                "similar_tickets": [t.ticketnumber for t in similar_tickets],
                "metadata": metadata
            })
            
            return self._create_response(
                response_text,
                session_id,
                related_tickets=similar_tickets
            )
            
        except Exception as e:
            logger.error(f"Error in _handle_ai_resolution: {e}")
            return self._create_response(
                "I encountered an error while generating the AI resolution. Please try again or contact support.",
                session_id,
                message_type="error"
            )

    def _handle_find_similar_tickets(self, entities: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle finding similar tickets with enhanced NLP/NLU capabilities."""
        try:
            # Check if user provided a specific ticket number
            ticket_number = entities.get('ticket_number')
            
            if ticket_number:
                # User provided a specific ticket number
                original_ticket = self._get_ticket_by_number(ticket_number)
                if not original_ticket:
                    return self._create_response(
                        f"I couldn't find ticket {ticket_number}. Please check the ticket number and try again.",
                        session_id,
                        message_type="error"
                    )
                
                # Find similar tickets based on the original ticket
                similar_tickets = self._find_similar_tickets_from_db(
                    [original_ticket.title or "", original_ticket.description or "", original_ticket.issuetype or ""],
                    technician.technician_id,
                    limit=5
                )
                
                if similar_tickets:
                    response_text = f"Here are similar tickets to {ticket_number}:\n\n"
                    for i, ticket in enumerate(similar_tickets[:5], 1):
                        response_text += f"{i}. **{ticket.ticketnumber}** - {ticket.title}\n"
                        response_text += f"   Status: {ticket.status}\n"
                        response_text += f"   Issue: {ticket.issuetype or 'N/A'}\n"
                        if ticket.resolution and ticket.resolution.strip():
                            response_text += f"   Resolution: {ticket.resolution[:150]}...\n"
                        response_text += "\n"
                    
                    response_text += f"Found {len(similar_tickets)} similar tickets based on ticket {ticket_number}.\n\n"
                    response_text += "💡 **Strong Similar Tickets with Resolutions:**\n"
                    
                    # Show resolved tickets with resolutions
                    resolved_tickets = [t for t in similar_tickets if t.resolution and t.resolution.strip()]
                    if resolved_tickets:
                        for i, ticket in enumerate(resolved_tickets[:3], 1):
                            response_text += f"   • **{ticket.ticketnumber}** - {ticket.title}\n"
                            response_text += f"     Resolution: {ticket.resolution[:200]}...\n\n"
                    else:
                        response_text += "   No resolved tickets with resolutions found.\n\n"
                else:
                    response_text = f"No similar tickets found for {ticket_number}. This might be a unique issue."
                
                return self._create_response(response_text, session_id, related_tickets=similar_tickets)
            
            else:
                # User provided a natural language query
                query = entities.get('query', '')
                if not query:
                    return self._create_response(
                        "I can help you find similar tickets! Please provide either:\n"
                        "1. A specific ticket number (e.g., 'T20250804.0001')\n"
                        "2. A description of the issue you're looking for (e.g., 'network connectivity problems')",
                        session_id,
                        message_type="clarification"
                    )
                
                # Use NLP/NLU to find similar tickets based on natural language
                similar_tickets = self._find_similar_tickets_by_query(query, limit=5)
                
                if similar_tickets:
                    response_text = f"Here are tickets similar to your query '{query}':\n\n"
                    for i, ticket in enumerate(similar_tickets[:5], 1):
                        response_text += f"{i}. **{ticket.ticketnumber}** - {ticket.title}\n"
                        response_text += f"   Status: {ticket.status}\n"
                        response_text += f"   Issue: {ticket.issuetype or 'N/A'}\n"
                        if ticket.resolution and ticket.resolution.strip():
                            response_text += f"   Resolution: {ticket.resolution[:150]}...\n"
                        response_text += "\n"
                    
                    response_text += f"Found {len(similar_tickets)} tickets matching your query.\n\n"
                    response_text += "💡 **Strong Similar Tickets with Resolutions:**\n"
                    
                    # Show resolved tickets with resolutions
                    resolved_tickets = [t for t in similar_tickets if t.resolution and t.resolution.strip()]
                    if resolved_tickets:
                        for i, ticket in enumerate(resolved_tickets[:3], 1):
                            response_text += f"   • **{ticket.ticketnumber}** - {ticket.title}\n"
                            response_text += f"     Resolution: {ticket.resolution[:200]}...\n\n"
                    else:
                        response_text += "   No resolved tickets with resolutions found.\n\n"
                else:
                    response_text = f"No tickets found matching '{query}'. Try using different keywords or a specific ticket number."
                
                return self._create_response(response_text, session_id, related_tickets=similar_tickets)
                
        except Exception as e:
            logger.error(f"Error in _handle_find_similar_tickets: {e}")
            return self._create_response(
                "I encountered an error while searching for similar tickets. Please try again or contact support.",
                session_id,
                message_type="error"
            )

    def _handle_get_resolution(self, entities: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Get AI-powered resolution using Cortex Complete."""
        query = entities.get('query', '')

        if not query or len(query.strip()) < 10:
            return self._create_response(
                "Please describe the specific problem you need help resolving.",
                session_id=session_id
            )

        # Clean the query
        clean_query = self._clean_resolution_query(query)

        # Find similar resolved tickets for context using enhanced search
        similar_tickets = self._find_similar_tickets_by_query(clean_query, limit=5)

        # Extract metadata for better resolution generation
        metadata = self._extract_query_metadata(clean_query)

        # Generate resolution using LLM with metadata
        try:
            if self.llm_service and hasattr(self.llm_service, 'generate_resolution_for_issue'):
                resolution = self.llm_service.generate_resolution_for_issue(clean_query, similar_tickets, metadata)
            else:
                resolution = self._generate_fallback_resolution(clean_query, similar_tickets, metadata)
        except Exception as e:
            logger.error(f"Error generating resolution: {e}")
            resolution = self._generate_fallback_resolution(clean_query, similar_tickets, metadata)

        # Set context for follow-up
        self._set_conversation_context(session_id, "resolution", {
            "issue": clean_query,
            "similar_tickets": [t.ticketnumber for t in similar_tickets] if similar_tickets else []
        })

        return self._create_response(resolution, session_id=session_id)

    def _handle_ticket_info(self, entities: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Get detailed information about a specific ticket."""
        ticket_id = entities.get('ticket_id')

        if not ticket_id:
            return self._create_response(
                "Please specify a ticket number (e.g., T20250723.0001 or TKN-123).",
                session_id=session_id
            )

        # Find ticket in database
        ticket = self._get_ticket_by_number(ticket_id)

        if not ticket:
            return self._create_response(
                f"I couldn't find ticket '{ticket_id}'. Please check the ticket number.",
                session_id=session_id
            )

        # Create detailed ticket information
        ticket_response = TicketResponse.from_orm(ticket)

        status_emoji = "✅" if ticket.status == "resolved" else "🔄"
        priority_emoji = "🔴" if ticket.priority == "high" else "🟡"

        response_text = f"""## 🎫 Ticket Details {status_emoji}

**{ticket.ticket_number}**
📝 **Title:** {ticket.title}
🏷️ **Type:** {ticket.issuetype} / {ticket.subissuetype or 'N/A'}
{priority_emoji} **Priority:** {ticket.priority}
📧 **User:** {ticket.useremail}
👤 **Assigned to:** {ticket.technicianemail}
📅 **Due Date:** {ticket.duedatetime or 'Not set'}

**Description:**
{ticket.description}
"""

        if ticket.resolution:
            response_text += f"\n**Resolution:**\n{ticket.resolution}"
        else:
            response_text += "\n❓ **Status:** No resolution yet - still open"

        response_text += "\n\n💬 Need help with this ticket? Ask me for a resolution or similar tickets!"

        # Set context for follow-up
        self._set_conversation_context(session_id, "ticket_details", {"ticket_id": ticket.ticketnumber})

        return self._create_response(
            response_text,
            session_id=session_id,
            related_tickets=[ticket_response]
        )

    def _handle_general_query(self, entities: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle general queries with conversational response."""
        query = entities.get('query', '')

        if not query:
            return self._create_response(
                "I'm here to help! You can ask me about your tickets, find similar tickets, or get resolutions for technical issues.",
                session_id=session_id
            )

        # Try to generate a helpful response using LLM
        try:
            if self.llm_service and hasattr(self.llm_service, 'generate_conversational_response'):
                response_text = self.llm_service.generate_conversational_response("general_query", query, [])
            else:
                response_text = self._generate_general_fallback(query)
        except Exception as e:
            logger.error(f"Error generating general response: {e}")
            response_text = self._generate_general_fallback(query)

        return self._create_response(response_text, session_id=session_id)

    def _handle_conversational_followup(
        self,
        message: str,
        conversation_context: Dict,
        conversation_history: List[str],
        technician: TechnicianDummyData,
        session_id: str
    ) -> ChatResponse:
        """Handle follow-up messages in ongoing conversation."""
        context_type = conversation_context.get('type', '')
        context_data = conversation_context.get('data', {})

        if context_type == "ticket_list":
            return self._handle_ticket_list_followup(message, context_data, technician, session_id)
        elif context_type == "similar_tickets":
            return self._handle_similar_tickets_followup(message, context_data, technician, session_id)
        elif context_type == "resolution":
            return self._handle_resolution_followup(message, context_data, conversation_history, technician, session_id)
        elif context_type == "ai_resolution":
            return self._handle_ai_resolution_followup(message, context_data, conversation_history, technician, session_id)
        elif context_type == "ticket_details":
            return self._handle_ticket_details_followup(message, context_data, technician, session_id)
        else:
            # General conversational follow-up
            try:
                if self.llm_service and hasattr(self.llm_service, 'generate_conversational_response'):
                    response_text = self.llm_service.generate_conversational_response(
                        "general_followup", message, conversation_history
                    )
                else:
                    response_text = "I understand you're following up. Could you please be more specific about what you'd like to know?"
            except Exception as e:
                logger.error(f"Error in conversational followup: {e}")
                response_text = "I understand you're following up. Could you please be more specific about what you'd like to know?"

            return self._create_response(response_text, session_id=session_id)

    def _handle_ticket_list_followup(self, message: str, context_data: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle follow-up after showing ticket list."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['more', 'details', 'tell me about']):
            # Extract ticket number if mentioned
            ticket_numbers = context_data.get('tickets', [])
            for ticket_num in ticket_numbers:
                if ticket_num.lower() in message_lower:
                    return self._handle_ticket_info({'ticket_id': ticket_num}, technician, session_id)

            return self._create_response(
                "Which ticket would you like more details about? Please mention the ticket number.",
                session_id=session_id
            )

        elif any(word in message_lower for word in ['similar', 'related']):
            return self._create_response(
                "Please describe the issue you'd like me to find similar tickets for.",
                session_id=session_id
            )

        else:
            return self._create_response(
                "I can help you with:\n• Get details about any specific ticket\n• Find similar tickets for an issue\n• Get resolution help\n\nWhat would you like to do?",
                session_id=session_id
            )

    def _handle_similar_tickets_followup(self, message: str, context_data: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle follow-up after showing similar tickets."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['resolution', 'solve', 'fix', 'help']):
            original_query = context_data.get('query', '')
            return self._handle_get_resolution({'query': original_query}, technician, session_id)

        elif any(word in message_lower for word in ['details', 'more info']):
            ticket_numbers = context_data.get('tickets', [])
            for ticket_num in ticket_numbers:
                if ticket_num.lower() in message_lower:
                    return self._handle_ticket_info({'ticket_id': ticket_num}, technician, session_id)

            return self._create_response(
                "Which ticket would you like more details about? Please mention the ticket number.",
                session_id=session_id
            )

        else:
            return self._create_response(
                "I can help you:\n• Get a resolution for the original issue\n• Show details about any specific ticket\n• Find more similar tickets\n\nWhat would you like to do?",
                session_id=session_id
            )

    def _handle_resolution_followup(self, message: str, context_data: Dict, conversation_history: List[str], technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle follow-up after providing a resolution."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['worked', 'fixed', 'solved', 'thanks', 'thank you']):
            return self._create_response(
                "Great! I'm glad the resolution worked for you! 🎉\n\nIs there anything else I can help you with today?",
                session_id=session_id
            )

        elif any(word in message_lower for word in ['didn\'t work', 'not working', 'still broken', 'error']):
            original_issue = context_data.get('issue', '')
            try:
                if self.llm_service and hasattr(self.llm_service, 'generate_conversational_response'):
                    response_text = self.llm_service.generate_conversational_response(
                        original_issue, message, conversation_history
                    )
                else:
                    response_text = f"I understand the previous solution didn't work. Let me try a different approach for: {original_issue}\n\nCan you tell me:\n• What exactly happened when you tried the solution?\n• Any error messages you saw?\n• What step didn't work?"
            except Exception as e:
                logger.error(f"Error generating resolution followup: {e}")
                response_text = "Let me help you troubleshoot further. Can you describe what happened when you tried the solution?"

            return self._create_response(response_text, session_id=session_id)

        else:
            return self._create_response(
                "How did the resolution work for you? Let me know if you need any clarification or if you encountered any issues.",
                session_id=session_id
            )

    def _handle_ticket_details_followup(self, message: str, context_data: Dict, technician: TechnicianDummyData, session_id: str) -> ChatResponse:
        """Handle follow-up after showing ticket details."""
        message_lower = message.lower()
        ticket_id = context_data.get('ticket_id', '')

        if any(word in message_lower for word in ['resolution', 'solve', 'fix', 'help']):
            # Get the ticket to extract the issue
            ticket = self._get_ticket_by_number(ticket_id)
            if ticket:
                issue_description = f"{ticket.title}: {ticket.description}"
                return self._handle_get_resolution({'query': issue_description}, technician, session_id)
            else:
                return self._create_response(
                    "Please describe the issue you need help resolving.",
                    session_id=session_id
                )

        elif any(word in message_lower for word in ['similar', 'related']):
            ticket = self._get_ticket_by_number(ticket_id)
            if ticket:
                issue_description = f"{ticket.title}: {ticket.description}"
                return self._handle_find_similar_tickets({'query': issue_description}, technician, session_id)
            else:
                return self._create_response(
                    "Please describe the issue you'd like me to find similar tickets for.",
                    session_id=session_id
                )

        else:
            return self._create_response(
                "I can help you:\n• Get a resolution for this ticket's issue\n• Find similar tickets\n• Show other ticket details\n\nWhat would you like to do?",
                session_id=session_id
            )

    # Database and utility methods
    def _get_technician_recent_tickets(self, technician_id: str, limit: int = 10) -> List[Ticket]:
        """Get recent tickets for a technician with caching."""
        # Check cache first
        cached_tickets = self.ticket_cache.get_technician_tickets(technician_id)
        if cached_tickets:
            logger.info(f"Cache hit: Found {len(cached_tickets)} tickets for {technician_id}")
            return cached_tickets[:limit]

        # Query database
        try:
            logger.info(f"Querying database for tickets assigned to: {technician_id}")

            # Query tickets assigned to this technician
            tickets = self.db.query(Ticket).filter(
                Ticket.technicianemail == technician_id
            ).order_by(Ticket.ticketnumber.desc()).limit(limit * 2).all()

            logger.info(f"Found {len(tickets)} tickets for technician {technician_id}")

            # If no tickets found for exact email match, try partial match
            if not tickets:
                logger.info(f"No exact match found, trying partial match for: {technician_id}")
                tickets = self.db.query(Ticket).filter(
                    Ticket.technicianemail.ilike(f"%{technician_id}%")
                ).order_by(Ticket.ticketnumber.desc()).limit(limit * 2).all()
                logger.info(f"Partial match found {len(tickets)} tickets")

            # If still no tickets, get a sample of all tickets for demo purposes
            if not tickets:
                logger.info("No tickets found for technician, getting sample tickets for demo")
                tickets = self.db.query(Ticket).order_by(
                    Ticket.ticketnumber.desc()
                ).limit(limit).all()
                logger.info(f"Sample tickets retrieved: {len(tickets)}")

            # Cache the results
            self.ticket_cache.cache_technician_tickets(technician_id, tickets)

            return tickets[:limit]
        except Exception as e:
            logger.error(f"Error fetching technician tickets for {technician_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _get_ticket_by_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get a specific ticket by number."""
        try:
            return self.db.query(Ticket).filter(
                Ticket.ticketnumber.ilike(f"%{ticket_number}%")
            ).first()
        except Exception as e:
            logger.error(f"Error fetching ticket {ticket_number}: {e}")
            return None

    def _find_similar_tickets_from_db(self, keywords: List[str], technician_id: str, limit: int = 4) -> List[Ticket]:
        """Find similar tickets using semantic similarity from both TICKETS and COMPANY_4130_DATA tables."""
        if not keywords:
            return []

        try:
            # Combine keywords into search text
            search_text = " ".join(keywords)
            
            # Use raw SQL for semantic similarity search since SQLAlchemy doesn't support Snowflake Cortex functions
            # Get the engine directly for raw SQL execution
            from ..database import create_snowflake_engine
            engine = create_snowflake_engine()
            
            # Search in TICKETS table using semantic similarity
            tickets_query = f"""
                SELECT 
                    TICKETNUMBER,
                    TITLE,
                    DESCRIPTION,
                    STATUS,
                    PRIORITY,
                    TECHNICIANEMAIL,
                    ISSUETYPE,
                    SUBISSUETYPE,
                    RESOLUTION,
                    SNOWFLAKE.CORTEX.AI_SIMILARITY(
                        COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, ''),
                        '{search_text.replace("'", "''")}'
                    ) AS SIMILARITY_SCORE
                FROM TEST_DB.PUBLIC.TICKETS
                WHERE TITLE IS NOT NULL
                AND DESCRIPTION IS NOT NULL
                AND TRIM(TITLE) != ''
                AND TRIM(DESCRIPTION) != ''
                AND LENGTH(TRIM(TITLE || ' ' || DESCRIPTION)) > 10
                ORDER BY SIMILARITY_SCORE DESC
                LIMIT {limit}
            """
            
            # Search in COMPANY_4130_DATA table using semantic similarity
            # Note: Using only the columns that exist in COMPANY_4130_DATA table
            company_query = f"""
                SELECT 
                    TICKETNUMBER,
                    TITLE,
                    DESCRIPTION,
                    STATUS,
                    PRIORITY,
                    ISSUETYPE,
                    SUBISSUETYPE,
                    RESOLUTION,
                    SNOWFLAKE.CORTEX.AI_SIMILARITY(
                        COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, ''),
                        '{search_text.replace("'", "''")}'
                    ) AS SIMILARITY_SCORE
                FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
                WHERE TITLE IS NOT NULL
                AND DESCRIPTION IS NOT NULL
                AND TRIM(TITLE) != ''
                AND TRIM(DESCRIPTION) != ''
                AND LENGTH(TRIM(TITLE || ' ' || DESCRIPTION)) > 10
                ORDER BY SIMILARITY_SCORE DESC
                LIMIT {limit}
            """
            
            # Execute queries using raw SQL
            from sqlalchemy import text
            with engine.connect() as connection:
                tickets_results = connection.execute(text(tickets_query)).fetchall()
                company_results = connection.execute(text(company_query)).fetchall()
                
            # Convert results to dictionaries for easier access
            tickets_dicts = [dict(row._mapping) for row in tickets_results]
            company_dicts = [dict(row._mapping) for row in company_results]
            
            # Combine and sort results by similarity score
            all_results = []
            
            # Process TICKETS results
            for row in tickets_dicts:
                score = row.get('SIMILARITY_SCORE', 0)
                if isinstance(score, (int, float)) and score >= 0.1:  # Minimum similarity threshold
                    # Create Ticket object from row
                    ticket = Ticket(
                        ticketnumber=row.get('TICKETNUMBER'),
                        title=row.get('TITLE'),
                        description=row.get('DESCRIPTION'),
                        status=row.get('STATUS'),
                        priority=row.get('PRIORITY'),
                        technicianemail=row.get('TECHNICIANEMAIL'),
                        issuetype=row.get('ISSUETYPE'),
                        subissuetype=row.get('SUBISSUETYPE'),
                        resolution=row.get('RESOLUTION')
                    )
                    all_results.append((ticket, score, 'TICKETS'))
            
            # Process COMPANY_4130_DATA results
            for row in company_dicts:
                score = row.get('SIMILARITY_SCORE', 0)
                if isinstance(score, (int, float)) and score >= 0.1:  # Minimum similarity threshold
                    # Create Ticket object from row (using same model for compatibility)
                    ticket = Ticket(
                        ticketnumber=row.get('TICKETNUMBER'),
                        title=row.get('TITLE'),
                        description=f"[Source: COMPANY_4130_DATA] {row.get('DESCRIPTION', '')}",
                        status=row.get('STATUS'),
                        priority=row.get('PRIORITY'),
                        technicianemail=None,  # COMPANY_4130_DATA doesn't have this column
                        issuetype=row.get('ISSUETYPE'),
                        subissuetype=row.get('SUBISSUETYPE'),
                        resolution=row.get('RESOLUTION')
                    )
                    all_results.append((ticket, score, 'COMPANY_4130_DATA'))
            
            # Sort by similarity score (highest first)
            all_results.sort(key=lambda x: x[1], reverse=True)
            
            # Return top tickets
            return [ticket for ticket, score, source in all_results[:limit]]

        except Exception as e:
            logger.error(f"Error finding similar tickets: {e}")
            # Fallback to keyword-based search if semantic similarity fails
            return self._find_similar_tickets_fallback(keywords, technician_id, limit)

    def _find_similar_tickets_fallback(self, keywords: List[str], technician_id: str, limit: int = 4) -> List[Ticket]:
        """Fallback method for finding similar tickets using keyword-based search."""
        if not keywords:
            return []

        try:
            # Build search conditions with weighted scoring approach
            search_conditions = []
            for keyword in keywords:
                search_conditions.extend([
                    Ticket.title.ilike(f"%{keyword}%"),
                    Ticket.description.ilike(f"%{keyword}%"),
                    Ticket.issuetype.ilike(f"%{keyword}%"),
                    Ticket.subissuetype.ilike(f"%{keyword}%")
                ])

            # Query for similar tickets with preference for resolved ones
            tickets = self.db.query(Ticket).filter(
                or_(*search_conditions)
            ).filter(
                Ticket.resolution.isnot(None),  # Prefer resolved tickets
                Ticket.resolution != ""
            ).limit(limit * 2).all()  # Get more tickets for scoring

            # If not enough resolved tickets, get some unresolved ones too
            if len(tickets) < limit:
                unresolved_tickets = self.db.query(Ticket).filter(
                    or_(*search_conditions)
                ).filter(
                    or_(Ticket.resolution.is_(None), Ticket.resolution == "")
                ).limit(limit).all()
                tickets.extend(unresolved_tickets)

            # Score and rank tickets
            scored_tickets = self._score_ticket_similarity(tickets, keywords)

            # Return top scored tickets
            return [ticket for ticket, score in scored_tickets[:limit]]

        except Exception as e:
            logger.error(f"Error in fallback similar tickets search: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text with enhanced technical term recognition."""
        # Enhanced stop words list
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'cannot', 'help', 'please',
            'find', 'show', 'get', 'need', 'want', 'how', 'what', 'when', 'where', 'why', 'which',
            'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }

        # Technical terms that should always be preserved
        technical_terms = {
            'wifi', 'bluetooth', 'ethernet', 'vpn', 'dns', 'dhcp', 'ip', 'tcp', 'udp', 'http', 'https',
            'ssl', 'tls', 'cpu', 'gpu', 'ram', 'ssd', 'hdd', 'usb', 'hdmi', 'vga', 'dvi', 'displayport',
            'windows', 'macos', 'linux', 'android', 'ios', 'chrome', 'firefox', 'safari', 'edge',
            'outlook', 'excel', 'word', 'powerpoint', 'teams', 'zoom', 'skype', 'slack',
            'printer', 'scanner', 'monitor', 'keyboard', 'mouse', 'webcam', 'microphone', 'speaker',
            'server', 'database', 'backup', 'restore', 'update', 'install', 'uninstall', 'configure',
            'firewall', 'antivirus', 'malware', 'virus', 'spam', 'phishing', 'security', 'password',
            'login', 'logout', 'authentication', 'authorization', 'permissions', 'access', 'sync',
            'crash', 'freeze', 'hang', 'slow', 'lag', 'error', 'bug', 'issue', 'problem', 'failure'
        }

        # Clean and split text, preserving technical terms
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        # Extract keywords with priority for technical terms
        keywords = []
        for word in words:
            if len(word) > 2:
                if word in technical_terms:
                    keywords.append(word)  # Always include technical terms
                elif word not in stop_words:
                    keywords.append(word)

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        # Return most relevant keywords (increased limit for better matching)
        return unique_keywords[:8]

    def _extract_query_metadata(self, query: str) -> Dict[str, any]:
        """Extract structured metadata from technician query for better ticket matching."""
        metadata = {
            'keywords': [],
            'issue_type': None,
            'sub_issue_type': None,
            'urgency_indicators': [],
            'device_types': [],
            'software_mentioned': [],
            'error_indicators': [],
            'action_requested': None
        }

        query_lower = query.lower()

        # Extract keywords using enhanced method
        metadata['keywords'] = self._extract_keywords(query)

        # Detect issue types
        issue_type_patterns = {
            'hardware': ['hardware', 'device', 'computer', 'laptop', 'desktop', 'monitor', 'printer', 'scanner', 'keyboard', 'mouse', 'webcam', 'microphone', 'speaker', 'headset'],
            'software': ['software', 'application', 'app', 'program', 'outlook', 'excel', 'word', 'powerpoint', 'teams', 'zoom', 'chrome', 'firefox'],
            'network': ['network', 'internet', 'wifi', 'ethernet', 'vpn', 'connection', 'connectivity', 'dns', 'dhcp', 'ip'],
            'security': ['security', 'virus', 'malware', 'antivirus', 'firewall', 'password', 'login', 'authentication', 'phishing', 'spam'],
            'email': ['email', 'outlook', 'mail', 'inbox', 'send', 'receive', 'attachment', 'sync'],
            'performance': ['slow', 'lag', 'freeze', 'hang', 'crash', 'performance', 'speed', 'memory', 'cpu', 'disk']
        }

        for issue_type, patterns in issue_type_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                metadata['issue_type'] = issue_type
                break

        # Detect urgency indicators
        urgency_patterns = ['urgent', 'critical', 'emergency', 'asap', 'immediately', 'broken', 'down', 'not working', 'failed', 'crashed']
        metadata['urgency_indicators'] = [pattern for pattern in urgency_patterns if pattern in query_lower]

        # Detect device types
        device_patterns = ['laptop', 'desktop', 'computer', 'pc', 'mac', 'iphone', 'android', 'tablet', 'ipad', 'monitor', 'printer', 'scanner']
        metadata['device_types'] = [device for device in device_patterns if device in query_lower]

        # Detect software mentioned
        software_patterns = ['outlook', 'excel', 'word', 'powerpoint', 'teams', 'zoom', 'skype', 'chrome', 'firefox', 'safari', 'edge']
        metadata['software_mentioned'] = [software for software in software_patterns if software in query_lower]

        # Detect error indicators
        error_patterns = ['error', 'bug', 'issue', 'problem', 'failure', 'exception', 'crash', 'freeze', 'hang', 'not working', 'broken']
        metadata['error_indicators'] = [error for error in error_patterns if error in query_lower]

        # Detect action requested
        action_patterns = {
            'troubleshoot': ['fix', 'solve', 'resolve', 'troubleshoot', 'repair'],
            'install': ['install', 'setup', 'configure', 'deploy'],
            'update': ['update', 'upgrade', 'patch'],
            'reset': ['reset', 'restart', 'reboot', 'refresh'],
            'backup': ['backup', 'restore', 'recover'],
            'help': ['help', 'assist', 'support', 'guide', 'how to']
        }

        for action, patterns in action_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                metadata['action_requested'] = action
                break

        return metadata

    def _score_ticket_similarity(self, tickets: List[Ticket], keywords: List[str]) -> List[tuple]:
        """Score tickets based on keyword matches with weighted fields."""
        scored_tickets = []

        # Field weights for scoring
        field_weights = {
            'title': 3.0,           # Title matches are most important
            'issuetype': 2.5,       # Issue type is very important
            'subissuetype': 2.0,    # Sub-issue type is important
            'description': 1.5,     # Description matches are moderately important
            'resolution': 1.0       # Resolution matches are least important but still valuable
        }

        for ticket in tickets:
            score = 0.0

            # Score based on keyword matches in different fields
            for keyword in keywords:
                keyword_lower = keyword.lower()

                # Title matches
                if ticket.title and keyword_lower in ticket.title.lower():
                    score += field_weights['title']

                # Issue type matches
                if ticket.issuetype and keyword_lower in ticket.issuetype.lower():
                    score += field_weights['issuetype']

                # Sub-issue type matches
                if ticket.subissuetype and keyword_lower in ticket.subissuetype.lower():
                    score += field_weights['subissuetype']

                # Description matches
                if ticket.description and keyword_lower in ticket.description.lower():
                    score += field_weights['description']

                # Resolution matches (for learning from solutions)
                if ticket.resolution and keyword_lower in ticket.resolution.lower():
                    score += field_weights['resolution']

            # Bonus for resolved tickets (they have solutions we can learn from)
            if ticket.resolution and ticket.resolution.strip():
                score += 1.0

            # Add ticket with its score
            if score > 0:
                scored_tickets.append((ticket, score))

        # Sort by score (highest first)
        scored_tickets.sort(key=lambda x: x[1], reverse=True)

        return scored_tickets

    def _find_similar_tickets_by_query(self, query: str, limit: int = 4) -> List[Ticket]:
        """Enhanced method to find similar tickets using metadata extraction."""
        try:
            # Extract metadata from query
            metadata = self._extract_query_metadata(query)
            keywords = metadata['keywords']

            if not keywords:
                return []

            # Build comprehensive search conditions
            search_conditions = []

            # Primary keyword search across all relevant fields
            for keyword in keywords:
                search_conditions.extend([
                    Ticket.title.ilike(f"%{keyword}%"),
                    Ticket.description.ilike(f"%{keyword}%"),
                    Ticket.issuetype.ilike(f"%{keyword}%"),
                    Ticket.subissuetype.ilike(f"%{keyword}%"),
                    Ticket.resolution.ilike(f"%{keyword}%")
                ])

            # Enhanced search for specific issue types if detected
            if metadata['issue_type']:
                issue_type = metadata['issue_type']
                search_conditions.extend([
                    Ticket.issuetype.ilike(f"%{issue_type}%"),
                    Ticket.subissuetype.ilike(f"%{issue_type}%")
                ])

            # Search for software-specific tickets
            for software in metadata['software_mentioned']:
                search_conditions.extend([
                    Ticket.title.ilike(f"%{software}%"),
                    Ticket.description.ilike(f"%{software}%")
                ])

            # Query database with all conditions
            tickets = self.db.query(Ticket).filter(
                or_(*search_conditions)
            ).limit(limit * 3).all()  # Get more tickets for better scoring

            # Score and rank tickets using enhanced scoring
            scored_tickets = self._score_ticket_similarity_with_metadata(tickets, metadata)

            # Return top scored tickets
            return [ticket for ticket, score in scored_tickets[:limit]]

        except Exception as e:
            logger.error(f"Error finding similar tickets by query: {e}")
            return []

    def _score_ticket_similarity_with_metadata(self, tickets: List[Ticket], metadata: Dict) -> List[tuple]:
        """Advanced scoring using extracted metadata."""
        scored_tickets = []
        keywords = metadata['keywords']

        # Enhanced field weights
        field_weights = {
            'title': 4.0,
            'issuetype': 3.5,
            'subissuetype': 3.0,
            'description': 2.0,
            'resolution': 1.5
        }

        for ticket in tickets:
            score = 0.0

            # Basic keyword scoring
            for keyword in keywords:
                keyword_lower = keyword.lower()

                if ticket.title and keyword_lower in ticket.title.lower():
                    score += field_weights['title']
                if ticket.issuetype and keyword_lower in ticket.issuetype.lower():
                    score += field_weights['issuetype']
                if ticket.subissuetype and keyword_lower in ticket.subissuetype.lower():
                    score += field_weights['subissuetype']
                if ticket.description and keyword_lower in ticket.description.lower():
                    score += field_weights['description']
                if ticket.resolution and keyword_lower in ticket.resolution.lower():
                    score += field_weights['resolution']

            # Bonus scoring for metadata matches
            if metadata['issue_type'] and ticket.issuetype:
                if metadata['issue_type'].lower() in ticket.issuetype.lower():
                    score += 5.0  # High bonus for issue type match

            # Software-specific bonus
            for software in metadata['software_mentioned']:
                if ticket.title and software in ticket.title.lower():
                    score += 3.0
                if ticket.description and software in ticket.description.lower():
                    score += 2.0

            # Device-specific bonus
            for device in metadata['device_types']:
                if ticket.title and device in ticket.title.lower():
                    score += 2.0
                if ticket.description and device in ticket.description.lower():
                    score += 1.5

            # Error indicator bonus
            for error in metadata['error_indicators']:
                if ticket.title and error in ticket.title.lower():
                    score += 1.5
                if ticket.description and error in ticket.description.lower():
                    score += 1.0

            # Resolution quality bonus
            if ticket.resolution and ticket.resolution.strip():
                resolution_length = len(ticket.resolution.strip())
                if resolution_length > 100:  # Detailed resolutions are more valuable
                    score += 2.0
                elif resolution_length > 50:
                    score += 1.0

            if score > 0:
                scored_tickets.append((ticket, score))

        # Sort by score (highest first)
        scored_tickets.sort(key=lambda x: x[1], reverse=True)

        return scored_tickets

    def _generate_fallback_resolution(self, query: str, similar_tickets: List[Ticket] = None, metadata: Dict = None) -> str:
        """Generate fallback resolution when LLM service is not available."""
        response = f"## 🔧 **Technical Support Resolution**\n\n**Issue:** {query}\n\n"

        # Add metadata context if available
        if metadata:
            response += "**Issue Analysis:**\n"
            if metadata.get('issue_type'):
                response += f"- Type: {metadata['issue_type'].title()}\n"
            if metadata.get('device_types'):
                response += f"- Devices: {', '.join(metadata['device_types']).title()}\n"
            if metadata.get('software_mentioned'):
                response += f"- Software: {', '.join(metadata['software_mentioned']).title()}\n"
            if metadata.get('action_requested'):
                response += f"- Action: {metadata['action_requested'].title()}\n"
            response += "\n"

        if similar_tickets:
            response += "**Based on similar resolved tickets:**\n\n"
            for i, ticket in enumerate(similar_tickets[:2], 1):
                if ticket.resolution and ticket.resolution.strip():
                    response += f"{i}. **{ticket.title}**\n"
                    response += f"   Resolution: {ticket.resolution[:200]}...\n\n"

        response += """## 🛠️ **Recommended Steps:**

1. **Identify the Problem** - Gather specific error messages or symptoms
2. **Check Basic Connectivity** - Verify network, power, and cable connections
3. **Restart Services** - Try restarting the affected application or service
4. **Update Software** - Ensure all software is up to date
5. **Check System Resources** - Verify sufficient disk space and memory
6. **Contact Support** - If issue persists, escalate to senior technician

## 💡 **Next Steps:**
Please provide more specific details about the issue for a more targeted solution. You can also search our knowledge base or check similar tickets for additional guidance.

*Note: This is a basic resolution template. For more detailed assistance, please describe your specific symptoms and error messages.*"""

        return response

    def _generate_ai_resolution_fallback(self, problem: str, similar_tickets: List[Ticket] = None, metadata: Dict = None) -> str:
        """Generate AI resolution fallback when LLM service is not available."""

        # Extract the core issue from the problem description
        core_issue = self._extract_core_issue(problem)

        response = f"## 🤖 **AI Technical Assistant**\n\n**Problem:** {core_issue}\n\n"

        # Add metadata-based analysis
        if metadata:
            response += "**Issue Analysis:**\n"
            if metadata.get('issue_type'):
                response += f"- Type: {metadata['issue_type'].title()}\n"
            if metadata.get('software_mentioned'):
                response += f"- Software: {', '.join(metadata['software_mentioned']).title()}\n"
            if metadata.get('urgency_indicators'):
                response += f"- Priority: {'High' if metadata['urgency_indicators'] else 'Normal'}\n"
            response += "\n"

        # Generate specific resolution based on the problem
        response += self._generate_specific_resolution(problem, metadata, similar_tickets)

        # Add similar ticket context if available
        if similar_tickets:
            response += "\n## 📋 **Related Resolved Cases:**\n\n"
            for i, ticket in enumerate(similar_tickets[:2], 1):
                if ticket.resolution and ticket.resolution.strip():
                    response += f"{i}. **{ticket.title}**\n"
                    response += f"   Solution: {ticket.resolution[:200]}...\n\n"

        response += "\n## 💬 **Need More Help?**\n"
        response += "If these steps don't resolve your issue, please let me know:\n"
        response += "- What step you're stuck on\n"
        response += "- Any error messages you see\n"
        response += "- What happens when you try the steps\n\n"
        response += "*I'm here to help you through each step! 😊*"

        return response

    def _extract_core_issue(self, problem: str) -> str:
        """Extract the core issue from a problem description."""
        # Remove common prefixes
        problem = problem.lower()
        prefixes_to_remove = [
            'help me resolve this issue:', 'help me fix:', 'help me with:',
            'i have a problem with:', 'i need help with:', 'can you help me with:',
            'how do i fix:', 'how to fix:', 'how can i resolve:'
        ]

        for prefix in prefixes_to_remove:
            if problem.startswith(prefix):
                problem = problem[len(prefix):].strip()
                break

        return problem.capitalize()

    def _generate_specific_resolution(self, problem: str, metadata: Dict = None, similar_tickets: List[Ticket] = None) -> str:
        """Generate specific resolution based on the problem type."""
        problem_lower = problem.lower()

        # Email/Outlook password issues
        if any(term in problem_lower for term in ['outlook', 'email', 'password', 'forgot password']):
            return self._generate_outlook_password_resolution()

        # Network/WiFi issues
        elif any(term in problem_lower for term in ['wifi', 'internet', 'network', 'connection']):
            return self._generate_network_resolution()

        # Printer issues
        elif any(term in problem_lower for term in ['printer', 'print', 'printing']):
            return self._generate_printer_resolution()

        # Computer slow/performance issues
        elif any(term in problem_lower for term in ['slow', 'lag', 'performance', 'freeze', 'hang']):
            return self._generate_performance_resolution()

        # Software installation issues
        elif any(term in problem_lower for term in ['install', 'installation', 'setup']):
            return self._generate_installation_resolution()

        # Login/authentication issues
        elif any(term in problem_lower for term in ['login', 'sign in', 'authentication', 'access']):
            return self._generate_login_resolution()

        # Default general resolution
        else:
            return self._generate_general_resolution(problem, metadata)

    def _generate_outlook_password_resolution(self) -> str:
        """Generate specific resolution for Outlook password issues."""
        return """## 🔍 **What's Happening**
You've forgotten your Outlook email password and need to reset it to regain access to your email account.

## 🛠️ **Step-by-Step Solution**

1. **Reset Password via Web Portal**
   - Go to https://login.microsoftonline.com
   - Click "Forgot my password" or "Can't access your account?"
   - Enter your email address and click "Next"

2. **Choose Verification Method**
   - Select phone number or alternate email for verification
   - Click "Email me" or "Text me" to receive verification code
   - Enter the code when prompted

3. **Create New Password**
   - Enter a strong new password (8+ characters, mix of letters, numbers, symbols)
   - Confirm the new password
   - Click "Finish" to complete the reset

4. **Update Outlook Application**
   - Open Outlook desktop app
   - Go to File → Account Settings → Account Settings
   - Select your email account and click "Change"
   - Enter your new password and click "Next"

5. **Test Email Access**
   - Try sending a test email to yourself
   - Check if you can receive new emails
   - Verify calendar and contacts are syncing

## ✅ **How to Verify It Worked**
- You can successfully log into Outlook web portal
- Desktop Outlook app connects without errors
- You can send and receive emails normally

## 🔄 **If That Doesn't Work**
1. **Contact IT Admin** - Your organization may manage passwords centrally
2. **Check Account Status** - Account might be locked or disabled
3. **Try Safe Mode** - Start Outlook in safe mode: Windows + R → outlook /safe"""

    def _generate_network_resolution(self) -> str:
        """Generate specific resolution for network/WiFi issues."""
        return """## 🔍 **What's Happening**
Your device is having trouble connecting to the network or internet, which could be due to WiFi settings, network configuration, or connectivity issues.

## 🛠️ **Step-by-Step Solution**

1. **Check Physical Connections**
   - Ensure WiFi is enabled on your device
   - Check if ethernet cable is properly connected (if using wired)
   - Verify router/modem lights are green/blue (not red)

2. **Restart Network Components**
   - Restart your device (computer/phone/tablet)
   - Unplug router for 30 seconds, then plug back in
   - Wait 2-3 minutes for full restart

3. **Forget and Reconnect WiFi**
   - Go to Settings → Network & Internet → WiFi
   - Click on your network name → "Forget"
   - Reconnect by selecting network and entering password

4. **Reset Network Settings**
   - Windows: Settings → Network & Internet → Status → Network reset
   - Mac: System Preferences → Network → Advanced → Renew DHCP Lease
   - Run as administrator: `ipconfig /release` then `ipconfig /renew`

5. **Check DNS Settings**
   - Use Google DNS: 8.8.8.8 and 8.8.4.4
   - Or Cloudflare DNS: 1.1.1.1 and 1.0.0.1
   - Apply settings and restart

## ✅ **How to Verify It Worked**
- You can browse websites normally
- Internet speed is back to normal
- All online applications work properly"""

    def _generate_printer_resolution(self) -> str:
        """Generate specific resolution for printer issues."""
        return """## 🔍 **What's Happening**
Your printer is not working properly, which could be due to connection issues, driver problems, or hardware malfunctions.

## 🛠️ **Step-by-Step Solution**

1. **Check Physical Connections**
   - Ensure printer is powered on and connected via USB or network
   - Check for paper jams, empty paper tray, or low ink/toner
   - Verify all cables are securely connected

2. **Restart Printer and Computer**
   - Turn off printer, wait 30 seconds, turn back on
   - Restart your computer
   - Wait for both to fully boot up

3. **Check Printer Status**
   - Windows: Settings → Devices → Printers & scanners
   - Right-click your printer → "See what's printing"
   - Clear any stuck print jobs

4. **Update or Reinstall Drivers**
   - Go to printer manufacturer's website
   - Download latest drivers for your printer model
   - Uninstall old drivers, install new ones

5. **Run Printer Troubleshooter**
   - Windows: Settings → Update & Security → Troubleshoot
   - Select "Printer" and run troubleshooter
   - Follow recommended fixes

## ✅ **How to Verify It Worked**
- Print a test page successfully
- Printer appears "Ready" in device settings
- No error lights on printer display"""

    def _generate_performance_resolution(self) -> str:
        """Generate specific resolution for computer performance issues."""
        return """## 🔍 **What's Happening**
Your computer is running slowly, which could be due to high resource usage, insufficient storage, or background processes.

## 🛠️ **Step-by-Step Solution**

1. **Check System Resources**
   - Press Ctrl + Shift + Esc to open Task Manager
   - Click "More details" → "Performance" tab
   - Check CPU, Memory, and Disk usage

2. **Close Unnecessary Programs**
   - In Task Manager → "Processes" tab
   - End high-resource programs you don't need
   - Right-click → "End task" for problematic processes

3. **Free Up Disk Space**
   - Windows: Settings → System → Storage
   - Run Disk Cleanup: Windows + R → cleanmgr
   - Delete temporary files, downloads, recycle bin

4. **Disable Startup Programs**
   - Task Manager → "Startup" tab
   - Disable programs you don't need at startup
   - Right-click → "Disable"

5. **Run System Maintenance**
   - Windows: Control Panel → System and Security → Security and Maintenance
   - Click "Start maintenance"
   - Run Windows Update and install updates

## ✅ **How to Verify It Worked**
- Computer boots faster
- Programs open quickly
- No lag when switching between applications"""

    def _generate_login_resolution(self) -> str:
        """Generate specific resolution for login/authentication issues."""
        return """## 🔍 **What's Happening**
You're unable to log into your account, which could be due to incorrect credentials, account lockout, or system issues.

## 🛠️ **Step-by-Step Solution**

1. **Verify Credentials**
   - Double-check username/email spelling
   - Ensure Caps Lock is off
   - Try typing password in notepad first to verify

2. **Reset Password**
   - Click "Forgot Password" or "Reset Password"
   - Check email for reset instructions
   - Follow the link and create new password

3. **Clear Browser Data**
   - Clear cookies and cache for the login site
   - Try incognito/private browsing mode
   - Disable browser extensions temporarily

4. **Check Account Status**
   - Contact IT admin if it's a work account
   - Verify account hasn't been suspended
   - Check if multi-factor authentication is required

5. **Try Different Browser/Device**
   - Test login from different browser
   - Try from mobile device or different computer
   - Check if the service is experiencing outages

## ✅ **How to Verify It Worked**
- You can successfully log into your account
- All account features are accessible
- Login works consistently across devices"""

    def _generate_installation_resolution(self) -> str:
        """Generate specific resolution for software installation issues."""
        return """## 🔍 **What's Happening**
You're having trouble installing software, which could be due to permissions, compatibility, or system requirements.

## 🛠️ **Step-by-Step Solution**

1. **Check System Requirements**
   - Verify your OS version is supported
   - Ensure sufficient disk space (at least 2GB free)
   - Check RAM and processor requirements

2. **Run as Administrator**
   - Right-click installer → "Run as administrator"
   - Enter admin credentials when prompted
   - Allow the installation to proceed

3. **Disable Antivirus Temporarily**
   - Temporarily disable real-time protection
   - Add installer to antivirus exceptions
   - Re-enable protection after installation

4. **Clear Temporary Files**
   - Windows + R → %temp% → Delete all files
   - Empty Recycle Bin
   - Restart computer before trying again

5. **Download Fresh Installer**
   - Download installer from official website
   - Verify file isn't corrupted (check file size)
   - Try compatibility mode if needed

## ✅ **How to Verify It Worked**
- Software installs without errors
- Application launches successfully
- All features work as expected"""

    def _generate_general_resolution(self, problem: str, metadata: Dict = None) -> str:
        """Generate general resolution for unspecified issues."""
        return f"""## 🔍 **What's Happening**
You're experiencing an issue that needs troubleshooting. Let me provide a systematic approach to resolve it.

## 🛠️ **Step-by-Step Solution**

1. **Gather Information**
   - Note exact error messages or symptoms
   - Identify when the problem started
   - List what you were doing when it occurred

2. **Try Basic Fixes**
   - Restart the affected application
   - Restart your computer
   - Check for software updates

3. **Check Connections**
   - Verify all cables are connected properly
   - Test network connectivity
   - Ensure power sources are working

4. **Isolate the Problem**
   - Test with different user account
   - Try safe mode or diagnostic mode
   - Disable recently installed software

5. **Advanced Troubleshooting**
   - Check system logs for errors
   - Run built-in diagnostic tools
   - Search for specific error codes online

## ✅ **How to Verify It Worked**
- The original problem no longer occurs
- All related functions work normally
- System performance is stable

## 🔄 **If That Doesn't Work**
Please provide more specific details about:
- Exact error messages
- When the problem occurs
- What you were trying to accomplish"""

    def _get_troubleshooting_steps(self, metadata: Dict) -> str:
        """Generate troubleshooting steps based on metadata."""
        steps = "1. **Identify Symptoms** - Document exact error messages and behaviors\n"
        steps += "2. **Check Connections** - Verify all cables and network connections\n"
        steps += "3. **Restart Components** - Try restarting the affected service/application\n"

        if metadata.get('software_mentioned'):
            steps += "4. **Update Software** - Ensure all applications are up to date\n"
            steps += "5. **Check Compatibility** - Verify software compatibility with your system\n"

        if metadata.get('device_types'):
            steps += "4. **Hardware Check** - Verify device drivers and hardware status\n"
            steps += "5. **Run Diagnostics** - Use built-in diagnostic tools\n"

        steps += "6. **Test Solution** - Verify the issue is resolved\n"
        return steps

    def _get_installation_steps(self, metadata: Dict) -> str:
        """Generate installation steps based on metadata."""
        steps = "1. **Prepare System** - Check system requirements and compatibility\n"
        steps += "2. **Download Software** - Get the latest version from official sources\n"
        steps += "3. **Backup Data** - Create backups before installation\n"
        steps += "4. **Install Application** - Follow installation wizard carefully\n"
        steps += "5. **Configure Settings** - Set up initial configuration\n"
        steps += "6. **Test Functionality** - Verify installation was successful\n"
        return steps

    def _get_update_steps(self, metadata: Dict) -> str:
        """Generate update steps based on metadata."""
        steps = "1. **Check Current Version** - Identify what version you're currently running\n"
        steps += "2. **Backup Settings** - Save current configuration and data\n"
        steps += "3. **Download Updates** - Get updates from official sources\n"
        steps += "4. **Install Updates** - Apply updates following proper procedures\n"
        steps += "5. **Restart Services** - Restart affected applications/services\n"
        steps += "6. **Verify Update** - Confirm update was applied successfully\n"
        return steps

    def _get_general_steps(self, metadata: Dict) -> str:
        """Generate general troubleshooting steps."""
        steps = "1. **Gather Information** - Collect error messages and system details\n"
        steps += "2. **Check Documentation** - Review user manuals and knowledge base\n"
        steps += "3. **Try Basic Fixes** - Restart, update, and check connections\n"
        steps += "4. **Isolate Problem** - Determine if issue is hardware or software related\n"
        steps += "5. **Apply Solution** - Implement the most appropriate fix\n"
        steps += "6. **Document Resolution** - Record what worked for future reference\n"
        return steps

    def _clean_resolution_query(self, query: str) -> str:
        """Clean resolution query by removing command words."""
        # Remove common command phrases
        command_phrases = ['help me', 'can you help', 'i need help', 'resolution for', 'solve', 'fix', 'how to']

        clean_query = query.lower()
        for phrase in command_phrases:
            clean_query = clean_query.replace(phrase, '')

        return clean_query.strip()

    def _generate_fallback_resolution(self, issue: str, similar_tickets: List[Ticket]) -> str:
        """Generate fallback resolution when LLM is not available."""
        response = f"## 🔧 Resolution for: {issue}\n\n"

        if similar_tickets:
            response += "**Based on similar resolved tickets:**\n\n"
            for i, ticket in enumerate(similar_tickets[:2], 1):
                if ticket.resolution:
                    response += f"{i}. **{ticket.title}**\n   Resolution: {ticket.resolution[:200]}...\n\n"

        response += """**General Troubleshooting Steps:**

1. **Restart and Update**
   - Restart the affected application/service
   - Check for and install updates
   - Restart your computer if needed

2. **Check System Resources**
   - Ensure adequate disk space (15%+ free)
   - Close unnecessary applications
   - Check Task Manager for high resource usage

3. **Verify Permissions**
   - Run as administrator if needed
   - Check user account permissions
   - Verify network connectivity

4. **Documentation**
   - Note exact error messages
   - Record when the issue occurs
   - Document steps to reproduce

💬 **Need more specific help?** Describe your exact symptoms and I'll provide targeted assistance!"""

        return response

    def _generate_general_fallback(self, query: str) -> str:
        """Generate fallback response for general queries."""
        return f"""I understand you're asking about: "{query}"

I'm here to help you with:
• 📋 **Ticket Management** - Show your recent tickets
• 🔍 **Similar Tickets** - Find related tickets for any issue
• 💡 **AI Resolutions** - Get step-by-step solutions
• 🎫 **Ticket Details** - Get information about specific tickets

What specific help do you need today?"""



    def _handle_ai_resolution_followup(
        self,
        message: str,
        context_data: Dict,
        conversation_history: List[str],
        technician: TechnicianDummyData,
        session_id: str
    ) -> ChatResponse:
        """Handle follow-up messages in AI resolution conversation."""
        original_problem = context_data.get('problem', '')
        similar_ticket_ids = context_data.get('similar_tickets', [])

        # Get similar tickets
        similar_tickets = []
        if similar_ticket_ids:
            try:
                similar_tickets = self.db.query(Ticket).filter(
                    Ticket.ticketnumber.in_(similar_ticket_ids)
                ).all()
            except Exception as e:
                logger.error(f"Error fetching similar tickets: {e}")

        try:
            # Use interactive AI resolution with conversation history
            if self.llm_service and hasattr(self.llm_service, 'generate_interactive_ai_resolution'):
                response_text = self.llm_service.generate_interactive_ai_resolution(
                    f"{original_problem} - Follow-up: {message}",
                    conversation_history + [message],
                    similar_tickets
                )
            else:
                response_text = self._generate_ai_followup_fallback(message, original_problem, similar_tickets)

            # Create ticket responses for related tickets
            ticket_responses = []
            if similar_tickets:
                ticket_responses = [TicketResponse.from_orm(ticket) for ticket in similar_tickets[:3]]

            return self._create_response(
                response_text,
                session_id=session_id,
                related_tickets=ticket_responses
            )

        except Exception as e:
            logger.error(f"Error in AI resolution follow-up: {e}")
            return self._create_response(
                self._generate_ai_followup_fallback(message, original_problem, similar_tickets),
                session_id=session_id
            )

    def _generate_ai_followup_fallback(self, message: str, original_problem: str, similar_tickets: List[Ticket] = None) -> str:
        """Generate fallback for AI resolution follow-up."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['thanks', 'thank you', 'worked', 'fixed', 'solved']):
            return "Great! I'm glad I could help you resolve the issue. Is there anything else you need assistance with?"

        elif any(word in message_lower for word in ['didn\'t work', 'not working', 'still', 'error', 'problem']):
            response = f"""I understand the solution didn't work as expected. Let me provide some alternative approaches for: **{original_problem}**

## 🔄 **Alternative Solutions:**

1. **Restart in Safe Mode** - Try restarting your device in safe mode to isolate the issue
2. **Check for Updates** - Ensure all software and drivers are up to date
3. **Run System Diagnostics** - Use built-in diagnostic tools to identify hardware issues
4. **Contact IT Support** - If the issue persists, escalate to your IT department

Can you tell me more about what happened when you tried the previous solution?"""

            if similar_tickets:
                response += "\n\n**📋 Other Solutions That Have Worked:**\n"
                for ticket in similar_tickets[:2]:
                    if ticket.resolution:
                        response += f"- **{ticket.title}**: {ticket.resolution[:150]}...\n"

            return response

        else:
            return f"""Thanks for the additional information about: **{original_problem}**

Based on what you've told me, here are the next steps:

## 🛠️ **Recommended Actions:**

1. **Document the Issue** - Note exactly what you see and when it happens
2. **Try Basic Troubleshooting** - Restart the application or device
3. **Check System Resources** - Ensure adequate memory and disk space
4. **Test with Different User** - See if the issue is user-specific

Would you like me to provide more specific guidance for any of these steps?"""
