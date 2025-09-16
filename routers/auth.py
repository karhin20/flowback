from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from supabase import Client
from database import get_db
from services.supabase_service import SupabaseService
from models import User
from utils.logger import api_logger
from utils.security import get_current_user

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = 'user'

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Client = Depends(get_db)):
    """
    Login user and return JWT access token.
    FastAPI's OAuth2PasswordRequestForm uses 'username' for the email field.
    """
    service = SupabaseService(db)
    try:
        api_logger.info(f"Login attempt for user: {form_data.username}")
        session = await service.sign_in(email=form_data.username, password=form_data.password)
        if session and session.access_token and session.user:
            api_logger.info(f"Login successful for user: {form_data.username}")
            return {"access_token": session.access_token, "token_type": "bearer", "user": session.user.dict()}
        
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

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
async def public_signup(user_data: PublicUserCreate, db: Client = Depends(get_db)):
    """
    Public signup endpoint for creating a new account.
    """
    service = SupabaseService(db)
    api_logger.info(f"Public user signup attempt for: {user_data.email}")

    user_metadata = {"name": user_data.name, "role": user_data.role}
    new_user = await service.sign_up(email=user_data.email, password=user_data.password, data=user_metadata)

    if not new_user:
        api_logger.error(f"Public user signup failed for: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create user. The email might already be in use."
        )

    api_logger.info(f"Public user {user_data.email} created successfully.")
    return new_user