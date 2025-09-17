import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import BulkSMSRequest, SMSRequest, User
from utils.logger import api_logger
from supabase import Client
from database import get_db
from services.supabase_service import SupabaseService
from services.sms_service import SMSService
from utils.security import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

# Initialize SMS service
sms_service = SMSService()

async def _send_sms_with_tracking(recipients: List[str], message: str, action_type: str, performed_by: str, db: Client, customer_id: str = None):
    """Send SMS and track the action in the database."""
    try:
        # Send SMS using centralized service
        success = await sms_service.send_sms(recipients, message)
        
        if not success:
            raise HTTPException(status_code=502, detail="Failed to send SMS")
        
        # Log the action in database if customer_id provided
        if customer_id:
            service = SupabaseService(db)
            await service.create_action({
                "customer_id": customer_id,
                "action": action_type,
                "performed_by": performed_by,
                "source": "manual"
            })
        
        api_logger.info(f"SMS sent successfully via {action_type} to {len(recipients)} recipients", 
                       performed_by=performed_by, customer_id=customer_id)
        
        return {"status": "success", "message": f"SMS sent successfully to {len(recipients)} recipient(s)"}
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Unexpected error sending SMS: {str(e)}", action_type=action_type)
        raise HTTPException(status_code=500, detail="Internal error occurred while sending SMS")

@router.post("/send-bulk", status_code=200)
async def send_bulk_sms(
    request: BulkSMSRequest, 
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send bulk SMS to multiple recipients."""
    if not sms_service.api_key or not sms_service.sender_id:
        api_logger.error("SMS service not configured")
        raise HTTPException(status_code=500, detail="SMS service is not configured")

    if not request.recipients:
        raise HTTPException(status_code=400, detail="No recipients provided")

    if len(request.recipients) > 1000:  # Rate limiting - allow up to 1000 per request
        raise HTTPException(status_code=400, detail="Maximum 1000 recipients allowed per bulk SMS")

    try:
        success = await sms_service.send_sms(request.recipients, request.message)
        
        if not success:
            raise HTTPException(status_code=502, detail="Failed to send bulk SMS")
        
        api_logger.info(f"Bulk SMS sent to {len(request.recipients)} recipients", 
                       performed_by=current_user.email)
        
        return {"status": "success", "message": f"SMS sent to {len(request.recipients)} recipients"}
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Bulk SMS error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error occurred while sending bulk SMS")

@router.post("/send", status_code=200)
async def send_custom_sms(
    request: SMSRequest, 
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send custom SMS to a specific customer."""
    service = SupabaseService(db)
    customer = await service.get_customer(request.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    message = request.message
    if request.include_arrears and customer.arrears:
        message += f"\nYour current arrears are: GHS {customer.arrears}"

    return await _send_sms_with_tracking(
        recipients=[customer.phone], 
        message=message, 
        action_type="sms_sent",
        performed_by=current_user.email,
        db=db,
        customer_id=customer.id
    )

@router.post("/send/warning/{customer_id}", status_code=200)
async def send_warning_sms(
    customer_id: str, 
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send warning SMS to customer using template."""
    service = SupabaseService(db)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    templates = await service.get_all_message_templates()
    template_msg = next((t['message'] for t in templates if t['action'] == 'warn'), None)
    if not template_msg:
        raise HTTPException(status_code=500, detail="Warning SMS template not found in database.")

    message = template_msg.replace('{amount}', f"GHS {customer.arrears}")
    
    return await _send_sms_with_tracking(
        recipients=[customer.phone], 
        message=message, 
        action_type="warn",
        performed_by=current_user.email,
        db=db,
        customer_id=customer.id
    )

@router.post("/send/disconnection/{customer_id}", status_code=200)
async def send_disconnection_sms(
    customer_id: str, 
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send disconnection SMS to customer using template."""
    service = SupabaseService(db)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    templates = await service.get_all_message_templates()
    template_msg = next((t['message'] for t in templates if t['action'] == 'disconnect'), None)
    if not template_msg:
        raise HTTPException(status_code=500, detail="Disconnection SMS template not found in database.")

    message = template_msg.replace('{amount}', f"GHS {customer.arrears}")
    
    return await _send_sms_with_tracking(
        recipients=[customer.phone], 
        message=message, 
        action_type="disconnect",
        performed_by=current_user.email,
        db=db,
        customer_id=customer.id
    )

@router.post("/send/connection/{customer_id}", status_code=200)
async def send_connection_sms(
    customer_id: str, 
    db: Client = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send connection SMS to customer using template."""
    service = SupabaseService(db)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    templates = await service.get_all_message_templates()
    template_msg = next((t['message'] for t in templates if t['action'] == 'connect'), None)
    if not template_msg:
        raise HTTPException(status_code=500, detail="Connection SMS template not found in database.")

    # The connection message might not have placeholders.
    message = template_msg.replace('{amount}', f"GHS {customer.arrears}")
    
    return await _send_sms_with_tracking(
        recipients=[customer.phone], 
        message=message, 
        action_type="connect",
        performed_by=current_user.email,
        db=db,
        customer_id=customer.id
    )

@router.get("/status/{message_id}", status_code=200)
async def get_sms_status(
    message_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get SMS delivery status from Arkesel."""
    if not sms_service.api_key:
        api_logger.error("SMS service not configured")
        raise HTTPException(status_code=500, detail="SMS service is not configured")

    url = f"https://sms.arkesel.com/api/v2/sms/{message_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, 
                headers={"api-key": sms_service.api_key}, 
                timeout=10.0
            )
            response.raise_for_status()
            response_data = response.json()
            api_logger.info(f"SMS status checked for message_id {message_id}", 
                           performed_by=current_user.email)
            return response_data
        except httpx.RequestError as e:
            api_logger.error(f"HTTP error checking SMS status: {e}")
            raise HTTPException(status_code=502, detail="Failed to communicate with SMS provider")
        except Exception as e:
            api_logger.error(f"SMS status check error: {e}")
            raise HTTPException(status_code=500, detail="Internal error occurred while checking SMS status")