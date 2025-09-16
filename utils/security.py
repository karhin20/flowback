from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase import Client
from database import get_db
from models import User  # Assuming User model is defined in models.py
from utils.logger import api_logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Client = Depends(get_db)) -> User:
    """
    Dependency to get current user from Supabase JWT.
    """
    try:
        user_response = db.auth.get_user(token)
        if user_response and user_response.user:
            # The user object from gotrue-py is already a Pydantic model.
            # We can cast it to our own User model if they differ, or use it directly.
            return User(**user_response.user.dict())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    except Exception as e:
        api_logger.error(f"Authentication error: {e}", token=token[:10] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )