"""Chatbot API Router for Autotask integration with exact functionality specifications."""

import logging
import jwt
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Global variables to store connections (will be set by main app)
snowflake_conn = None
llm_service = None

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

# Security
security = HTTPBearer()

# JWT Configuration (from .env)
JWT_SECRET_KEY = "your-secret-key-here-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    timestamp: datetime = datetime.now()

class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_technician: Optional[str] = None

class SearchCriteria(BaseModel):
    query: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_technician: Optional[str] = None

# Helper Functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token."""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# 1. POST /chatbot/auth/login – Allows user login (authentication) and give access_token for authentication
@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Allows user login (authentication) and gives access_token for authentication."""
    try:
        # Simple authentication - validate username and password
        # In production, this should validate against a real user database
        if not request.username or not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and password are required"
            )

        # For demo purposes, accept any non-empty credentials
        # In production, validate against database
        if len(request.username) > 0 and len(request.password) > 0:
            # Create JWT token
            access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": request.username}, expires_delta=access_token_expires
            )
            return TokenResponse(access_token=access_token, token_type="bearer")
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# 2. GET /chatbot/tickets/my – Retrieves tickets assigned to the logged-in user
@router.get("/tickets/my", response_model=List[TicketResponse])
async def get_my_tickets(current_user: str = Depends(verify_token)):
    """Retrieves tickets assigned to the logged-in user."""
    try:
        if not snowflake_conn:
            # Fallback to mock data if no database connection
            return [
                TicketResponse(
                    ticket_id="T20250730.0001",
                    title="Network Issue (Mock)",
                    description="Network connectivity problem - Database not connected",
                    status="Open",
                    priority="High",
                    assigned_technician=current_user
                )
            ]

        # Query real tickets from database assigned to current user
        query = f"""
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, TECHNICIANEMAIL
            FROM TEST_DB.PUBLIC.TICKETS
            WHERE TECHNICIANEMAIL = %s
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
                status=row.get('STATUS') or 'Open',  # Default to 'Open' if None
                priority=row.get('PRIORITY') or 'Medium',  # Default to 'Medium' if None
                assigned_technician=row.get('TECHNICIANEMAIL', '')
            ))

        return tickets

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching my tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickets: {str(e)}")

# 4. GET /chatbot/tickets/search – Searches for tickets based on provided criteria
@router.get("/tickets/search", response_model=List[TicketResponse])
async def search_tickets(
    q: str = Query(..., description="Search query"),
    current_user: str = Depends(verify_token)
):
    """Searches for tickets based on provided criteria."""
    try:
        if not snowflake_conn:
            # Fallback to mock data if no database connection
            return [
                TicketResponse(
                    ticket_id="T20250730.0003",
                    title=f"Search result for: {q} (Mock)",
                    description=f"Ticket matching search query: {q} - Database not connected",
                    status="Open",
                    priority="Medium",
                    assigned_technician=current_user
                )
            ]

        # Search real tickets from database
        search_term = f"%{q}%"
        query = f"""
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, TECHNICIANEMAIL
            FROM TEST_DB.PUBLIC.TICKETS
            WHERE UPPER(TITLE) LIKE UPPER('{search_term}')
               OR UPPER(DESCRIPTION) LIKE UPPER('{search_term}')
            ORDER BY TICKETNUMBER DESC
            LIMIT 20
        """
        results = snowflake_conn.execute_query(query)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search tickets: {str(e)}")

# 3. GET /chatbot/tickets/{ticket_id} – Fetches detailed information for a specific ticket by using ticket number
@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, current_user: str = Depends(verify_token)):
    """Fetches detailed information for a specific ticket by using ticket number."""
    try:
        if not snowflake_conn:
            # Fallback to mock data if no database connection
            return TicketResponse(
                ticket_id=ticket_id,
                title="Sample Ticket (Mock)",
                description="This is a sample ticket description - Database not connected",
                status="Open",
                priority="Medium",
                assigned_technician=current_user
            )

        # Query specific ticket from database
        query = f"""
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, TECHNICIANEMAIL
            FROM TEST_DB.PUBLIC.TICKETS
            WHERE TICKETNUMBER = '{ticket_id}'
        """
        results = snowflake_conn.execute_query(query)

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

