# LLM-Based Notification System

## Overview

The notification system has been completely rewritten from scratch to use LLM (Large Language Model) for generating dynamic, contextual email notifications based on ticket metadata. This replaces the previous rule-based template system with an intelligent AI-powered approach.

## Key Features

### 🤖 LLM-Powered Content Generation
- Uses Snowflake Cortex LLM (mixtral-8x7b) to generate email content
- Dynamic content based on ticket metadata and context
- Contextually appropriate tone for different recipient types
- Intelligent inclusion of relevant technical details

### 🎯 Recipient-Aware Messaging
- **Customer**: Friendly, empathetic, and reassuring tone
- **Technician**: Professional, direct, and action-oriented tone  
- **Manager**: Formal, concise, and informative tone
- **Team**: Collaborative and informative tone

### 📧 Multiple Notification Types
- **Confirmation**: Customer ticket confirmation with AI resolution steps
- **Assignment**: Technician assignment with comprehensive details
- **Status Update**: Progress updates with context and next steps
- **Escalation**: Urgent notifications with escalation reasons
- **Resolution**: Completion notifications with solution summaries

### 🛡️ Robust Fallback System
- Graceful fallback to basic templates when LLM is unavailable
- No service interruption if database connection fails
- Maintains functionality even without LLM access

### 🔄 Backward Compatibility
- Same public interface as the original system
- All existing code continues to work without changes
- Drop-in replacement for the old notification agent

## Architecture

```
NotificationAgent
├── LLM Integration (Snowflake Cortex)
├── SMTP Email Sending
├── Template Fallback System
└── Convenience Methods
```

### Core Methods

#### `generate_email_notification(notification_type, ticket_data, recipient_type)`
Main method that generates email content using LLM or templates.

#### `send_email(recipient_email, email_content)`
Handles SMTP email sending with HTML and text versions.

#### Convenience Methods (Backward Compatibility)
- `send_ticket_confirmation(user_email, ticket_data, ticket_number)`
- `send_technician_assignment(technician_email, ticket_data, ticket_number)`

## Usage

### Basic Usage (Template Mode)
```python
from src.agents.notification_agent import NotificationAgent

# Initialize without database connection (uses templates)
agent = NotificationAgent()

# Generate email content
email_content = agent.generate_email_notification(
    notification_type='confirmation',
    ticket_data=ticket_data,
    recipient_type='customer'
)

# Send email
agent.send_email('user@company.com', email_content)
```

### LLM-Enabled Usage
```python
from src.database import SnowflakeConnection
from src.agents.notification_agent import NotificationAgent

# Initialize with database connection (enables LLM)
db_connection = SnowflakeConnection(...)
agent = NotificationAgent(db_connection)

# Same interface - now with LLM power!
email_content = agent.generate_email_notification(
    notification_type='confirmation',
    ticket_data=ticket_data,
    recipient_type='customer'
)
```

### Backward Compatibility
```python
# Existing code works unchanged
agent.send_ticket_confirmation(
    user_email='user@company.com',
    ticket_data=ticket_data,
    ticket_number='TL-2024-001'
)
```

## Ticket Data Structure

The system expects ticket data with the following structure:

```python
ticket_data = {
    "ticket_number": "TL-2024-001",
    "title": "Issue title",
    "name": "Customer Name",
    "user_email": "customer@company.com",
    "description": "Issue description",
    "date": "2024-01-15",
    "time": "10:30:00",
    "due_date": "2024-01-17",
    "classified_data": {
        "PRIORITY": {"Label": "High"},
        "ISSUETYPE": {"Label": "Email Issues"},
        "TICKETTYPE": {"Label": "Service Request"}
    },
    "extracted_metadata": {
        "main_issue": "Main issue description",
        "affected_systems": ["System1", "System2"],
        "error_messages": "Error details",
        "urgency_indicators": ["Indicator1", "Indicator2"]
    },
    "resolution_note": "AI-generated resolution steps",
    "assignment_result": {
        "assigned_technician": "Tech Name",
        "technician_email": "tech@company.com"
    }
}
```

## Configuration

### Environment Variables
- `SMTP_SERVER`: SMTP server address (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP port (default: 587)
- `SMTP_USERNAME`: SMTP username
- `SMTP_PASSWORD`: SMTP password (required for email sending)
- `FROM_EMAIL`: From email address
- `FROM_NAME`: From name (default: TeamLogic Support)

### LLM Configuration
- Model: `mixtral-8x7b` (Snowflake Cortex)
- Expects JSON response format
- Automatic fallback on LLM errors

## Benefits Over Previous System

### ✅ Before (Rule-Based)
- Static email templates
- Limited customization
- Manual template maintenance
- Fixed content structure

### 🚀 After (LLM-Based)
- Dynamic content generation
- Context-aware messaging
- Automatic tone adaptation
- Rich metadata integration
- Professional formatting
- Intelligent content selection

## Testing

Run the demo script to see the system in action:

```bash
cd Autotask
python demo_llm_notifications.py
```

This will demonstrate:
- Different notification types
- Template fallback functionality
- Backward compatibility
- Content generation examples

## Integration

The system is automatically integrated into the main ticket processing workflow:

1. **Intake Agent** initializes NotificationAgent with database connection
2. **Ticket Processing** generates rich metadata
3. **Notification Agent** uses LLM to create contextual emails
4. **SMTP Sending** delivers professional notifications

## Error Handling

- **LLM Unavailable**: Falls back to basic templates
- **SMTP Disabled**: Logs warning, returns false
- **Invalid Data**: Handles gracefully with defaults
- **Network Issues**: Automatic retry and fallback

## Future Enhancements

- Additional notification types (reminders, feedback requests)
- Multi-language support
- Email template customization via LLM
- Advanced recipient targeting
- Analytics and email performance tracking

## Conclusion

The new LLM-based notification system provides intelligent, contextual email generation while maintaining full backward compatibility. It represents a significant upgrade from static templates to dynamic, AI-powered communications that adapt to each ticket's unique context and recipient needs.
