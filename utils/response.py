from typing import Any, Dict, Optional, Generic, TypeVar
from pydantic import BaseModel
from datetime import datetime
import uuid

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper"""
    success: bool
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    field: Optional[str] = None

class ResponseMeta(BaseModel):
    """Response metadata"""
    timestamp: str
    request_id: str
    version: str = "1.0.0"

def create_success_response(
    data: Any,
    request_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> ApiResponse:
    """Create a successful API response"""
    return ApiResponse(
        success=True,
        data=data,
        meta={
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id or str(uuid.uuid4()),
            "version": "1.0.0",
            **(meta or {})
        }
    )

def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    field: Optional[str] = None,
    request_id: Optional[str] = None
) -> ApiResponse:
    """Create an error API response"""
    return ApiResponse(
        success=False,
        error={
            "code": error_code,
            "message": message,
            "details": details,
            "field": field,
            "status_code": status_code
        },
        meta={
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id or str(uuid.uuid4()),
            "version": "1.0.0"
        }
    )

def create_paginated_response(
    data: list,
    total: int,
    page: int,
    limit: int,
    request_id: Optional[str] = None
) -> ApiResponse:
    """Create a paginated response"""
    total_pages = (total + limit - 1) // limit
    
    return ApiResponse(
        success=True,
        data=data,
        meta={
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id or str(uuid.uuid4()),
            "version": "1.0.0",
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    )
