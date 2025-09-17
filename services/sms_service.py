"""
SMS Service using Arkesel
"""
import httpx
from typing import List, Optional, Dict, Any
from utils.logger import api_logger
from config.settings import settings

class SMSService:
    def __init__(self):
        self.api_key = settings.arkesel_api_key or ""
        self.sender_id = settings.arkesel_sender_id or ""
        self.base_url = "https://sms.arkesel.com/api/v2/sms/send"
        self.status_url = "https://sms.arkesel.com/api/v2/sms"
    
    async def send_sms(self, recipients: List[str], message: str) -> bool:
        """Send SMS to multiple recipients using Arkesel with batching for large volumes"""
        if not self.api_key or not self.sender_id:
            api_logger.error("Arkesel SMS credentials not configured")
            return False
        
        # Arkesel typically handles up to 1000 recipients per request
        # For larger volumes, we'll batch them
        batch_size = 1000
        total_recipients = len(recipients)
        successful_batches = 0
        
        try:
            for i in range(0, total_recipients, batch_size):
                batch = recipients[i:i + batch_size]
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.base_url,
                        json={
                            "sender": self.sender_id,
                            "message": message,
                            "recipients": batch
                        },
                        headers={
                            "api-key": self.api_key,
                            "Content-Type": "application/json"
                        },
                        timeout=60.0  # Longer timeout for large batches
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        api_logger.info(f"SMS batch {i//batch_size + 1} sent successfully to {len(batch)} recipients")
                        successful_batches += 1
                    else:
                        api_logger.error(f"SMS batch {i//batch_size + 1} failed", 
                                       status_code=response.status_code, 
                                       response=response.text)
                        return False
                
                # Small delay between batches to avoid overwhelming the API
                if i + batch_size < total_recipients:
                    import asyncio
                    await asyncio.sleep(0.5)
            
            api_logger.info(f"All SMS batches sent successfully: {successful_batches} batches, {total_recipients} total recipients")
            return True
                    
        except Exception as e:
            api_logger.error(f"SMS sending error: {str(e)}")
            return False
    
    async def send_single_sms(self, phone: str, message: str) -> bool:
        """Send SMS to a single recipient"""
        return await self.send_sms([phone], message)
    
    async def get_sms_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get SMS delivery status from Arkesel"""
        if not self.api_key:
            api_logger.error("Arkesel API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.status_url}/{message_id}",
                    headers={"api-key": self.api_key},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    api_logger.error(f"SMS status check failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            api_logger.error(f"SMS status check error: {str(e)}")
            return None
    
    def is_configured(self) -> bool:
        """Check if SMS service is properly configured"""
        return bool(self.api_key and self.sender_id)
