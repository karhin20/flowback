import os
import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import BulkSMSRequest, SMSRequest
from utils.logger import api_logger
from supabase import Client
from database import get_db
from services.supabase_service import SupabaseService

router = APIRouter()

ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = os.getenv("ARKESEL_SENDER_ID")
ARKESEL_API_URL = "https://sms.arkesel.com/api/v2/sms/send"
ARKESEL_STATUS_API_URL = "https://sms.arkesel.com/api/v2/sms/{message_id}"

async def _send_sms(recipients: List[str], message: str):
    """Helper function to send SMS via Arkesel API."""
    if not ARKESEL_API_KEY or not ARKESEL_SENDER_ID:
        api_logger.error("Arkesel API Key or Sender ID is not configured on the server.")
        raise HTTPException(status_code=500, detail="SMS service is not configured.")

    payload = {
        "sender": ARKESEL_SENDER_ID,
        "recipients": recipients,
        "message": message,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                ARKESEL_API_URL,
                headers={"api-key": ARKESEL_API_KEY},
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            response_data = response.json()
            if response_data.get("status", "").lower() != "success":
                raise HTTPException(status_code=502, detail=f"SMS provider error: {response_data.get('message', 'Unknown error')}")
            return response_data
        except httpx.RequestError as e:
            api_logger.error(f"HTTP error occurred when calling Arkesel API: {e}")
            raise HTTPException(status_code=502, detail="Failed to communicate with SMS provider.")

@router.post("/send-bulk", status_code=200)
async def send_bulk_sms(request: BulkSMSRequest):
    if not ARKESEL_API_KEY or not ARKESEL_SENDER_ID:
        api_logger.error("Arkesel API Key or Sender ID is not configured on the server.")
        raise HTTPException(status_code=500, detail="SMS service is not configured.")

    await _send_sms(request.recipients, request.message)
    api_logger.info(f"Successfully initiated bulk SMS to {len(request.recipients)} recipients.")
    return {"status": "success", "message": "SMS sent successfully."}

@router.post("/send", status_code=200)
async def send_custom_sms(request: SMSRequest, db: Client = Depends(get_db)):
    service = SupabaseService(db)
    customer = await service.get_customer(request.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    message = request.message
    if request.include_arrears and customer.arrears:
        message += f"\nYour current arrears are: GHS {customer.arrears}"

    await _send_sms([customer.phone], message)
    api_logger.info(f"Sent custom SMS to customer {customer.id}")
    return {"status": "success", "message": f"SMS sent to {customer.name}."}

@router.post("/send/warning/{customer_id}", status_code=200)
async def send_warning_sms(customer_id: str, db: Client = Depends(get_db)):
    service = SupabaseService(db)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    templates = await service.get_all_message_templates()
    template_msg = next((t['message'] for t in templates if t['action'] == 'warn'), None)
    if not template_msg:
        raise HTTPException(status_code=500, detail="Warning SMS template not found in database.")

    message = template_msg.replace('{amount}', f"GHS {customer.arrears}")
    
    await _send_sms([customer.phone], message)
    api_logger.info(f"Sent warning SMS to customer {customer.id}")
    return {"status": "success", "message": f"Warning SMS sent to {customer.name}."}

@router.post("/send/disconnection/{customer_id}", status_code=200)
async def send_disconnection_sms(customer_id: str, db: Client = Depends(get_db)):
    service = SupabaseService(db)
    customer = await service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    templates = await service.get_all_message_templates()
    template_msg = next((t['message'] for t in templates if t['action'] == 'disconnect'), None)
    if not template_msg:
        raise HTTPException(status_code=500, detail="Disconnection SMS template not found in database.")

    message = template_msg.replace('{amount}', f"GHS {customer.arrears}")
    
    await _send_sms([customer.phone], message)
    api_logger.info(f"Sent disconnection SMS to customer {customer.id}")
    return {"status": "success", "message": f"Disconnection SMS sent to {customer.name}."}

@router.post("/send/connection/{customer_id}", status_code=200)
async def send_connection_sms(customer_id: str, db: Client = Depends(get_db)):
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
    
    await _send_sms([customer.phone], message)
    api_logger.info(f"Sent connection SMS to customer {customer.id}")
    return {"status": "success", "message": f"Connection SMS sent to {customer.name}."}

@router.get("/status/{message_id}", status_code=200)
async def get_sms_status(message_id: str):
    if not ARKESEL_API_KEY:
        api_logger.error("Arkesel API Key is not configured on the server.")
        raise HTTPException(status_code=500, detail="SMS service is not configured.")

    url = ARKESEL_STATUS_API_URL.format(message_id=message_id)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers={"api-key": ARKESEL_API_KEY}, timeout=10.0)
            response.raise_for_status()
            response_data = response.json()
            api_logger.info(f"Checked SMS status for message_id {message_id}.")
            return response_data
        except httpx.RequestError as e:
            api_logger.error(f"HTTP error occurred when checking Arkesel SMS status: {e}")
            raise HTTPException(status_code=502, detail="Failed to communicate with SMS provider.")
        except Exception as e:
            api_logger.error(f"An unexpected error occurred during SMS status check: {e}")
            raise HTTPException(status_code=500, detail="An internal error occurred while checking SMS status.")