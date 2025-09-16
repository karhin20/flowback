"""
Configuration settings for the Insight Ops Flow Backend
"""
import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # SMS Service Configuration
    SMS_API_URL: str = os.getenv("SMS_API_URL", "")
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_SENDER_ID: str = os.getenv("SMS_SENDER_ID", "")
    
    # FastAPI Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "true").lower() == "true"
    
    # Database Configuration
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".xlsx", ".xls"]
    
    # Pagination Configuration
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))
    
    # SMS Configuration
    SMS_TIMEOUT: int = int(os.getenv("SMS_TIMEOUT", "30"))
    SMS_RETRY_ATTEMPTS: int = int(os.getenv("SMS_RETRY_ATTEMPTS", "3"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    def validate(self) -> bool:
        """Validate that all required settings are configured"""
        required_settings = [
            ("SUPABASE_URL", self.SUPABASE_URL),
            ("SUPABASE_KEY", self.SUPABASE_KEY),
            ("SMS_API_URL", self.SMS_API_URL),
            ("SMS_API_KEY", self.SMS_API_KEY),
            ("SMS_SENDER_ID", self.SMS_SENDER_ID),
            ("SECRET_KEY", self.SECRET_KEY)
        ]
        
        missing_settings = []
        for setting_name, setting_value in required_settings:
            if not setting_value or setting_value == "your-secret-key-here":
                missing_settings.append(setting_name)
        
        if missing_settings:
            print(f"❌ Missing required settings: {', '.join(missing_settings)}")
            print("Please check your .env file and ensure all required variables are set.")
            return False
        
        return True

# Global settings instance
settings = Settings()
