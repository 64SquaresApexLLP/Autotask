"""Configuration settings for the Technician Chatbot application."""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

# Load environment variables from .env file
from dotenv import load_dotenv

# Find the .env file in the project root (two levels up from backend/)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Snowflake Database Configuration
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str = ""
    snowflake_authenticator: str = "externalbrowser"
    snowflake_database: str = "TEST_DB"
    snowflake_schema: str = "PUBLIC"
    snowflake_warehouse: str = "S_WHH"
    snowflake_role: str = "ACCOUNTADMIN"
    
    # JWT Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # LLM APIs (optional)
    openai_api_key: str = ""
    groq_api_key: str = ""
    
    # Application Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # CORS Configuration
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
