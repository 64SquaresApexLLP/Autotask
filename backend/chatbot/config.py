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
    
    # Snowflake Database Configuration
    # Read the SF_* names actually populated in .env (the rest of the app looks
    # for SNOWFLAKE_* names instead, which aren't set, so those always fell back
    # to stale/empty values). This Snowflake account is SSO-federated: the
    # SF_PASSWORD value in .env does not work for password-based login (verified
    # directly against Snowflake - "Incorrect username or password"), so the
    # authenticator must stay "externalbrowser" to match the connection method
    # the rest of the app already uses successfully.
    #
    # snowflake_user is a deliberate exception: .env's SF_USER ("AnantL") does
    # NOT match the identity actually logged into the SSO provider in the
    # browser - verified directly against Snowflake ("The user you were trying
    # to authenticate as differs from the user currently logged in at the
    # IDP"). The project-root config.py never reads SF_USER either; it looks
    # for SNOWFLAKE_USER (also unset in .env) and falls back to
    # "anant.lad@64-squares.com", which is the identity that actually works
    # (proven by the main app's ticket queries succeeding). Mirror that here.
    snowflake_account: str = Field(default="", validation_alias="SF_ACCOUNT")
    snowflake_user: str = Field(default="anant.lad@64-squares.com", validation_alias="SNOWFLAKE_USER")
    snowflake_password: str = Field(default="", validation_alias="SF_PASSWORD")
    snowflake_authenticator: str = Field(default="externalbrowser", validation_alias="SF_AUTHENTICATOR")
    snowflake_database: str = Field(default="TEST_DB", validation_alias="SF_DATABASE")
    snowflake_schema: str = Field(default="PUBLIC", validation_alias="SF_SCHEMA")
    snowflake_warehouse: str = Field(default="S_WHH", validation_alias="SF_WAREHOUSE")
    snowflake_role: str = Field(default="ACCOUNTADMIN", validation_alias="SF_ROLE")

    # JWT Authentication (using standardized variable names)
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    # LLM APIs (using standardized variable names)
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    # Application Configuration (using standardized variable names)
    app_host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")
    debug: bool = Field(default=True, validation_alias="DEBUG")

    # Logging (using standardized variable names)
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="json", validation_alias="LOG_FORMAT")

    # CORS Configuration (using standardized variable names)
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000", validation_alias="ALLOWED_ORIGINS")

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
