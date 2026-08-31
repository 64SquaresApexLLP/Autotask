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

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file with:
   ```env
   # Snowflake Configuration for Key-Pair (RSA) Authentication — no password / no MFA/TOTP
   SF_ACCOUNT=your_account
   SF_USER=your_username
   SF_AUTHENTICATOR=keypair
   SF_PRIVATE_KEY_PATH=/absolute/path/to/rsa_key.p8
   SF_PRIVATE_KEY_PWD=

   # Email Configuration
   EMAIL_ACCOUNT=your_email_account
   SUPPORT_EMAIL_PASSWORD=your_app_password
   IMAP_SERVER=imap.gmail.com
   EMAIL_FOLDER=inbox

   # Support Contact Info
   SUPPORT_PHONE=your_phone
   SUPPORT_EMAIL=your_email
   ```

### 🔑 Snowflake Key-Pair (RSA) Authentication (recommended)
The app authenticates to Snowflake with an RSA key pair instead of a password/TOTP, so the
service account never triggers an MFA prompt. One-time setup (as the account owner):

```bash
# 1. Generate the key pair (or run the bundled helper)
openssl genrsa 2048 2>/dev/null | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8 -nocrypt
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub

# 2. Register the public key on the Snowflake user (AccountAdmin)
#    ALTER USER ATISHC SET RSA_PUBLIC_KEY='<contents of rsa_key.pub, base64 body only>';

# 3. Or let the helper generate + print + optionally register + verify everything:
python scripts/setup_keypair_auth.py            # generate keys + print ALTER USER
python scripts/setup_keypair_auth.py --register # also run the ALTER USER (needs password in .env, one-time)
python scripts/setup_keypair_auth.py --test     # verify key-pair connection only
```

Connect points already wired for key-pair auth: `src/database/snowflake_db.py`
(`SnowflakeConnection`, used by the backend/site uploader), the chatbot Cortex
`llm_service`, and the chatbot SQLAlchemy engine. Set `SF_AUTHENTICATOR=keypair`
(and the `SNOWFLAKE_*` aliases in `.env`) and ensure `SF_PASSWORD`/`SF_PASSCODE`
are blank — then no password and no TOTP is ever used for this account.



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
