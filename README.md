# TeamLogic AutoTask - IT Support Ticket Management System

A comprehensive AI-powered IT support ticket management system built with Streamlit and Snowflake Cortex LLM.

## 🚀 Features

- **Automated Email Processing**: IMAP integration for automatic ticket creation from emails
- **AI-Powered Classification**: Snowflake Cortex LLM for intelligent ticket categorization
- **Smart Assignment**: Skill-based technician assignment with workload balancing
- **Resolution Generation**: AI-generated resolution suggestions based on historical data
- **Email Notifications**: Automated confirmation emails to users
- **Knowledge Management**: Persistent knowledge base with similar ticket tracking
- **Real-time Dashboard**: Interactive Streamlit interface with analytics

## 📁 Project Structure

```
teamlogic-autotask/
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (not in repo)
├── config.py                      # Configuration settings
├── backend/                       # FastAPI backend server
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

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   ```
   Activate it (you must do this every time before running the app):
   - Windows (PowerShell):
     ```powershell
     venv\Scripts\Activate.ps1
     ```
   - Windows (cmd):
     ```cmd
     venv\Scripts\activate.bat
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file with:
   ```env
   # Snowflake Configuration for SSO Authentication
   SF_ACCOUNT=your_account
   SF_USER=your_username
   SF_WAREHOUSE=your_warehouse
   SF_DATABASE=your_database
   SF_SCHEMA=your_schema
   SF_ROLE=your_role

   # Email Configuration
   EMAIL_ACCOUNT=your_email_account
   SUPPORT_EMAIL_PASSWORD=your_app_password
   IMAP_SERVER=imap.gmail.com
   EMAIL_FOLDER=inbox

   # Support Contact Info
   SUPPORT_PHONE=your_phone
   SUPPORT_EMAIL=your_email
   ```



## 🔧 Configuration

### Snowflake Setup
- Ensure you have access to Snowflake Cortex LLM
- Create tables: `COMPANY_4130_DATA`, `TECHNICIAN_DUMMY_DATA`
- Configure MFA if required

### Email Setup
- Use Gmail with App Password for IMAP/SMTP
- Configure email monitoring settings in `config.py`

## 📊 Usage

1. **Manual Ticket Creation**: Use the web interface to submit tickets
2. **Email Integration**: Send emails to monitored inbox for automatic processing
3. **Dashboard**: View ticket analytics and recent activity
4. **Assignment**: Tickets are automatically assigned to best-matched technicians

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
