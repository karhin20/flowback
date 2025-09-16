import httpx
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from models import SMSRequest, SMSResponse

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.api_url = os.getenv("SMS_API_URL")
        self.api_key = os.getenv("SMS_API_KEY")
        self.sender_id = os.getenv("SMS_SENDER_ID")
        
        if not all([self.api_url, self.api_key, self.sender_id]):
            logger.warning("SMS service not fully configured. Some features may not work.")

    async def send_sms(self, phone: str, message: str, include_arrears: bool = True, arrears: str = None) -> SMSResponse:
        """Send SMS to a phone number"""
        try:
            if not self.api_url or not self.api_key:
                raise Exception("SMS service not configured")
            
            # Format message with arrears if requested
            if include_arrears and arrears:
                message = f"{message}\n\nArrears: {arrears}"
            
            # Prepare SMS payload
            payload = {
                "to": phone,
                "message": message,
                "sender_id": self.sender_id
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/send",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return SMSResponse(
                        message_id=result.get("message_id", "unknown"),
                        status="sent",
                        sent_at=datetime.now()
                    )
                else:
                    logger.error(f"SMS API error: {response.status_code} - {response.text}")
                    raise Exception(f"SMS sending failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            raise

    async def send_warning_sms(self, customer_name: str, phone: str, arrears: str) -> SMSResponse:
        """Send warning SMS with arrears information"""
        message = (
            f"Dear Customer, you are reminded to settle your arrears of {arrears} to avoid disconnection."
        )
        return await self.send_sms(phone, message, include_arrears=True, arrears=arrears)

    async def send_disconnection_sms(self, customer_name: str, phone: str, arrears: str) -> SMSResponse:
        """Send disconnection SMS with arrears information"""
        message = (
            f"Dear Customer, due to arrears of {arrears}, your service has been disconnected."
        )
        return await self.send_sms(phone, message, include_arrears=True, arrears=arrears)

    async def send_connection_sms(self, customer_name: str, phone: str) -> SMSResponse:
        """Send connection confirmation SMS"""
        message = f"Dear {customer_name},\n\nYour service has been successfully connected. Thank you for your payment."
        return await self.send_sms(phone, message, include_arrears=False)

    async def get_sms_status(self, message_id: str) -> Dict[str, Any]:
        """Get SMS delivery status"""
        try:
            if not self.api_url or not self.api_key:
                raise Exception("SMS service not configured")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/status/{message_id}",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"SMS status API error: {response.status_code} - {response.text}")
                    raise Exception(f"Failed to get SMS status: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error getting SMS status: {e}")
            raise
