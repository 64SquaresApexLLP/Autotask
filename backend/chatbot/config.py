"""Configuration settings for the Technician Chatbot application."""

import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
from dotenv import load_dotenv

# Find the .env file in the project root (two levels up from backend/)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Snowflake Database Configuration (using standardized variable names)
    snowflake_account: str = Field(env="SNOWFLAKE_ACCOUNT")
    snowflake_user: str = Field(env="SNOWFLAKE_USER")
    snowflake_password: str = Field(default="", env="SNOWFLAKE_PASSWORD")
    snowflake_authenticator: str = Field(default="externalbrowser", env="SNOWFLAKE_AUTHENTICATOR")
    snowflake_database: str = Field(default="TEST_DB", env="SNOWFLAKE_DATABASE")
    snowflake_schema: str = Field(default="PUBLIC", env="SNOWFLAKE_SCHEMA")
    snowflake_warehouse: str = Field(default="S_WHH", env="SNOWFLAKE_WAREHOUSE")
    snowflake_role: str = Field(default="ACCOUNTADMIN", env="SNOWFLAKE_ROLE")
    
    # JWT Authentication (using standardized variable names)
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # LLM APIs (using standardized variable names)
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    
    # Application Configuration (using standardized variable names)
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Logging (using standardized variable names)
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # CORS Configuration (using standardized variable names)
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000", env="ALLOWED_ORIGINS")

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()
