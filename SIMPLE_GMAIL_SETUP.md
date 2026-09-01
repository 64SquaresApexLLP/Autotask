# Simple Gmail Real-time Setup

## Overview
This is a **simplified Gmail integration** that uses your existing `credentials.json` file to authenticate with `venkatehp12@gmail.com` and monitor for new emails in real-time.

## ✅ What You Have
- ✅ `client_secret_826171701006-6biqf0hffn6bhvit91tp0j015beo10s7.apps.googleusercontent.com.json`
- ✅ FastAPI backend with webhook endpoint
- ✅ Intake agent for ticket processing

## 🚀 Quick Setup (3 Steps)

### Step 1: Authenticate Gmail
```bash
cd Autotask
source venv/bin/activate
python gmail_simple_auth.py
```

**What this does:**
- Uses your existing credentials.json
- Opens browser for OAuth with venkatehp12@gmail.com
- Creates token.json for future use
- Validates you're connected to the correct account

### Step 2: Start Backend
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**What this does:**
- Starts FastAPI server on port 8001
- Provides webhook endpoint: `/webhooks/gmail/simple`
- Ready to receive and process emails

### Step 3: Start Email Monitor
```bash
# In a new terminal
cd Autotask
source venv/bin/activate
python gmail_monitor_simple.py
```

**What this does:**
- Monitors venkatehp12@gmail.com for new emails
- Sends new emails to webhook for processing
- Creates tickets automatically via intake agent

## 🧪 Testing

1. **Send a test email** to `venkatehp12@gmail.com`
2. **Watch the monitor logs** for email detection
3. **Check backend logs** for ticket creation
4. **Verify ticket** was created successfully

## 📊 How It Works

```
📧 Email arrives at venkatehp12@gmail.com
    ↓
🔍 Gmail Monitor detects new email (every 5 seconds)
    ↓
📡 Sends email data to webhook: /webhooks/gmail/simple
    ↓
🤖 Intake Agent processes email
    ↓
🎫 Creates ticket with AI classification
    ↓
👨‍💻 Assigns to appropriate technician
```

## 🔧 Configuration

### Email Monitoring
- **Check interval:** 5 seconds
- **Target account:** venkatehp12@gmail.com
- **Webhook URL:** http://localhost:8001/webhooks/gmail/simple

### Authentication
- **Credentials file:** Your existing credentials.json
- **Token file:** token.json (created automatically)
- **Scopes:** Gmail read and modify

## 📋 Troubleshooting

### Authentication Issues
```bash
# If wrong account is selected
rm token.json
python gmail_simple_auth.py

# Make sure to select venkatehp12@gmail.com in browser
```

### Monitor Not Starting
```bash
# Check if token exists
ls -la token.json

# Re-authenticate if needed
python gmail_simple_auth.py
```

### Webhook Errors
```bash
# Check if backend is running
curl http://localhost:8001/webhooks/gmail/simple

# Should return method not allowed (405) - that's normal
```

## 🎯 Expected Output

### Authentication Success
```
🎉 Successfully authenticated with: venkatehp12@gmail.com
📊 Total messages: 1234
📊 Total threads: 567
✅ Token saved for future use
```

### Monitor Running
```
🔍 Starting email monitoring (checking every 5 seconds)
📧 Send an email to venkatehp12@gmail.com to test!
🚨 Only NEW emails will be processed!
```

### Email Processing
```
🚨 NEW EMAIL DETECTED!
📧 Processing: Test Support Request
   From: John Doe <john@example.com>
✅ Email processed successfully!
🎫 Ticket created: TL-2024-001
```

## 🔄 Daily Usage

1. **Start backend:** `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8001`
2. **Start monitor:** `python gmail_monitor_simple.py`
3. **Send emails** to venkatehp12@gmail.com
4. **Watch automatic** ticket creation

## 🛑 Stopping

- **Stop monitor:** Press `Ctrl+C` in monitor terminal
- **Stop backend:** Press `Ctrl+C` in backend terminal

## 📈 Advantages

✅ **Simple setup** - No complex Pub/Sub configuration  
✅ **Uses existing credentials** - Your credentials.json works  
✅ **Real-time processing** - 5-second check interval  
✅ **Automatic validation** - Ensures correct email account  
✅ **Error handling** - Robust error recovery  
✅ **Event-driven** - Only processes NEW emails  

---

**🎉 Ready to start? Run the 3 commands above and you'll have real-time email processing!**
