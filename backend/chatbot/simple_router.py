"""Chatbot API Router for Autotask integration without authentication requirement."""

import logging
import os
import json
import jwt
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Env-driven Snowflake database/schema (no hardcoded DB name in queries)
try:
    from config import SF_DATABASE, SF_SCHEMA
except ImportError:  # project root not on sys.path
    SF_DATABASE = os.getenv('SF_DATABASE') or os.getenv('SNOWFLAKE_DATABASE') or 'TEST_DB'
    SF_SCHEMA = os.getenv('SF_SCHEMA') or os.getenv('SNOWFLAKE_SCHEMA') or 'PUBLIC'

# Same secret/algorithm the main app uses to sign tokens (backend/main.py) so that
# a real logged-in technician can be identified here instead of always defaulting.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

# Global variables to store connections (will be set by main app)
snowflake_conn = None
llm_service = None

# In-memory conversation history keyed by session_id.
# Each entry is a single string in the form "USER: ..." / "BOT: ...".
conversation_store: Dict[str, List[str]] = {}
MAX_HISTORY_ENTRIES = 20

# Diagnostics: last LLM error so a /debug endpoint can reveal why the LLM path fails.
last_llm_error: Optional[str] = None
last_llm_error_at: Optional[str] = None

def set_database_connection(conn):
    """Set the database connection from the main app."""
    global snowflake_conn
    snowflake_conn = conn
    print("✅ Chatbot: Database connection set successfully")

def set_llm_service(service):
    """Set the LLM service from the main app."""
    global llm_service
    llm_service = service
    print("✅ Chatbot: LLM service set successfully")

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# Models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    message_type: Optional[str] = "user"
    timestamp: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime = Field(default_factory=datetime.now)

class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_technician: Optional[str] = None

