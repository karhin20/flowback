import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from utils.errors import ValidationError

class PhoneValidator:
    """Validates phone numbers"""
    
    # Ghana phone number patterns
    PATTERNS = [
        r'^0[2-9]\d{8}$',  # 0XX XXX XXXX
        r'^\+233[2-9]\d{8}$',  # +233 XX XXX XXXX
        r'^233[2-9]\d{8}$',  # 233 XX XXX XXXX
        r'^[2-9]\d{8}$',  # 9-digit number missing leading 0
    ]
    
    @classmethod
    def validate(cls, phone: str) -> str:
        """Validate and normalize phone number"""
        if not phone:
            raise ValidationError("Phone number is required", field="phone")
        
        # Convert to string (for int inputs) and remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
        # Check against patterns
        for pattern in cls.PATTERNS:
            if re.match(pattern, cleaned):
                # Normalize to 0XX XXX XXXX format
                if cleaned.startswith('+233'):
                    return '0' + cleaned[4:]
                elif cleaned.startswith('233'):
                    return '0' + cleaned[3:]
                elif len(cleaned) == 9 and cleaned[0] != '0':
                    return '0' + cleaned
                
                return cleaned
        
        raise ValidationError(
            "Invalid phone number format. Use format: 0XX XXX XXXX",
            field="phone"
        )

class AccountNumberValidator:
    """Validates account numbers"""
    
    PATTERN = r'^[A-Z]{2,4}-\d{4,8}$'
    
    @classmethod
    def validate(cls, account_number: str) -> str:
        """Validate account number format"""
        if not account_number:
            raise ValidationError("Account number is required", field="account_number")
        
        # Convert to uppercase and remove spaces
        cleaned = account_number.upper().replace(' ', '')
        
        if not re.match(cls.PATTERN, cleaned):
            raise ValidationError(
                "Invalid account number format. Use format: ABC-123456",
                field="account_number"
            )
        
        return cleaned

class AmountValidator:
    """Validates monetary amounts"""
    
    @classmethod
    def validate(cls, amount: str) -> str:
        """Validate and format amount"""
        if not amount:
            raise ValidationError("Amount is required", field="arrears")
        
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[^\d.,]', '', amount)
        
        # Replace comma with dot for decimal
        cleaned = cleaned.replace(',', '.')
        
        # Validate format
        if not re.match(r'^\d+(\.\d{1,2})?$', cleaned):
            raise ValidationError(
                "Invalid amount format. Use format: 123.45",
                field="arrears"
            )
        
        # Ensure 2 decimal places
        if '.' in cleaned:
            integer, decimal = cleaned.split('.')
            decimal = decimal.ljust(2, '0')[:2]
            cleaned = f"{integer}.{decimal}"
        else:
            cleaned = f"{cleaned}.00"
        
        return cleaned

class NameValidator:
    """Validates names"""
    
    @classmethod
    def validate(cls, name: str) -> str:
        """Validate and clean name"""
        if not name:
            raise ValidationError("Name is required", field="name")
        
        # Remove extra spaces and validate length
        cleaned = ' '.join(name.strip().split())
        
        if len(cleaned) < 2:
            raise ValidationError("Name must be at least 2 characters long", field="name")
        
        if len(cleaned) > 255:
            raise ValidationError("Name must be less than 255 characters", field="name")
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", cleaned):
            raise ValidationError(
                "Name can only contain letters, spaces, hyphens, and apostrophes",
                field="name"
            )
        
        return cleaned.title()

class StatusValidator:
    """Validates customer status"""
    
    VALID_STATUSES = ['connected', 'disconnected', 'warned']
    
    @classmethod
    def validate(cls, status: str) -> str:
        """Validate status"""
        if not status:
            raise ValidationError("Status is required", field="status")
        
        if status not in cls.VALID_STATUSES:
            raise ValidationError(
                f"Invalid status. Must be one of: {', '.join(cls.VALID_STATUSES)}",
                field="status"
            )
        
        return status

class ActionValidator:
    """Validates action types"""
    
    VALID_ACTIONS = ['connect', 'disconnect', 'warn', 'sms_sent']
    
    @classmethod
    def validate(cls, action: str) -> str:
        """Validate action type"""
        if not action:
            raise ValidationError("Action is required", field="action")
        
        if action not in cls.VALID_ACTIONS:
            raise ValidationError(
                f"Invalid action. Must be one of: {', '.join(cls.VALID_ACTIONS)}",
                field="action"
            )
        
        return action

def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """Sanitize string input"""
    if not isinstance(value, str):
        value = str(value)
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

def validate_pagination(page: int, limit: int) -> tuple[int, int]:
    """Validate pagination parameters"""
    if page < 1:
        raise ValidationError("Page must be greater than 0", field="page")
    
    if limit < 1 or limit > 100:
        raise ValidationError("Limit must be between 1 and 100", field="limit")
    
    return page, limit

def validate_uuid(uuid_string: str, field_name: str = "id") -> str:
    """Validate UUID format"""
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    if not re.match(uuid_pattern, uuid_string, re.IGNORECASE):
        raise ValidationError(f"Invalid {field_name} format", field=field_name)
    
    return uuid_string
