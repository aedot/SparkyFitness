"""
Configuration module for Whoop microservice
Centralized settings management
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings from environment variables"""
    
    # Whoop API Configuration
    WHOOP_CLIENT_ID: str = os.getenv("WHOOP_CLIENT_ID", "")
    WHOOP_CLIENT_SECRET: str = os.getenv("WHOOP_CLIENT_SECRET", "")
    WHOOP_REDIRECT_URI: str = os.getenv("WHOOP_REDIRECT_URI", "http://localhost:8000/auth/whoop/callback")
    WHOOP_API_BASE: str = os.getenv("WHOOP_API_BASE", "https://api.prod.whoop.com/api/v2")
    WHOOP_OAUTH_URL: str = "https://api.prod.whoop.com/oauth/oauth2"
    
    # Service Configuration
    SERVICE_PORT: int = int(os.getenv("WHOOP_SERVICE_PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./whoop_tokens.db")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    
    # Token Management
    TOKEN_REFRESH_THRESHOLD: int = 300  # Refresh token 5 mins before expiry
    TOKEN_TTL_SECONDS: int = 86400  # Default token lifetime (24 hours)
    
    # Rate Limiting
    WHOOP_RATE_LIMIT: int = 100  # Requests per minute
    REQUEST_TIMEOUT: int = 30  # Seconds
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        required = ["WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET"]
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")

settings = Settings()