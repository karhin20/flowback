from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
from utils.validators import (
    PhoneValidator, AccountNumberValidator, AmountValidator, 
    NameValidator, StatusValidator, ActionValidator
)

class CustomerStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    WARNED = "warned"

class ActionType(str, Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    WARN = "warn"

class SourceType(str, Enum):
    MANUAL = "manual"
    BATCH = "batch"

# Customer Models
class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    account_number: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., max_length=25)
    status: CustomerStatus = CustomerStatus.CONNECTED
    arrears: str = Field(..., min_length=1)
    
    @validator('name')
    def validate_name(cls, v):
        return NameValidator.validate(v)
    
    # Account number validation removed - accept any format
    
    @validator('phone')
    def validate_phone(cls, v):
        return PhoneValidator.validate(v)
    
    @validator('status')
    def validate_status(cls, v):
        return StatusValidator.validate(v.value if hasattr(v, 'value') else v)
    
    @validator('arrears')
    def validate_arrears(cls, v):
        return AmountValidator.validate(v)

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=25)
    status: Optional[CustomerStatus] = None
    arrears: Optional[str] = Field(None, min_length=1)
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            return NameValidator.validate(v)
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            return PhoneValidator.validate(v)
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            return StatusValidator.validate(v.value if hasattr(v, 'value') else v)
        return v
    
    @validator('arrears')
    def validate_arrears(cls, v):
        if v is not None:
            return AmountValidator.validate(v)
        return v

class Customer(CustomerBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Action Models
class CustomerActionBase(BaseModel):
    customer_id: str
    action: ActionType
    performed_by: str = Field(..., min_length=1)
    source: SourceType = SourceType.MANUAL
    batch_id: Optional[str] = None

class CustomerActionCreate(CustomerActionBase):
    pass

class CustomerAction(CustomerActionBase):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True

# Batch Upload Models
class BatchUploadItem(BaseModel):
    row: int
    name: str
    account_number: str
    phone: str
    arrears: str
    status: Literal["validated", "error", "pending"] = "pending"

class BatchUploadRequest(BaseModel):
    data: List[BatchUploadItem]
    batch_id: str

class BatchUploadResponse(BaseModel):
    batch_id: str
    total_rows: int
    validated_rows: int
    error_rows: int
    errors: List[dict]

class BatchProcessResponse(BaseModel):
    message: str
    actions_created: int
    customers_created: int
    customers_updated: int
    batch_id: str
    success: bool = True
    errors: List[dict] = []

class CustomerForValidation(BaseModel):
    name: str
    account_number: str
    phone: str
    arrears: str

class ValidationErrorItem(BaseModel):
    row: int
    error: str
    data: dict

class CustomerValidationResponse(BaseModel):
    validated: List[BatchUploadItem]
    errors: List[ValidationErrorItem]
    total: int
    valid_count: int
    error_count: int

# Message Template Models
class MessageTemplateUpdate(BaseModel):
    message: str

class MessageTemplate(BaseModel):
    action: str
    message: str

    class Config:
        from_attributes = True

# SMS Models
class BulkSMSRequest(BaseModel):
    recipients: List[str]
    message: str

class SMSRequest(BaseModel):
    customer_id: str
    message: str
    include_arrears: bool = True

class SMSResponse(BaseModel):
    message_id: str
    status: str
    sent_at: datetime

# KPI Models
class KPIData(BaseModel):
    title: str
    value: str
    change: float
    is_positive: bool

class DashboardData(BaseModel):
    total_customers: int
    connected_customers: int
    disconnected_customers: int
    warned_customers: int
    total_arrears: str
    recent_actions: List[CustomerAction]
    kpis: List[KPIData]

# Filter Models
class CustomerFilters(BaseModel):
    search: Optional[str] = None
    status: Optional[CustomerStatus] = None
    arrears_min: Optional[float] = None
    arrears_max: Optional[float] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    limit: int = 50

# Response Models
class PaginatedResponse(BaseModel):
    data: List[dict]
    total: int
    page: int
    limit: int
    pages: int

# Auth/User Models
class User(BaseModel):
    id: str
    email: Optional[str] = None
    role: Optional[str] = None
    aud: Optional[str] = None
    email_confirmed_at: Optional[datetime] = None
    phone: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    last_sign_in_at: Optional[datetime] = None
    app_metadata: Optional[dict] = None
    user_metadata: Optional[dict] = None

    class Config:
        from_attributes = True
        extra = 'ignore'