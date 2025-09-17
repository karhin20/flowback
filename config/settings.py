from pydantic import BaseSettings, Field, validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    app_name: str = "Insight Ops Flow"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    frontend_url: str = "http://localhost:3000"
    email_redirect_path: str = "/auth/callback"
    
    # Database Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    signup_code: str = Field("", env="SIGNUP_CODE")
    
    # SMS Configuration
    sms_api_url: Optional[str] = Field(None, env="SMS_API_URL")
    sms_api_key: Optional[str] = Field(None, env="SMS_API_KEY")
    sms_sender_id: Optional[str] = Field(None, env="SMS_SENDER_ID")
    
    # Cache Configuration
    cache_ttl_customers: int = 300  # 5 minutes
    cache_ttl_dashboard: int = 60   # 1 minute
    cache_ttl_actions: int = 180    # 3 minutes
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # File Upload
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = [".xlsx", ".xls"]
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('supabase_url')
    def validate_supabase_url(cls, v):
        if not v.startswith('https://'):
            raise ValueError('Supabase URL must start with https://')
        return v
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {", ".join(valid_levels)}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Environment-specific configurations
class DevelopmentSettings(Settings):
    debug: bool = True
    log_level: str = "DEBUG"

class ProductionSettings(Settings):
    debug: bool = False
    log_level: str = "INFO"
    
    @validator('cors_origins')
    def validate_production_cors(cls, v):
        # In production, ensure only secure origins
        for origin in v:
            if not origin.startswith('https://'):
                raise ValueError('Production CORS origins must use HTTPS')
        return v

class TestingSettings(Settings):
    debug: bool = True
    log_level: str = "DEBUG"
    supabase_url: str = "https://test.supabase.co"
    supabase_key: str = "test-key"
    supabase_service_key: str = "test-service-key"
    secret_key: str = "test-secret-key-32-characters-long"

def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return ProductionSettings()
    elif env == 'testing':
        return TestingSettings()
    else:
        return DevelopmentSettings()