# Helper function to get current technician from main app's authentication
async def get_current_technician_from_main_app(request: Request) -> str:
    """Get the current technician ID from the main application's authentication.

    Decodes the same JWT the main app issues on login and returns the real
    technician ID (the token's "sub" claim). Falls back to a default technician
    when no token is present or it fails to validate, since this router
    intentionally also supports unauthenticated/demo access.
    """
    try:
        # Get the Authorization header
        auth_header = request.headers.get("Authorization") if request else None
        if not auth_header or not auth_header.startswith("Bearer "):
            # If no auth header, default to a test user
            return "T001"  # Default technician for testing

        # Extract and validate the token
        token = auth_header.split(" ", 1)[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub") or "T001"

    except jwt.PyJWTError as e:
        # Expected when the caller's token is missing/expired — we intentionally
        # fall back to the default technician for anonymous/demo access.
        logger.debug(f"Invalid chatbot auth token, using default technician: {e}")
        return "T001"
    except Exception as e:
        logger.debug(f"Could not extract technician from auth: {e}")
        return "T001"  # Default technician

# ---------------------------------------------------------------------------
# Conversation helpers (LLM-first routing)
# ---------------------------------------------------------------------------

def _get_conversation_history(session_id: str) -> List[str]:
    """Return the recent conversational turns for a session."""
    if not session_id:
        return []
    return conversation_store.get(session_id, [])[-10:]


def _append_to_history(session_id: str, user_message: str, bot_message: str):
    """Record one user/bot exchange for a session."""
    if not session_id:
        return
    history = conversation_store.setdefault(session_id, [])
    history.append(f"USER: {user_message}")
    history.append(f"BOT: {bot_message}")
    # Keep the store bounded
    if len(history) > MAX_HISTORY_ENTRIES:
        conversation_store[session_id] = history[-MAX_HISTORY_ENTRIES:]


def _detect_intent(message: str) -> str:
    """Classify what kind of support request the user is making.

    This is only a *hint* for building context / instructions — the LLM itself
    always makes the final decision about scope and how to respond.
    """
    m = message.lower()

    if any(w in m for w in [
        'ai resolution', 'ai help', 'ai support', 'ai_resolution',
        'resolve', 'resolution', 'how to fix'
    ]):
        return "ai_resolution"
    if any(w in m for w in ['similar ticket', 'tickets similar', 'similar to', 'find tickets related']):
        return "similar_tickets"
    if any(w in m for w in ['faq', 'frequently asked', 'help topics', 'what can you help', 'knowledge base']):
        return "faq"
    if any(w in m for w in ['my ticket', 'my_tickets', 'my recent tickets', 'show my', 'show me my', 'assigned to me']):
        return "my_tickets"
    if any(w in m for w in ['hello', 'hi ', 'hey', 'good morning', 'good afternoon', 'good evening', ' how are you']):
        return "greeting"
    if any(w in m for w in ['thank you', 'thanks', 'appreciate it', 'thankyou']):
        return "thanks"
    if _is_technical_question(message):
        return "technical_issue"
    return "general"


def _fetch_my_tickets(current_user: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch tickets assigned to the current user (raw DB rows)."""
    if not snowflake_conn:
        return []
    try:
        query = f"""
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY
            FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS
            WHERE TECHNICIAN_ID = %s
            ORDER BY TICKETNUMBER DESC
            LIMIT {int(limit)}
        """
        results = snowflake_conn.execute_query(query, (current_user,))
        return [dict(row) for row in results]
    except Exception as e:
        logger.warning(f"Could not fetch my tickets for {current_user}: {e}")
        return []


# Semantic search over tickets.
# NOTE: SNOWFLAKE.CORTEX.AI_SIMILARITY is NOT available on this account (it throws
# "Unknown user-defined function"), so we use Cortex embeddings + VECTOR_COSINE_SIMILARITY
# instead (verified working). If vector search fails anywhere, we fall back to a keyword
# (ILIKE) search so the similar-tickets feature always returns something useful.
_SEMANTIC_SCORE_EXPR = (
    "VECTOR_COSINE_SIMILARITY(\n"
    "    SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', "
    "COALESCE(TITLE, '') || ' ' || COALESCE(DESCRIPTION, '')),\n"
    "    SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', %s)\n"
    ") AS SIMILARITY_SCORE"
)


def _semantic_search(
    table: str,
    search_text: str,
    exclude_ticket: Optional[str] = None,
    limit: int = 5,
    select_columns: str = "TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, RESOLUTION",
) -> List[Dict[str, Any]]:
    """Similar-ticket search using Cortex embeddings (vector cosine similarity).

    Falls back to a keyword (ILIKE) search if the vector functions are unavailable.
    Returns a list of dict-like rows. Rows from the vector search include a
    SIMILARITY_SCORE key; keyword-fallback rows don't (use default 0.3 downstream).
    """
    if not snowflake_conn:
        return []

    exclude_clause = ""
    if exclude_ticket:
        safe_ticket = exclude_ticket.replace("'", "''")
        exclude_clause = f"AND TICKETNUMBER != '{safe_ticket}'"

    base_where = f"""
    WHERE TITLE IS NOT NULL AND DESCRIPTION IS NOT NULL
      AND TRIM(TITLE) != '' AND TRIM(DESCRIPTION) != ''
      AND LENGTH(TRIM(TITLE || ' ' || DESCRIPTION)) > 10
      {exclude_clause}
    """

    # 1) Try Cortex vector similarity (EMBED_TEXT_768 + VECTOR_COSINE_SIMILARITY)
    try:
        query = f"""
            SELECT {select_columns},
                   {_SEMANTIC_SCORE_EXPR}
            FROM {table}
            {base_where}
            ORDER BY SIMILARITY_SCORE DESC
            LIMIT {int(limit)}
        """
        results = snowflake_conn.execute_query(query, (search_text,))
        rows = [dict(row) for row in results]
        if rows:
            return rows
    except Exception as e:
        logger.warning(f"Cortex vector similarity failed on {table}; using keyword fallback: {e}")

    # 2) Keyword fallback (works even without Cortex vector functions)
    try:
        terms = [w for w in search_text.lower().split() if len(w) > 2][:5]
        if not terms:
            return []
        safe_terms = [t.replace("'", "''") for t in terms]
        like_clauses = " OR ".join(
            f"UPPER(COALESCE(TITLE,'')) LIKE UPPER('%{t}%') "
            f"OR UPPER(COALESCE(DESCRIPTION,'')) LIKE UPPER('%{t}%')"
            for t in safe_terms
        )
        query = f"""
            SELECT {select_columns}
            FROM {table}
            {base_where}
              AND ({like_clauses})
            ORDER BY TICKETNUMBER DESC
            LIMIT {int(limit)}
        """
        results = snowflake_conn.execute_query(query)
        return [dict(row) for row in results]
    except Exception as e:
        logger.warning(f"Keyword fallback failed on {table}: {e}")
        return []


def _fetch_similar_tickets(search_text: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Fetch tickets similar to `search_text` (vector similarity + keyword fallback)."""
    return _semantic_search(f"{SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS", search_text, limit=limit)


def _gather_ticket_context(user_message: str, current_user: str) -> Dict[str, Any]:
    """Gather relevant ticket/DB context so the LLM can answer with real data.

    For ticket/issue-related intents we pull the user's assigned tickets and —
    when the user is looking for similar/resolved issues — semantically similar
    tickets via Cortex.
    """
    intent = _detect_intent(user_message)
    context: Dict[str, Any] = {}

    my_tickets = _fetch_my_tickets(current_user, limit=5)
    context["my_tickets"] = my_tickets
    if my_tickets:
        context["my_ticket_count"] = len(my_tickets)

    if intent in ("similar_tickets", "ai_resolution", "technical_issue"):
        search_text = user_message
        # If the user references their latest ticket, search using its content.
        if my_tickets and any(w in user_message.lower() for w in ["latest ticket", "my ticket"]):
            latest = my_tickets[0]
            search_text = f"{latest.get('TITLE', '')} {latest.get('DESCRIPTION', '')}".strip()
        if search_text:
            similar = _fetch_similar_tickets(search_text, limit=3)
            context["similar_tickets"] = similar

    if not my_tickets:
        context["note"] = (
            "The database returned NO tickets for this user. Do not invent ticket numbers, "
            "titles, or statuses. If the user asks about their tickets, state plainly that "
            "none were found and suggest how to proceed."
        )
    return context


# 1. GET /chatbot/tickets/my – Retrieves tickets assigned to the logged-in user
@router.get("/tickets/my", response_model=List[TicketResponse])
async def get_my_tickets(request: Request):
    """Retrieves tickets assigned to the logged-in user."""
    try:
        current_user = await get_current_technician_from_main_app(request)
        
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection not available. Please ensure Snowflake connection is properly configured.")

        # Query real tickets from database assigned to current user
        query = f"""
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, TECHNICIAN_ID
            FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS
            WHERE TECHNICIAN_ID = %s
            ORDER BY TICKETNUMBER DESC
            LIMIT 20
        """
        results = snowflake_conn.execute_query(query, (current_user,))

        tickets = []
        for row in results:
            tickets.append(TicketResponse(
                ticket_id=row.get('TICKETNUMBER', ''),
                title=row.get('TITLE', ''),
                description=row.get('DESCRIPTION', ''),
                status=row.get('STATUS') or 'Open',
                priority=row.get('PRIORITY') or 'Medium',
                assigned_technician=row.get('TECHNICIAN_ID', '')
            ))

        return tickets

    except Exception as e:
        logger.error(f"Error fetching my tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickets: {str(e)}")

# 2. GET /chatbot/tickets/search – Searches for tickets based on provided criteria
@router.get("/tickets/search", response_model=List[TicketResponse])
async def search_tickets(
    q: str = Query(..., description="Search query"),
    request: Request = None
):
    """Searches for tickets based on provided criteria."""
    try:
        current_user = await get_current_technician_from_main_app(request) if request else "T001"
        
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection not available. Please ensure Snowflake connection is properly configured.")

        # Search real tickets from database
        search_term = f"%{q}%"
        query = f"""
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, TECHNICIANEMAIL
            FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS
            WHERE UPPER(TITLE) LIKE UPPER(%s)
               OR UPPER(DESCRIPTION) LIKE UPPER(%s)
            ORDER BY TICKETNUMBER DESC
            LIMIT 20
        """
        results = snowflake_conn.execute_query(query, (search_term, search_term))

        tickets = []
        for row in results:
            tickets.append(TicketResponse(
                ticket_id=row.get('TICKETNUMBER', ''),
                title=row.get('TITLE', ''),
                description=row.get('DESCRIPTION', ''),
                status=row.get('STATUS', ''),
                priority=row.get('PRIORITY', ''),
                assigned_technician=row.get('TECHNICIANEMAIL', '')
            ))

        return tickets

    except Exception as e:
        logger.error(f"Error searching tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search tickets: {str(e)}")

# 3. GET /chatbot/tickets/{ticket_id} – Fetches detailed information for a specific ticket
@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, request: Request = None):
    """Fetches detailed information for a specific ticket by using ticket number."""
    try:
        current_user = await get_current_technician_from_main_app(request) if request else "T001"
        
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection not available. Please ensure Snowflake connection is properly configured.")

        # Query specific ticket from database
        query = f"""
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, TECHNICIANEMAIL
            FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS
            WHERE TICKETNUMBER = %s
        """
        results = snowflake_conn.execute_query(query, (ticket_id,))

        if not results:
            raise HTTPException(status_code=404, detail="Ticket not found")

        row = results[0]
        return TicketResponse(
            ticket_id=row.get('TICKETNUMBER', ''),
            title=row.get('TITLE', ''),
            description=row.get('DESCRIPTION', ''),
            status=row.get('STATUS', ''),
            priority=row.get('PRIORITY', ''),
            assigned_technician=row.get('TECHNICIANEMAIL', '')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ticket: {str(e)}")

# 4. GET /chatbot/tickets/similar/{ticket_number} – Finds tickets similar to the specified ticket number
@router.get("/tickets/similar/{ticket_number}", response_model=List[TicketResponse])
async def find_similar_tickets(ticket_number: str, request: Request = None):
    """Finds tickets similar to the specified ticket number using semantic similarity."""
    try:
        current_user = await get_current_technician_from_main_app(request) if request else "T001"
        
        if not snowflake_conn:
            raise HTTPException(status_code=503, detail="Database connection not available. Please ensure Snowflake connection is properly configured.")

        # First, get the original ticket to find similar ones
        original_query = f"""
            SELECT TITLE, DESCRIPTION, STATUS, PRIORITY, ISSUETYPE, SUBISSUETYPE
            FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS
            WHERE TICKETNUMBER = %s
        """
        original_results = snowflake_conn.execute_query(original_query, (ticket_number,))

        if not original_results:
            raise HTTPException(status_code=404, detail="Original ticket not found")

        original_ticket = original_results[0]
        original_title = original_ticket.get('TITLE', '')
        original_description = original_ticket.get('DESCRIPTION', '')
        original_issue_type = original_ticket.get('ISSUETYPE', '')
        
        # Combine title and description for semantic search
        search_text = f"{original_title} {original_description}".strip()
        
        if not search_text:
            raise HTTPException(status_code=400, detail="Original ticket has no content to search for similar tickets")

        # Semantic similarity search in TICKETS table (Cortex embeddings + keyword fallback)
        tickets_results = _semantic_search(
            f"{SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS",
            search_text,
            exclude_ticket=ticket_number,
            limit=5,
            select_columns=(
                "TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, "
                "TECHNICIANEMAIL, ISSUETYPE, SUBISSUETYPE, RESOLUTION"
            ),
        )

        # Semantic similarity search in COMPANY_4130_DATA table
        company_results = _semantic_search(
            f"{SF_DATABASE}.{SF_SCHEMA}.COMPANY_4130_DATA",
            search_text,
            limit=5,
            select_columns=(
                "TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, "
                "ISSUETYPE, SUBISSUETYPE, RESOLUTION"
            ),
        )
        
        # Combine and sort results by similarity score
        all_results = []
        
        # Add TICKETS results
        for row in tickets_results:
            # Keyword fallback rows have no SIMILARITY_SCORE — give them a modest default.
            score = row.get('SIMILARITY_SCORE', 0.3)
            if not isinstance(score, (int, float)) or score < 0:
                score = 0.3
            all_results.append({
                'source': 'TICKETS',
                'data': row,
                'score': score
            })
        
        # Add COMPANY_4130_DATA results
        for row in company_results:
            score = row.get('SIMILARITY_SCORE', 0.3)
            if not isinstance(score, (int, float)) or score < 0:
                score = 0.3
            all_results.append({
                'source': 'COMPANY_4130_DATA',
                'data': row,
                'score': score
            })
        
        # Sort by similarity score (highest first)
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Convert to TicketResponse format
        tickets = []
        for result in all_results[:10]:  # Return top 10 most similar
            row = result['data']
            source = result['source']
            
            # Create enhanced description with source and resolution info
            description = row.get('DESCRIPTION', '')
            resolution = row.get('RESOLUTION', '')
            
            enhanced_description = f"[Source: {source}] {description}"
            if resolution and resolution.strip():
                enhanced_description += f"\n\nResolution: {resolution[:200]}{'...' if len(resolution) > 200 else ''}"
            
            tickets.append(TicketResponse(
                ticket_id=row.get('TICKETNUMBER', ''),
                title=row.get('TITLE', ''),
                description=enhanced_description,
                status=row.get('STATUS', ''),
                priority=row.get('PRIORITY', ''),
                assigned_technician=row.get('TECHNICIANEMAIL', '') if source == 'TICKETS' else None
            ))

        return tickets

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar tickets for {ticket_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find similar tickets: {str(e)}")

# Scope + per-intent instructions for the LLM (Snowflake Cortex).
# Every user prompt is sent to the LLM; the LLM itself decides whether the
# request is in scope for this IT-support assistant and how to respond.
_SCOPE_INSTRUCTIONS = (
    "SCOPE RULE: First decide whether the user's request is within the scope of an "
    "IT support assistant for our service desk (computers, laptops, servers, networking, "
    "Wi-Fi, printers, software, email, passwords, accounts, tickets, technical "
    "troubleshooting, and similar). If it IS in scope, respond helpfully and completely. "
    "If it is NOT in scope (e.g. unrelated topics, non-IT questions), do not answer the "
    "question itself — politely explain that you are the IT support assistant and can only "
    "help with technical/IT support topics, then briefly suggest what you CAN help with."
)

_INTENT_INSTRUCTIONS = {
    "ai_resolution": (
        "You are an expert IT support technician with 15+ years of experience. "
        "Provide a COMPREHENSIVE, step-by-step solution for the user's technical problem. "
        "Structure your answer with clear numbered steps, exact menu paths or commands, "
        "verification steps, and alternative approaches. If useful, reference the "
        "similar_tickets/context data to show how similar resolved issues were handled."
    ),
    "technical_issue": (
        "You are a friendly but expert IT support technician. Diagnose the user's technical "
        "issue and give a clear, actionable step-by-step fix. If the context includes "
        "similar resolved tickets, use them as the best-known resolution. Ask one focused "
        "clarifying question only if the problem is genuinely ambiguous."
    ),
    "similar_tickets": (
        "The user is looking for tickets similar to their issue. Use ONLY the similar_tickets "
        "and my_tickets context provided below — never invent ticket numbers, resolutions, or "
        "statuses. Summarize the most relevant tickets (with their actual ticket numbers), "
        "explain how they relate to the user's issue, and share the resolution that was applied "
        "so the user can try it. If the context contains no similar tickets, say so honestly "
        "and offer next steps."
    ),
    "my_tickets": (
        "Summarize the user's assigned tickets using ONLY the my_tickets context provided below "
        "(ticket number, title, status, priority). NEVER invent ticket numbers, titles, statuses, "
        "or priorities. If the context shows there are no tickets ('my_tickets' is empty or a "
        "'note' says none were found), tell the user plainly that they have no assigned tickets "
        "and offer to help create or search for one."
    ),
    "faq": (
        "The user wants help topics / frequently asked questions. Produce a concise, friendly "
        "FAQ-style overview of common IT issues and how the assistant can help, based on the "
        "context. Keep it structured with a small number of categories."
    ),
    "greeting": (
        "Acknowledge the greeting warmly and briefly, then offer what you can help with "
        "(troubleshooting, tickets, FAQs). Keep it short."
    ),
    "thanks": (
        "Respond briefly and warmly to the thanks and offer further help if needed. "
        "Keep it short."
    ),
    "general": (
        "You are a helpful, knowledgeable IT support assistant. Also apply the SCOPE RULE "
        "above: if the question is general but IT-related, answer clearly and concisely; "
        "if it is unrelated to IT support, politely decline and redirect to IT topics."
    ),
}

# 5. POST /chatbot/chat – Sends a chat message to the chatbot for the resolution and general message
@router.post("/chat", response_model=ChatResponse)
async def chat_message(message: ChatMessage, request: Request = None):
    """Sends a chat message to the chatbot.

    EVERY prompt is routed to the LLM (Snowflake Cortex). The LLM internally decides
    whether the request is in scope for the IT support assistant and answers accordingly
    (help if in-scope, politely redirect if out-of-scope). The rule-based engine is only
    used as a last-resort fallback if the LLM is genuinely unavailable.
    """
    global last_llm_error, last_llm_error_at
    try:
        current_user = await get_current_technician_from_main_app(request) if request else "T001"
        user_message = message.message.strip()
        session_id = message.session_id or f"anon_{datetime.now().timestamp():.0f}"
        intent = _detect_intent(user_message)

        # ---- ALWAYS try the LLM first, for every single prompt ----
        if llm_service:
            try:
                # Gather ticket / similar-ticket context (via Snowflake Cortex AI_SIMILARITY)
                ticket_context = _gather_ticket_context(user_message, current_user)
                history = _get_conversation_history(session_id)

                instructions = (
                    _SCOPE_INSTRUCTIONS + "\n\n"
                    + _INTENT_INSTRUCTIONS.get(intent, _INTENT_INSTRUCTIONS["general"])
                )

                ai_response = llm_service.generate_conversational_response(
                    context_type=f"intent={intent}",
                    user_message=user_message,
                    conversation_history=history,
                    extra_context=ticket_context,
                    system_instructions=instructions,
                )
                if ai_response and len(ai_response.strip()) > 10:  # Valid response
                    _append_to_history(session_id, user_message, ai_response)
                    return ChatResponse(response=ai_response)

            except Exception as e:
                logger.error(f"LLM failed for intent '{intent}': {e}")
                last_llm_error = str(e)
                last_llm_error_at = datetime.now().isoformat()

            # Second chance: interactive AI resolution (more guided format)
            try:
                ai_response = llm_service.generate_interactive_ai_resolution(
                    user_problem=user_message,
                    conversation_history=_get_conversation_history(session_id),
                    similar_tickets=[],
                    metadata={"user": current_user}
                )
                if ai_response and len(ai_response.strip()) > 10:
                    _append_to_history(session_id, user_message, ai_response)
                    return ChatResponse(response=ai_response)
            except Exception as e:
                logger.error(f"Interactive AI resolution failed: {e}")
                if not last_llm_error:
                    last_llm_error = str(e)
                    last_llm_error_at = datetime.now().isoformat()

        # ---- Last-resort fallback: rule-based engine (LLM unavailable/error) ----
        if not llm_service and not last_llm_error_at:
            last_llm_error = "llm_service is None (LLM was never initialized)."
            last_llm_error_at = datetime.now().isoformat()

        response_text = _generate_intelligent_response(user_message, current_user)
        _append_to_history(session_id, user_message, response_text)
        return ChatResponse(response=response_text)

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Error processing chat message")


@router.get("/debug")
async def debug_status():
    """Diagnostic endpoint showing whether the LLM is wired in and any last error."""
    return {
        "llm_service_initialized": llm_service is not None,
        "cortex_available": bool(llm_service and llm_service.cortex_available),
        "db_connected": bool(snowflake_conn and snowflake_conn.is_connected()) if snowflake_conn else False,
        "conversation_sessions": len(conversation_store),
        "last_llm_error": last_llm_error,
        "last_llm_error_at": last_llm_error_at,
        "server_time": datetime.now().isoformat(),
    }

def _is_technical_question(message: str) -> bool:
    """Determine if the message is asking for technical help."""
    technical_keywords = [
        'error', 'issue', 'problem', 'not working', 'broken', 'fix', 'help',
        'troubleshoot', 'install', 'configure', 'setup', 'network', 'server',
        'computer', 'laptop', 'printer', 'email', 'software', 'hardware',
        'windows', 'linux', 'mac', 'office', 'outlook', 'internet', 'wifi',
        'password', 'login', 'access', 'permission', 'slow', 'crash', 'freeze',
        'blue screen', 'restart', 'boot', 'startup', 'shutdown', 'update',
        'virus', 'malware', 'security', 'backup', 'restore', 'recovery',
        'firewall', 'vpn', 'dns', 'ip address', 'router', 'modem', 'ethernet',
        'database', 'sql', 'api', 'ssl', 'certificate', 'encryption', 'port',
        'driver', 'bios', 'firmware', 'disk space', 'memory', 'cpu', 'gpu'
    ]

    # Also check for question patterns that suggest technical inquiry
    question_patterns = [
        'how to', 'how do i', 'what is', 'why is', 'can you help',
        'how can i', 'what does', 'explain', 'difference between'
    ]

    message_lower = message.lower()

    # Check for technical keywords
    has_technical_keyword = any(keyword in message_lower for keyword in technical_keywords)

    # Check for question patterns combined with any tech-related context
    has_question_pattern = any(pattern in message_lower for pattern in question_patterns)

    # If it's a question pattern, it's likely technical if it contains any tech terms
    if has_question_pattern:
        tech_context = ['computer', 'system', 'software', 'application', 'program', 'file', 'folder']
        has_tech_context = any(term in message_lower for term in tech_context)
        return has_technical_keyword or has_tech_context

    return has_technical_keyword

def _generate_direct_answer_fallback(message: str, user: str) -> str:
    """Generate direct answers to common questions when AI is not available."""
    message_lower = message.lower()

    # Direct answers for "What is" questions
    if any(phrase in message_lower for phrase in ['what is computer', 'what is a computer']):
        return f"""Hello {user}! A computer is an electronic device that processes data and performs calculations. Here's a comprehensive overview:

🖥️ **What is a Computer:**
A computer is a programmable electronic machine that:
• **Processes data** - Takes input, processes it, and produces output
• **Stores information** - Can save and retrieve data
• **Executes instructions** - Follows programmed commands automatically
• **Performs calculations** - Does mathematical and logical operations

**Main Components:**
• **CPU (Processor)** - The "brain" that executes instructions
• **Memory (RAM)** - Temporary storage for active programs
• **Storage** - Hard drives/SSDs for permanent data storage
• **Input devices** - Keyboard, mouse, touchscreen
• **Output devices** - Monitor, speakers, printer

**Types of Computers:**
• **Desktop** - Stationary computers for office/home use
• **Laptop** - Portable computers with built-in components
• **Server** - Powerful computers that serve other computers
• **Mobile devices** - Smartphones, tablets with computing capabilities

**How it works:** Input → Processing → Output → Storage

Need help with a specific computer issue or want to know more about any component?"""

    elif any(phrase in message_lower for phrase in ['what is software', 'what is a software']):
        return f"""Hello {user}! Software refers to programs and applications that run on computers:

💻 **What is Software:**
Software is a collection of instructions, programs, and data that tells a computer how to work.

**Types of Software:**
• **System Software** - Operating systems (Windows, Linux, macOS)
• **Application Software** - Programs like Microsoft Office, web browsers
• **Programming Software** - Tools for creating other software
• **Firmware** - Low-level software stored in hardware

**Examples:**
• **Operating Systems** - Windows 11, macOS, Ubuntu Linux
• **Productivity** - Microsoft Office, Google Workspace
• **Web Browsers** - Chrome, Firefox, Safari
• **Media** - VLC Player, Photoshop, Spotify
• **Security** - Antivirus programs, firewalls

**Software vs Hardware:**
• **Software** - Programs and instructions (intangible)
• **Hardware** - Physical components you can touch

Need help with installing, troubleshooting, or understanding specific software?"""

    elif any(phrase in message_lower for phrase in ['what is hardware', 'what is a hardware']):
        return f"""Hello {user}! Hardware refers to the physical components of a computer:

🔧 **What is Hardware:**
Hardware consists of all the physical, tangible parts of a computer system.

**Main Hardware Components:**
• **CPU (Central Processing Unit)** - The processor/brain
• **Motherboard** - Main circuit board connecting everything
• **RAM (Memory)** - Temporary storage for active programs
• **Storage** - Hard drives (HDD) or Solid State Drives (SSD)
• **Graphics Card (GPU)** - Processes visual data
• **Power Supply** - Converts AC power to DC for components

**Input/Output Hardware:**
• **Input** - Keyboard, mouse, microphone, camera
• **Output** - Monitor, speakers, printer
• **Storage** - USB drives, external hard drives

**Internal vs External:**
• **Internal** - Components inside the computer case
• **External** - Peripherals connected via cables/wireless

**Hardware vs Software:**
• **Hardware** - Physical components (tangible)
• **Software** - Programs and instructions (intangible)

Having issues with any specific hardware component?"""

    elif any(phrase in message_lower for phrase in ['what is internet', 'what is the internet']):
        return f"""Hello {user}! The Internet is a global network of interconnected computers:

🌐 **What is the Internet:**
The Internet is a worldwide system of computer networks that allows devices to communicate and share information.

**Key Concepts:**
• **Network of Networks** - Connects millions of private, public, academic, business networks
• **Global Communication** - Enables worldwide information sharing
• **Protocols** - Uses standardized rules (TCP/IP) for communication
• **Decentralized** - No single controlling authority

**How it Works:**
• **ISP (Internet Service Provider)** - Provides your internet connection
• **Routers** - Direct data between networks
• **Servers** - Computers that host websites and services
• **DNS** - Translates website names to IP addresses

**Common Internet Services:**
• **World Wide Web (WWW)** - Websites and web pages
• **Email** - Electronic messaging
• **File Transfer** - Sharing files between computers
• **Streaming** - Video, music, live content
• **Social Media** - Platforms for communication and sharing

**Internet vs Web:**
• **Internet** - The infrastructure/network
• **Web** - One service that runs on the Internet

Need help with internet connectivity or understanding how something works online?"""

    # Continue with existing responses for other patterns...
    return _generate_enhanced_fallback_response(message, user)

def _generate_intelligent_response(message: str, user: str) -> str:
    """Generate intelligent responses to ANY user query using AI-like logic."""
    message_lower = message.lower()

    # First try direct answers for specific questions
    direct_answer = _generate_direct_answer_fallback(message, user)
    if "I'd be happy to help explain IT concepts" not in direct_answer:
        return direct_answer

    # AI-like response generation for any query
    return _generate_ai_like_response(message, user)

def _generate_ai_like_response(message: str, user: str) -> str:
    """Generate AI-like responses for any user query."""
    message_lower = message.lower()

    # Programming and Development Questions
    if any(word in message_lower for word in ['python', 'javascript', 'java', 'programming', 'code', 'coding', 'developer', 'api', 'database', 'sql']):
        return f"""Hello {user}! I can help with programming and development questions!

**Programming Languages & Technologies:**
• **Python** - Versatile language for web development, data science, automation
• **JavaScript** - Essential for web development, both frontend and backend
• **Java** - Enterprise applications, Android development
• **SQL** - Database queries and management
• **APIs** - Application Programming Interfaces for system integration

**Development Concepts:**
• **Frontend** - User interface (HTML, CSS, JavaScript, React, Vue)
• **Backend** - Server-side logic (Node.js, Python, Java, databases)
• **Databases** - Data storage (MySQL, PostgreSQL, MongoDB)
• **Version Control** - Git, GitHub for code management

**Common Development Tasks:**
• Setting up development environments
• Debugging code issues
• Database design and optimization
• API integration and testing

What specific programming topic or issue would you like help with?"""

    # Business and Productivity Questions
    elif any(word in message_lower for word in ['excel', 'word', 'powerpoint', 'office', 'microsoft', 'google', 'productivity', 'business']):
        return f"""Hello {user}! I can help with business productivity tools and software!

**Microsoft Office Suite:**
• **Excel** - Spreadsheets, formulas, data analysis, pivot tables
• **Word** - Document creation, formatting, collaboration
• **PowerPoint** - Presentations, slide design, animations
• **Outlook** - Email management, calendar, contacts

**Google Workspace:**
• **Google Sheets** - Online spreadsheets with collaboration
• **Google Docs** - Document editing and sharing
• **Google Slides** - Presentation creation
• **Gmail** - Email with powerful search and organization

**Productivity Tips:**
• Keyboard shortcuts for faster work
• Template creation and reuse
• Collaboration and sharing best practices
• Data organization and analysis

**Common Issues:**
• File compatibility between different versions
• Collaboration and sharing permissions
• Formula troubleshooting in spreadsheets
• Email setup and synchronization

What specific productivity tool or task do you need help with?"""

    # Technology and General IT Questions
    elif any(word in message_lower for word in ['technology', 'tech', 'digital', 'cloud', 'cybersecurity', 'ai', 'artificial intelligence', 'machine learning']):
        return f"""Hello {user}! I can help explain modern technology concepts!

**Cloud Computing:**
• **Public Cloud** - AWS, Azure, Google Cloud services
• **Private Cloud** - Internal company cloud infrastructure
• **Hybrid Cloud** - Combination of public and private
• **SaaS** - Software as a Service (Office 365, Salesforce)

**Cybersecurity:**
• **Firewalls** - Network security barriers
• **Encryption** - Data protection through encoding
• **Multi-factor Authentication** - Enhanced login security
• **Backup & Recovery** - Data protection strategies

**Artificial Intelligence:**
• **Machine Learning** - Systems that learn from data
• **Natural Language Processing** - AI understanding human language
• **Automation** - AI-powered task automation
• **Chatbots** - AI assistants like me!

**Emerging Technologies:**
• Internet of Things (IoT) - Connected smart devices
• Blockchain - Distributed ledger technology
• 5G Networks - Next-generation mobile connectivity
• Edge Computing - Processing data closer to source

What specific technology topic interests you or what issue are you facing?"""

    # General Questions and Explanations
    elif any(phrase in message_lower for phrase in ['what is', 'how does', 'explain', 'tell me about', 'how to', 'why']):
        return f"""Hello {user}! I'm here to help explain and answer your questions!

Based on your question "{message}", I can provide information on a wide range of topics:

**Technology & IT:**
• Computer systems and components
• Software applications and tools
• Network and internet concepts
• Security and data protection

**Business & Productivity:**
• Office software and applications
• Workflow optimization
• Communication tools
• Data management

**Troubleshooting & Support:**
• Common technical issues
• Step-by-step problem solving
• Best practices and recommendations
• Preventive maintenance

**Learning & Development:**
• Technology concepts explained simply
• Practical tips and tricks
• Industry standards and practices
• Career guidance in IT

Could you be more specific about what aspect you'd like me to explain? For example:
• "What is cloud computing?"
• "How does email encryption work?"
• "Explain the difference between RAM and storage"
• "How to troubleshoot slow internet"

I'm here to provide detailed, helpful explanations for any topic you're curious about!"""

    # Problem-solving and Troubleshooting
    elif any(word in message_lower for word in ['problem', 'issue', 'error', 'not working', 'broken', 'fix', 'solve', 'troubleshoot']):
        return f"""Hello {user}! I'm here to help solve your technical problems!

**Common Problem Categories:**

🖥️ **Computer Issues:**
• Slow performance - Check RAM usage, disk space, background programs
• Startup problems - Safe mode, system restore, hardware checks
• Software crashes - Update drivers, reinstall applications, check compatibility

🌐 **Network & Internet:**
• No internet connection - Check cables, restart router, contact ISP
• Slow internet - Speed test, check for interference, optimize settings
• WiFi problems - Password verification, signal strength, router placement

📧 **Email & Communication:**
• Email not sending/receiving - Check settings, internet connection, server status
• Login issues - Password reset, two-factor authentication, account verification
• Synchronization problems - Update settings, check server configuration

🖨️ **Printer & Peripherals:**
• Printer not responding - Check connections, restart devices, update drivers
• Print quality issues - Clean print heads, check ink/toner, paper settings
• Device not recognized - Driver installation, USB port testing, compatibility

**Troubleshooting Steps:**
1. **Identify the problem** - When did it start? What changed?
2. **Basic checks** - Power, connections, recent updates
3. **Restart devices** - Often resolves temporary issues
4. **Check for updates** - Software, drivers, firmware
5. **Test systematically** - Isolate the cause step by step

What specific problem are you experiencing? Describe the issue and I'll provide targeted troubleshooting steps!"""

    # Default comprehensive response for any other query
    else:
        return f"""Hello {user}! I'm your intelligent IT support assistant, and I'm here to help with any question you have!

**I can assist you with:**

🤖 **Any Technology Question:**
• Computer hardware and software
• Internet and networking
• Mobile devices and apps
• Cloud services and digital tools

💼 **Business & Productivity:**
• Microsoft Office (Word, Excel, PowerPoint)
• Google Workspace tools
• Email setup and management
• File sharing and collaboration

🔧 **Technical Support:**
• Troubleshooting any device or software
• Step-by-step problem solving
• Performance optimization
• Security and backup advice

📚 **Learning & Explanation:**
• Technology concepts made simple
• How-to guides and tutorials
• Best practices and recommendations
• Industry insights and trends

**About your question: "{message}"**

I'd be happy to provide a detailed answer! Could you tell me:
• What specific aspect interests you most?
• Are you looking for a general explanation or help with a specific problem?
• What's your current level of experience with this topic?

I'm designed to provide comprehensive, helpful responses to any question - from basic concepts to advanced technical issues. Just let me know what you'd like to learn or what problem you need to solve!

How can I help you today?"""

def _generate_enhanced_fallback_response(message: str, user: str) -> str:
    """Generate an enhanced fallback response when AI is not available."""
    message_lower = message.lower()

    # General greetings and conversational responses
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
        return f"""Hello {user}! 👋 Great to see you! I'm your IT support chatbot assistant.

I'm here to help you with:
• Technical support questions
• Troubleshooting guidance
• Ticket management
• General IT knowledge

How can I assist you today?"""

    # General questions about the chatbot itself
    elif any(word in message_lower for word in ['who are you', 'what are you', 'what can you do', 'help me', 'capabilities']):
        return f"""Hi {user}! I'm your intelligent IT support chatbot! 🤖

**What I can do:**
• Answer technical questions (Windows, Linux, networking, etc.)
• Help troubleshoot common IT issues
• Search our ticket database
• Provide step-by-step guidance
• Find similar resolved tickets
• General IT knowledge and advice

**Try asking me:**
• "What's the difference between Windows and Linux?"
• "How do I troubleshoot network issues?"
• "Search for printer problems"
• "Show my tickets"
• "Help with email setup"

What would you like to know?"""

    # Time and date questions
    elif any(word in message_lower for word in ['time', 'date', 'today', 'what day']):
        from datetime import datetime
        now = datetime.now()
        return f"""Hello {user}!

📅 **Current Date & Time:**
• Date: {now.strftime('%A, %B %d, %Y')}
• Time: {now.strftime('%I:%M %p')}

Is there anything IT-related I can help you with today?"""

    # Weather questions (redirect to IT focus)
    elif any(word in message_lower for word in ['weather', 'temperature', 'rain', 'sunny']):
        return f"""Hello {user}! While I can't check the weather for you, I'm specialized in IT support! 🌤️

I can help you with:
• Computer and network issues
• Software troubleshooting
• Hardware problems
• IT best practices

Is there any technical issue I can assist you with today?"""

    # Specific technical questions
    elif any(word in message_lower for word in ['windows', 'linux', 'difference', 'compare', 'operating system', 'os']):
        return f"""Hello {user}! Great question about operating systems! Here's a comparison:

🖥️ **Windows:**
- User-friendly interface, great for general users
- Wide software compatibility (Office, games, etc.)
- Better hardware driver support
- More expensive (licensing costs)

🐧 **Linux:**
- Open-source and free
- More secure and stable
- Better for servers and development
- Steeper learning curve for beginners

**For IT Support:** Linux is excellent for servers, while Windows is common in office environments.

Would you like me to help you with a specific Windows or Linux issue?"""

    elif any(word in message_lower for word in ['network', 'internet', 'wifi', 'connection', 'connectivity']):
        return f"""Hello {user}! I can help with network issues! Here are some quick troubleshooting steps:

🔧 **Basic Network Troubleshooting:**
1. **Check cables** - Ensure all connections are secure
2. **Restart devices** - Router, modem, and computer
3. **Check IP settings** - Run: `ipconfig /release` then `ipconfig /renew`
4. **Test connectivity** - Run: `ping 8.8.8.8`
5. **Check DNS** - Try: `nslookup google.com`

Need help with a specific network issue? I can search our ticket database for similar problems!"""

    elif any(word in message_lower for word in ['printer', 'print', 'printing']):
        return f"""Hello {user}! Printer issues are common! Here's how to troubleshoot:

🖨️ **Printer Troubleshooting:**
1. **Check connections** - USB/Network cables secure
2. **Restart printer** - Turn off for 30 seconds, then on
3. **Check print queue** - Clear any stuck jobs
4. **Update drivers** - Download latest from manufacturer
5. **Test print** - Try printing a test page

What specific printer issue are you experiencing?"""

    elif any(word in message_lower for word in ['email', 'outlook', 'mail']):
        return f"""Hello {user}! Email problems can be frustrating! Here's what to check:

📧 **Email Troubleshooting:**
1. **Check internet** - Ensure you're connected
2. **Verify settings** - Server, port, authentication
3. **Clear cache** - Close and restart email client
4. **Check storage** - Mailbox might be full
5. **Test webmail** - Try accessing via browser

Having trouble with Outlook or another email client?"""

    # General knowledge questions
    elif any(word in message_lower for word in ['how to', 'what is', 'explain', 'define']):
        return f"""Hello {user}! I'd be happy to help explain IT concepts!

I can provide information about:
• Computer hardware and software
• Networking concepts
• Security best practices
• Troubleshooting procedures
• IT terminology

Could you be more specific about what you'd like me to explain? For example:
• "What is a firewall?"
• "How to set up a VPN?"
• "Explain DNS resolution"
• "What are the different types of malware?"

What would you like to learn about?"""

    # Thank you responses
    elif any(word in message_lower for word in ['thank you', 'thanks', 'appreciate']):
        return f"""You're very welcome, {user}! 😊

I'm always here to help with your IT support needs. Feel free to ask me anything about:
• Technical troubleshooting
• IT best practices
• System administration
• Software issues

Have a great day, and don't hesitate to reach out if you need more assistance!"""

    # Default response for general questions
    else:
        return f"""Hello {user}! I'm your IT support chatbot assistant! 🤖

I can help you with a wide range of topics:

**Technical Support:**
• Troubleshooting computer issues
• Network connectivity problems
• Software installation and configuration
• Hardware diagnostics

**General IT Knowledge:**
• Operating systems (Windows, Linux, macOS)
• Security best practices
• Email and communication tools
• System administration

**Ticket Management:**
• Search our ticket database
• Find similar resolved issues
• Look up your assigned tickets

What would you like to know or what issue can I help you resolve today?"""

# Additional endpoints without authentication
@router.get("/health")
async def health_check():
    """Health Check endpoint for chatbot service."""
    return {
        "status": "ok",
        "service": "chatbot",
        "timestamp": datetime.now()
    }

@router.get("/")
async def read_root():
    """Root endpoint for chatbot service."""
    return {
        "message": "Chatbot API is running",
        "version": "1.0.0",
        "available_endpoints": [
            "GET /chatbot/tickets/my",
            "GET /chatbot/tickets/{ticket_id}",
            "GET /chatbot/tickets/search",
            "GET /chatbot/tickets/similar/{ticket_number}",
            "POST /chatbot/chat",
            "GET /chatbot/health",
            "GET /chatbot/debug",
            "GET /chatbot/"
        ]
    }