# 5. GET /chatbot/tickets/similar/{ticket_number} – Finds tickets similar to the specified ticket number
@router.get("/tickets/similar/{ticket_number}", response_model=List[TicketResponse])
async def find_similar_tickets(
    ticket_number: str,
    current_user: str = Depends(verify_token)
):
    """Finds tickets similar to the specified ticket number."""
    try:
        if not snowflake_conn:
            # Fallback to mock data if no database connection
            return [
                TicketResponse(
                    ticket_id="T20250730.0004",
                    title="Similar Issue 1 (Mock)",
                    description="Similar ticket description - Database not connected",
                    status="Resolved",
                    priority="Medium",
                    assigned_technician=current_user
                ),
                TicketResponse(
                    ticket_id="T20250730.0005",
                    title="Similar Issue 2 (Mock)",
                    description="Another similar ticket - Database not connected",
                    status="Open",
                    priority="Low",
                    assigned_technician=current_user
                )
            ]

        # First, get the original ticket to find similar ones
        original_query = f"""
            SELECT TITLE, DESCRIPTION, STATUS, PRIORITY
            FROM TEST_DB.PUBLIC.TICKETS
            WHERE TICKETNUMBER = '{ticket_number}'
        """
        original_results = snowflake_conn.execute_query(original_query)

        if not original_results:
            raise HTTPException(status_code=404, detail="Original ticket not found")

        original_ticket = original_results[0]
        original_title = original_ticket.get('TITLE', '')
        original_description = original_ticket.get('DESCRIPTION', '')

        # Find similar tickets based on title and description keywords
        # Simple similarity search using common words
        title_words = original_title.split()[:3]  # Take first 3 words
        desc_words = original_description.split()[:5]  # Take first 5 words

        similar_conditions = []
        for word in title_words + desc_words:
            if len(word) > 3:  # Only use words longer than 3 characters
                similar_conditions.append(f"UPPER(TITLE) LIKE UPPER('%{word}%') OR UPPER(DESCRIPTION) LIKE UPPER('%{word}%')")

        if similar_conditions:
            similarity_query = f"""
                SELECT TICKETNUMBER, TITLE, DESCRIPTION, STATUS, PRIORITY, TECHNICIANEMAIL
                FROM TEST_DB.PUBLIC.TICKETS
                WHERE TICKETNUMBER != '{ticket_number}'
                AND ({' OR '.join(similar_conditions)})
                ORDER BY TICKETNUMBER DESC
                LIMIT 10
            """
            results = snowflake_conn.execute_query(similarity_query)
        else:
            results = []

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar tickets for {ticket_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to find similar tickets: {str(e)}")

# 6. POST /chatbot/chat – Sends a chat message to the chatbot for the resolution and general message
@router.post("/chat", response_model=ChatResponse)
async def chat_message(
    message: ChatMessage,
    current_user: str = Depends(verify_token)
):
    """Sends a chat message to the chatbot for the resolution and general message."""
    try:
        user_message = message.message.strip()

        # ALWAYS try to use LLM service first for ALL questions
        if llm_service:
            try:
                # Try conversational response first for all questions
                ai_response = llm_service.generate_conversational_response(
                    context_type="general_technical_support",
                    user_message=user_message,
                    conversation_history=[]
                )
                if ai_response and len(ai_response.strip()) > 10:  # Valid response
                    return ChatResponse(response=ai_response)

            except Exception as e:
                logger.error(f"Error calling Cortex AI conversational: {e}")

            # If conversational fails, try interactive AI resolution
            try:
                ai_response = llm_service.generate_interactive_ai_resolution(
                    user_problem=user_message,
                    conversation_history=[],
                    similar_tickets=[],
                    metadata={"user": current_user}
                )
                if ai_response and len(ai_response.strip()) > 10:  # Valid response
                    return ChatResponse(response=ai_response)

            except Exception as e:
                logger.error(f"Error calling Cortex AI interactive: {e}")

        # Enhanced fallback with intelligent responses for ANY question
        response_text = _generate_intelligent_response(user_message, current_user)
        return ChatResponse(response=response_text)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Error processing chat message")

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

# Additional endpoints with authentication
@router.get("/health")
async def health_check(current_user: str = Depends(verify_token)):
    """Health Check endpoint for chatbot service (requires authentication)."""
    return {
        "status": "ok",
        "service": "chatbot",
        "user": current_user,
        "timestamp": datetime.now()
    }

@router.get("/")
async def read_root(current_user: str = Depends(verify_token)):
    """Root endpoint for chatbot service (requires authentication)."""
    return {
        "message": "Chatbot API is running",
        "version": "1.0.0",
        "user": current_user,
        "authenticated_endpoints": [
            "POST /chatbot/auth/login",
            "GET /chatbot/tickets/my",
            "GET /chatbot/tickets/{ticket_id}",
            "GET /chatbot/tickets/search",
            "GET /chatbot/tickets/similar/{ticket_number}",
            "POST /chatbot/chat",
            "GET /chatbot/health",
            "GET /chatbot/"
        ]
    }
