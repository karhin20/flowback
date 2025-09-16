from typing import Any, Dict, Optional
from fastapi import HTTPException
from enum import Enum

class ErrorCode(str, Enum):
    # Customer errors
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    CUSTOMER_ALREADY_EXISTS = "CUSTOMER_ALREADY_EXISTS"
    INVALID_CUSTOMER_DATA = "INVALID_CUSTOMER_DATA"
    
    # Action errors
    INVALID_ACTION = "INVALID_ACTION"
    ACTION_NOT_FOUND = "ACTION_NOT_FOUND"
    
    # Upload errors
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    BATCH_PROCESSING_ERROR = "BATCH_PROCESSING_ERROR"
    
    # SMS errors
    SMS_SEND_FAILED = "SMS_SEND_FAILED"
    INVALID_PHONE_NUMBER = "INVALID_PHONE_NUMBER"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    REQUIRED_FIELD_MISSING = "REQUIRED_FIELD_MISSING"
    
    # Authentication errors
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

class InsightOpsError(Exception):
    """Base exception class for Insight Ops Flow"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(InsightOpsError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={**details, "field": field} if field else details
        )

class CustomerNotFoundError(InsightOpsError):
    """Raised when customer is not found"""
    
    def __init__(self, customer_id: str):
        super().__init__(
            message=f"Customer with ID {customer_id} not found",
            error_code=ErrorCode.CUSTOMER_NOT_FOUND,
            status_code=404,
            details={"customer_id": customer_id}
        )

class CustomerAlreadyExistsError(InsightOpsError):
    """Raised when customer already exists"""
    
    def __init__(self, account_number: str):
        super().__init__(
            message=f"Customer with account number {account_number} already exists",
            error_code=ErrorCode.CUSTOMER_ALREADY_EXISTS,
            status_code=409,
            details={"account_number": account_number}
        )

class DatabaseError(InsightOpsError):
    """Raised when database operation fails"""
    
    def __init__(self, message: str, operation: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_QUERY_ERROR,
            status_code=500,
            details={**details, "operation": operation}
        )

def create_http_exception(error: InsightOpsError) -> HTTPException:
    """Convert InsightOpsError to HTTPException"""
    return HTTPException(
        status_code=error.status_code,
        detail={
            "error_code": error.error_code.value,
            "message": error.message,
            "details": error.details
        }
    )

def get_user_friendly_message(error: Exception) -> str:
    """Get user-friendly error message"""
    if isinstance(error, InsightOpsError):
        return error.message
    
    # Map common exceptions to user-friendly messages
    error_messages = {
        "ValidationError": "Please check your input and try again",
        "ConnectionError": "Unable to connect to the service. Please try again later",
        "TimeoutError": "Request timed out. Please try again",
        "PermissionError": "You don't have permission to perform this action",
    }
    
    error_type = type(error).__name__
    return error_messages.get(error_type, "An unexpected error occurred. Please try again")
