from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from database import get_db
from services.supabase_service import SupabaseService
from models import (
    Customer, CustomerCreate, CustomerUpdate, CustomerFilters, 
    PaginatedResponse, DashboardData, User, SystemAuditLogCreate
)
from supabase import Client
from websocket_manager import websocket_manager
from utils.logger import api_logger
from utils.errors import (
    CustomerNotFoundError, CustomerAlreadyExistsError, DatabaseError,
    create_http_exception, get_user_friendly_message
)
from utils.validators import validate_pagination
from utils.security import get_current_user, resolve_display_name
from contextvars import ContextVar
import uuid

# Context variables
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/", response_model=Customer)
async def create_customer(
    customer: CustomerCreate,
    request: Request,
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new customer"""
    # Set request context
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    
    try:
        api_logger.info("Creating customer", request_id=request_id, customer_data=customer.dict())
        
        service = SupabaseService(db)
        new_customer = await service.create_customer(customer)
        
        # Broadcast WebSocket update
        await websocket_manager.broadcast_customer_created(new_customer.dict())
        
        api_logger.info("Customer created successfully", request_id=request_id, customer_id=new_customer.id)
        
        # Log to system audit trail
        try:
            await service.log_system_event(SystemAuditLogCreate(
                action_category="CUSTOMER",
                action_type="CREATE",
                performed_by=resolve_display_name(current_user, db),
                details={"account_number": new_customer.account_number, "name": new_customer.name}
            ))
        except Exception as e:
            api_logger.warning("Failed to log customer creation to audit trail", error=e)
            
        return new_customer
        
    except (CustomerAlreadyExistsError, DatabaseError) as e:
        api_logger.error("Customer creation failed", error=e, request_id=request_id)
        raise create_http_exception(e)
    except Exception as e:
        api_logger.error("Unexpected error creating customer", error=e, request_id=request_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": get_user_friendly_message(e),
                "request_id": request_id
            }
        )

@router.get("/", response_model=PaginatedResponse)
async def get_customers(
    search: Optional[str] = Query(None, description="Search term for name, account number, or phone"),
    status: Optional[str] = Query(None, description="Filter by customer status"),
    arrears_min: Optional[float] = Query(None, description="Minimum arrears amount"),
    arrears_max: Optional[float] = Query(None, description="Maximum arrears amount"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Client = Depends(get_db)
):
    """Get customers with optional filters and pagination"""
    try:
        api_logger.info("Fetching customers", 
                       search=search, status=status, 
                       arrears_min=arrears_min, arrears_max=arrears_max,
                       page=page, limit=limit)
        
        service = SupabaseService(db)
        
        filters = {}
        if search:
            filters["search"] = search
        if status:
            filters["status"] = status
        if arrears_min is not None:
            filters["arrears_min"] = arrears_min
        if arrears_max is not None:
            filters["arrears_max"] = arrears_max
        
        customers = await service.get_customers(filters, page, limit)
        
        # Get total count for pagination
        try:
            total_result = db.table("customers").select("id", count="exact").execute()
            total = total_result.count if total_result.count is not None else 0
        except Exception as e:
            api_logger.warning("Failed to get total count", error=e)
            total = 0
        
        # Ensure customers is a list and convert to dict
        customers_data = []
        if customers:
            try:
                customers_data = [customer.dict() for customer in customers]
            except Exception as e:
                api_logger.error("Error converting customers to dict", error=e, customer_count=len(customers))
                # Try to convert each customer individually
                for i, customer in enumerate(customers):
                    try:
                        customers_data.append(customer.dict())
                    except Exception as customer_error:
                        api_logger.error(f"Error converting customer {i} to dict", error=customer_error, customer_id=getattr(customer, 'id', 'unknown'))
                        # Skip this customer
                        continue
        
        response = PaginatedResponse(
            data=customers_data,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit if total > 0 else 0
        )
        
        api_logger.info("Customers fetched successfully", 
                       count=len(customers), total=total, page=page)
        
        return response
        
    except DatabaseError as de:
        api_logger.error("Database error fetching customers", error=de)
        raise create_http_exception(de)
    except Exception as e:
        api_logger.error("Unexpected error fetching customers", error=e, error_type=type(e).__name__)
        # Add more detailed error information
        error_detail = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "error_args": getattr(e, 'args', None)
        }
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/{customer_id}", response_model=Customer)
async def get_customer(
    customer_id: str,
    db: Client = Depends(get_db)
):
    """Get a specific customer by ID"""
    try:
        service = SupabaseService(db)
        customer = await service.get_customer(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{customer_id}", response_model=Customer)
async def update_customer(
    customer_id: str,
    customer_update: CustomerUpdate,
    db: Client = Depends(get_db)
):
    """Update a customer"""
    try:
        # Log the incoming data for debugging
        api_logger.info(f"Updating customer {customer_id} with data: {customer_update.dict()}")
        
        service = SupabaseService(db)
        customer = await service.update_customer(customer_id, customer_update)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Broadcast WebSocket updates
        await websocket_manager.broadcast_customer_updated(customer.dict())
        
        # Broadcast dashboard update
        dashboard_data = await service.get_dashboard_data()
        await websocket_manager.broadcast_dashboard_updated(dashboard_data)
        
        return customer
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error updating customer {customer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a customer"""
    try:
        service = SupabaseService(db)
        success = await service.delete_customer(customer_id)
        if not success:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        # Broadcast WebSocket update
        await websocket_manager.broadcast_customer_deleted(customer_id)
        
        # Log to system audit trail
        try:
            await service.log_system_event(SystemAuditLogCreate(
                action_category="CUSTOMER",
                action_type="DELETE",
                performed_by=resolve_display_name(current_user, db),
                details={"customer_id": customer_id}
            ))
        except Exception as e:
            api_logger.warning("Failed to log customer deletion to audit trail", error=e)

        return {"message": "Customer deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/data", response_model=DashboardData)
async def get_dashboard_data(
    db: Client = Depends(get_db)
):
    """Get dashboard statistics and data"""
    try:
        service = SupabaseService(db)
        data = await service.get_dashboard_data()
        
        # Calculate KPIs
        kpis = [
            {
                "title": "Total Customers",
                "value": str(data["total_customers"]),
                "change": 0.0,
                "is_positive": True
            },
            {
                "title": "Connected",
                "value": str(data["connected_customers"]),
                "change": 0.0,
                "is_positive": True
            },
            {
                "title": "Disconnected",
                "value": str(data["disconnected_customers"]),
                "change": 0.0,
                "is_positive": False
            },
            {
                "title": "Warned",
                "value": str(data["warned_customers"]),
                "change": 0.0,
                "is_positive": False
            }
        ]
        
        return DashboardData(
            total_customers=data["total_customers"],
            connected_customers=data["connected_customers"],
            disconnected_customers=data["disconnected_customers"],
            warned_customers=data["warned_customers"],
            total_arrears=data["total_arrears"],
            recent_actions=data["recent_actions"],
            kpis=kpis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
