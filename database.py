from supabase import create_client, Client
import os
from typing import Optional
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Ensure .env is loaded before reading environment variables
load_dotenv()

class DatabaseConfig:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL and key must be provided")
        
        self.client: Client = create_client(self.url, self.key)
        self.service_client: Optional[Client] = None
        
        if self.service_key:
            self.service_client = create_client(self.url, self.service_key)

# Global database instance
db_config = DatabaseConfig()

async def init_db():
    """Initialize database tables if they don't exist"""
    try:
        # Check if tables exist by querying them
        # If they don't exist, we'll get an error which we can handle
        db_config.client.table("customers").select("*").limit(1).execute()
        logger.info("Database tables already exist")
    except Exception as e:
        logger.warning(f"Database tables may not exist: {e}")
        # In a real scenario, you might want to create tables here
        # For Supabase, tables are typically created through the dashboard

def get_db():
    """Dependency to get database client"""
    return db_config.client

def get_service_db():
    """Dependency to get service database client (with elevated permissions)"""
    if not db_config.service_client:
        raise HTTPException(
            status_code=500, 
            detail="Service database client not configured"
        )
    return db_config.service_client
