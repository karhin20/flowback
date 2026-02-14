from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from supabase import Client
from database import get_db
from models import SystemAuditLog, PaginatedResponse, User
from services.supabase_service import SupabaseService
from utils.security import get_current_user
from utils.logger import api_logger

router = APIRouter()

@router.get("/system", response_model=List[SystemAuditLog])
async def get_system_audit_logs(
    category: Optional[str] = Query(None, description="Filter by category (USER, CUSTOMER, TEMPLATE, SYSTEM)"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch system-wide audit logs.
    """
    service = SupabaseService(db)
    api_logger.info(f"Fetching system audit logs for user {current_user.email}", category=category)
    return await service.get_system_audit_logs(category=category, page=page, limit=limit)
