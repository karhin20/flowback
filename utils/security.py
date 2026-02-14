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


def resolve_display_name(current_user: User, db: Client) -> str:
    """
    Resolve the user's display name from the profiles (users) table.
    Bypasses RLS by using service_client if available.
    Falls back to user_metadata.name, then email.
    """
    from database import db_config
    
    # Use service client to bypass RLS for profile lookup
    lookup_db = db_config.service_client or db
    
    try:
        # Get user ID regardless of if it's a Pydantic model or dict
        user_id = getattr(current_user, 'id', None) or (current_user.get('id') if isinstance(current_user, dict) else None)
        
        if user_id:
            # Check profiles table
            profile_resp = lookup_db.table("users").select("display_name").eq("id", user_id).limit(1).execute()
            if profile_resp.data and len(profile_resp.data) > 0:
                display_name = profile_resp.data[0].get("display_name")
                if display_name:
                    return display_name
    except Exception as e:
        api_logger.error(f"Failed to resolve display_name from profiles: {e}")

    # Fallback to user_metadata
    user_meta = {}
    if hasattr(current_user, 'user_metadata') and current_user.user_metadata:
        user_meta = current_user.user_metadata
    elif isinstance(current_user, dict):
        user_meta = current_user.get('user_metadata', {}) or {}
    
    # Try various metadata keys, including raw_user_meta which Supabase sometimes uses
    name = (
        user_meta.get('name') or
        user_meta.get('full_name') or
        user_meta.get('display_name') or
        user_meta.get('user_name') or
        (getattr(current_user, 'email', None) if not isinstance(current_user, dict) else current_user.get('email'))
    )
    
    if name:
        return name
        
    return "System"