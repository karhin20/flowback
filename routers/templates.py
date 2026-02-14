from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from supabase import Client
from database import get_db
from services.supabase_service import SupabaseService
from utils.security import get_current_user, resolve_display_name
from models import MessageTemplate, User, SystemAuditLogCreate

router = APIRouter()

class MessageTemplateUpdate(BaseModel):
    message: str

@router.get("/", response_model=List[MessageTemplate])
async def get_message_templates(db: Client = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve all message templates."""
    try:
        service = SupabaseService(db)
        templates = await service.get_all_message_templates()
        return templates
    except Exception as e:
        api_logger.error("Failed to get message templates", error=e)
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{action}", response_model=MessageTemplate)
async def update_message_template(action: str, template_update: MessageTemplateUpdate, db: Client = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update a specific message template."""
    service = SupabaseService(db)
    updated_template = await service.update_message_template(action, template_update.message)

    # The error "'NoneType' object is not a mapping" can occur if the framework
    # tries to process a None value as a dictionary when a template is not found.
    # Explicitly checking for None and raising a 404 is the correct way to handle this.
    if updated_template is None:
        api_logger.warning(f"Attempted to update non-existent template for action '{action}'")
        raise HTTPException(
            status_code=404,
            detail=f"Template for action '{action}' not found."
        )

    # Log template update
    try:
        await service.log_system_event(SystemAuditLogCreate(
            action_category="TEMPLATE",
            action_type="UPDATE",
            performed_by=resolve_display_name(current_user, db),
            details={"action": action, "message": template_update.message}
        ))
    except Exception:
        pass

    return updated_template