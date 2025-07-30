"""
Webhook Configuration for Autotask Integration
"""

import os
from typing import Optional

class WebhookConfig:
    """Configuration class for webhook settings"""
    
    # Webhook Security
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-key")
    
    # Autotask Integration URLs
    AUTOTASK_WEBHOOK_URL: str = os.getenv("AUTOTASK_WEBHOOK_URL", "")
    AUTOTASK_API_URL: str = os.getenv("AUTOTASK_API_URL", "")
    AUTOTASK_API_KEY: str = os.getenv("AUTOTASK_API_KEY", "")
    
    # Webhook Endpoints
    INBOUND_WEBHOOK_PATH: str = "/webhooks/autotask/inbound"
    ASSIGNMENT_WEBHOOK_PATH: str = "/webhooks/autotask/assignment"
    NOTIFICATION_WEBHOOK_PATH: str = "/webhooks/autotask/notification"
    
    # Security Settings
    VERIFY_SIGNATURES: bool = os.getenv("VERIFY_WEBHOOK_SIGNATURES", "true").lower() == "true"
    ALLOWED_IPS: list = os.getenv("WEBHOOK_ALLOWED_IPS", "").split(",") if os.getenv("WEBHOOK_ALLOWED_IPS") else []
    
    # Timeout Settings
    WEBHOOK_TIMEOUT: int = int(os.getenv("WEBHOOK_TIMEOUT", "30"))
    RETRY_ATTEMPTS: int = int(os.getenv("WEBHOOK_RETRY_ATTEMPTS", "3"))
    
    # Logging
    LOG_WEBHOOK_REQUESTS: bool = os.getenv("LOG_WEBHOOK_REQUESTS", "true").lower() == "true"
    LOG_WEBHOOK_RESPONSES: bool = os.getenv("LOG_WEBHOOK_RESPONSES", "true").lower() == "true"
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if webhook is properly configured"""
        return bool(cls.WEBHOOK_SECRET and cls.AUTOTASK_WEBHOOK_URL)
    
    @classmethod
    def get_full_webhook_url(cls, path: str) -> str:
        """Get full webhook URL for a given path"""
        base_url = cls.AUTOTASK_WEBHOOK_URL.rstrip('/')
        path = path.lstrip('/')
        return f"{base_url}/{path}"

# Default configuration instance
webhook_config = WebhookConfig()
