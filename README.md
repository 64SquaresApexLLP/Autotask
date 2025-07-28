# TeamLogic AutoTask - IT Support Ticket Management System

A comprehensive AI-powered IT support ticket management system built with Snowflake Cortex LLM.

## 🚀 Features

- **Automated Email Processing**: IMAP integration for automatic ticket creation from emails
- **AI-Powered Classification**: Snowflake Cortex LLM for intelligent ticket categorization
- **Smart Assignment**: Skill-based technician assignment with workload balancing
- **Resolution Generation**: AI-generated resolution suggestions based on historical data
- **Email Notifications**: Automated confirmation emails to users
- **Knowledge Management**: Persistent knowledge base with similar ticket tracking
- **Core Processing Engine**: Backend processing without UI dependencies
- **FastAPI Backend**: RESTful API with complete AI workflow integration
- **Swagger Documentation**: Interactive API documentation with testing interface

## 📁 Project Structure

```
teamlogic-autotask/
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (not in repo)
├── app.py                         # Main Streamlit application
├── config.py                      # Configuration settings
├── start_backend.py               # FastAPI backend starter script
│
├── backend/                       # FastAPI Backend
│   ├── main.py                    # Main FastAPI application
│   ├── run.py                     # Backend runner script
│   ├── test_api.py                # API testing script
│   ├── requirements.txt           # Backend dependencies
│   ├── README.md                  # Backend documentation
│   └── API_ENDPOINTS.md           # Complete API documentation
│
├── src/                           # Source code
│   ├── agents/                    # AI Agents
│   │   ├── intake_agent.py        # Main orchestrator agent
│   │   ├── assignment_agent.py    # Technician assignment logic
│   │   └── notification_agent.py  # Email notification handler
│   │
│   ├── processors/                # Data processors
│   │   ├── ai_processor.py        # AI/LLM processing
│   │   ├── ticket_processor.py    # Ticket similarity matching
│   │   └── image_processor.py     # Image/OCR processing
│   │
│   ├── database/                  # Database layer
│   │   └── snowflake_db.py        # Snowflake connection & queries
│   │
│   ├── data/                      # Data management
│   │   └── data_manager.py        # Knowledge base operations
│   │
│   └── ui/                        # UI components
│       └── components.py          # Streamlit UI components
│
├── data/                          # Data files
│   ├── reference_data.txt         # Classification reference data
│   ├── knowledgebase.json         # Ticket knowledge base
│   └── ticket_sequence.json       # Ticket numbering sequence
│
├── logs/                          # Log files
└── docs/                          # Documentation
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd teamlogic-autotask
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file with:
   ```env
   # Snowflake Configuration
   SF_ACCOUNT=your_account
   SF_USER=your_username
   SF_PASSWORD=your_password
   SF_WAREHOUSE=your_warehouse
   SF_DATABASE=your_database
   SF_SCHEMA=your_schema
   SF_ROLE=your_role
   SF_PASSCODE=your_mfa_code

   # Email Configuration
   SUPPORT_EMAIL_PASSWORD=your_app_password
   SUPPORT_PHONE=your_phone
   SUPPORT_EMAIL=your_email
   ```

4. **Run the application**
   
   **Option A: Streamlit Frontend**
   ```bash
   streamlit run app.py
   ```
   
   **Option B: FastAPI Backend**
   ```bash
   # Using the starter script
   python start_backend.py
   
   # Or directly with uvicorn
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   
   **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

### Snowflake Setup
- Ensure you have access to Snowflake Cortex LLM
- Create tables: `COMPANY_4130_DATA`, `TECHNICIAN_DUMMY_DATA`
- Configure MFA if required

### Email Setup
- Use Gmail with App Password for IMAP/SMTP
- Configure email monitoring settings in `config.py`

## 📊 Usage

### Web Interface (Streamlit)
1. **Manual Ticket Creation**: Use the web interface to submit tickets
2. **Email Integration**: Send emails to monitored inbox for automatic processing
3. **Dashboard**: View ticket analytics and recent activity
4. **Assignment**: Tickets are automatically assigned to best-matched technicians

### API Interface (FastAPI)
1. **Create Tickets**: POST `/tickets` with title, description, and due date
2. **Get Ticket Details**: GET `/tickets/{ticket_number}`
3. **Get Assigned Technician**: GET `/tickets/{ticket_number}/technician`
4. **List All Tickets**: GET `/tickets` with optional filtering and pagination
5. **Health Check**: GET `/health` for monitoring

**API Documentation**: http://localhost:8000/docs

## 🔄 Workflow

1. **Intake** → Email/Manual input processed
2. **Extraction** → AI extracts metadata from description
3. **Classification** → LLM categorizes ticket (type, priority, etc.)
4. **Assignment** → Algorithm assigns to best technician
5. **Resolution** → AI generates resolution suggestions
6. **Notification** → Email confirmation sent to user
7. **Storage** → Ticket saved to knowledge base

## 🧪 Testing

Run the application and test with sample tickets to ensure all components work correctly.

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]
