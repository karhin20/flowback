from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from supabase import Client
from database import get_db
from services.supabase_service import SupabaseService
from models import User
from utils.logger import api_logger
from utils.security import get_current_user
from config.settings import settings

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = 'user'
    signup_code: str

class SignupCodeVerify(BaseModel):
    code: str

def verify_signup_code(code: str) -> bool:
    """
    Verify the signup code against the configured signup code.
    """
    if not settings.signup_code:
        api_logger.warning("SIGNUP_CODE not configured in settings")
        return False
    
    return code == settings.signup_code

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Client = Depends(get_db)):
    """
    Login user and return JWT access token.
    FastAPI's OAuth2PasswordRequestForm uses 'username' for the email field.
    """
    service = SupabaseService(db)
    try:
        api_logger.info(f"Login attempt for user: {form_data.username}")
        auth_response = await service.sign_in(email=form_data.username, password=form_data.password)
        # auth_response is AuthResponse from supabase-py: contains .session and .user
        if auth_response and getattr(auth_response, 'session', None) and getattr(auth_response.session, 'access_token', None) and getattr(auth_response, 'user', None):
            api_logger.info(f"Login successful for user: {form_data.username}")
            # user is a pydantic-like model; use dict() if available
            user_payload = auth_response.user.dict() if hasattr(auth_response.user, 'dict') else auth_response.user
            return {"access_token": auth_response.session.access_token, "token_type": "bearer", "user": user_payload}
        
        api_logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    except Exception as e:
        api_logger.error(f"Login process failed for {form_data.username}", error=str(e))
        # Don't expose internal error details to the client
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Register a new user. Requires authentication.
    """
    service = SupabaseService(db)
    api_logger.info(f"User registration attempt for: {user_data.email} by {current_user.email}")

    user_metadata = {"name": user_data.name, "role": user_data.role}
    new_user = await service.sign_up(email=user_data.email, password=user_data.password, data=user_metadata)

    if not new_user:
        api_logger.error(f"User registration failed for: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create user. The email might already be in use."
        )
    
    api_logger.info(f"User {user_data.email} created successfully.")
    return new_user

class PublicUserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = 'user'
    signup_code: str

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
async def public_signup(user_data: PublicUserCreate, db: Client = Depends(get_db)):
    """
    Public signup endpoint for creating a new account.
    Requires a valid signup code for authentication.
    """
    service = SupabaseService(db)
    api_logger.info(f"Public user signup attempt for: {user_data.email}")

    # Verify signup code first
    if not verify_signup_code(user_data.signup_code):
        api_logger.warning(f"Invalid signup code provided for: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signup code. Please contact administrator for a valid code."
        )

    user_metadata = {"name": user_data.name, "role": user_data.role}
    new_user = await service.sign_up(email=user_data.email, password=user_data.password, data=user_metadata)

    if not new_user:
        api_logger.error(f"Public user signup failed for: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create user. The email might already be in use."
        )

    api_logger.info(f"Public user {user_data.email} created successfully with valid signup code.")
    return new_user

@router.post("/verify-signup-code")
async def verify_signup_code_endpoint(code_data: SignupCodeVerify):
    """
    Verify a signup code without creating a user.
    """
    is_valid = verify_signup_code(code_data.code)
    
    if is_valid:
        return {"valid": True, "message": "Signup code is valid"}
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signup code. Please contact administrator for a valid code."
        )

@router.get("/me")
async def get_me(db: Client = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Return current auth user and linked app profile (public.users).
    """
    try:
        profile_resp = db.table("users").select("display_name, role, avatar_url").eq("id", current_user.id).limit(1).execute()
        profile = (profile_resp.data[0] if (getattr(profile_resp, 'data', None) and len(profile_resp.data) > 0) else None)
        return {
            "user": current_user.dict() if hasattr(current_user, 'dict') else current_user,
            "profile": profile
        }
    except Exception as e:
        api_logger.error("Failed to fetch profile in /me", error=str(e))
        return {
            "user": current_user.dict() if hasattr(current_user, 'dict') else current_user,
            "profile": None
        }