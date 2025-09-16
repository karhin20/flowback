from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from database import get_db
from services.supabase_service import SupabaseService
from models import CustomerAction, CustomerActionCreate, PaginatedResponse, User
from supabase import Client
from websocket_manager import websocket_manager
from utils.security import get_current_user

router = APIRouter()

@router.post("/", response_model=CustomerAction)
async def create_action(
    action: CustomerActionCreate,
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new customer action"""
    try:
        service = SupabaseService(db)
        new_action = await service.create_action(action)
        
        # Broadcast WebSocket update
        await websocket_manager.broadcast_action_created(new_action.dict())
        
        return new_action
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=PaginatedResponse)
async def get_actions(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get customer actions with optional customer filter and pagination"""
    try:
        service = SupabaseService(db)
        actions = await service.get_customer_actions(customer_id, page, limit)
        
        # Get total count for pagination
        query = db.table("customer_actions").select("id", count="exact")
        if customer_id:
            query = query.eq("customer_id", customer_id)
        total_result = query.execute()
        total = total_result.count or 0
        
        return PaginatedResponse(
            data=actions,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customer/{customer_id}", response_model=List[CustomerAction])
async def get_customer_actions(
    customer_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all actions for a specific customer"""
    try:
        service = SupabaseService(db)
        actions = await service.get_customer_actions(customer_id, page, limit)
        return actions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[CustomerAction])
async def create_batch_actions(
    actions: List[CustomerActionCreate],
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple actions in a batch"""
    try:
        service = SupabaseService(db)
        new_actions = await service.create_batch_actions(actions)
        
        # Broadcast WebSocket updates for each action
        for action in new_actions:
            await websocket_manager.broadcast_action_created(action.dict())
        
        return new_actions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
