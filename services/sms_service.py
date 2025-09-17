"""
SMS Service using Arkesel API v2
Based on official Arkesel documentation: https://sms.arkesel.com
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
        
        # Headers as per Arkesel documentation
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def send_sms(self, recipients: List[str], message: str, callback_url: Optional[str] = None, scheduled_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Send SMS to multiple recipients using Arkesel API v2
        Based on official Arkesel documentation format
        """
        if not self.api_key or not self.sender_id:
            api_logger.error("Arkesel SMS credentials not configured")
            return {"success": False, "error": "SMS credentials not configured"}
        
        # Format recipients to ensure they're in the correct format (233XXXXXXXXX)
        formatted_recipients = []
        for recipient in recipients:
            # Remove any non-digit characters except +
            cleaned = ''.join(filter(str.isdigit, recipient))
            
            # Convert to 233 format if needed
            if cleaned.startswith('0'):
                # Convert 0XXXXXXXXX to 233XXXXXXXXX
                formatted_recipients.append('233' + cleaned[1:])
            elif cleaned.startswith('233'):
                # Already in correct format
                formatted_recipients.append(cleaned)
            elif len(cleaned) == 9:
                # Convert 9-digit number to 233XXXXXXXXX
                formatted_recipients.append('233' + cleaned)
            else:
                # Use as-is if it doesn't match expected patterns
                formatted_recipients.append(cleaned)
        
        # Arkesel typically handles up to 1000 recipients per request
        batch_size = 1000
        total_recipients = len(formatted_recipients)
        successful_batches = 0
        all_responses = []
        
        try:
            for i in range(0, total_recipients, batch_size):
                batch = formatted_recipients[i:i + batch_size]
                
                # Prepare payload as per Arkesel documentation
                payload = {
                    "sender": self.sender_id,
                    "message": message,
                    "recipients": batch
                }
                
                # Add optional fields if provided
                if callback_url:
                    payload["callback_url"] = callback_url
                if scheduled_date:
                    payload["scheduled_date"] = scheduled_date
                
                api_logger.info(f"Sending SMS batch {i//batch_size + 1} to {len(batch)} recipients")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.base_url,
                        json=payload,
                        headers=self.headers,
                        timeout=60.0
                    )
                    
                    response_data = response.json() if response.content else {}
                    
                    if response.status_code == 200:
                        api_logger.info(f"SMS batch {i//batch_size + 1} sent successfully to {len(batch)} recipients")
                        successful_batches += 1
                        all_responses.append({
                            "batch": i//batch_size + 1,
                            "recipients": len(batch),
                            "response": response_data
                        })
                    else:
                        api_logger.error(f"SMS batch {i//batch_size + 1} failed", 
                                       status_code=response.status_code, 
                                       response=response_data)
                        all_responses.append({
                            "batch": i//batch_size + 1,
                            "recipients": len(batch),
                            "error": response_data
                        })
                
                # Small delay between batches to avoid overwhelming the API
                if i + batch_size < total_recipients:
                    import asyncio
                    await asyncio.sleep(0.5)
            
            success = successful_batches > 0
            api_logger.info(f"SMS sending completed: {successful_batches}/{len(range(0, total_recipients, batch_size))} batches successful, {total_recipients} total recipients")
            
            return {
                "success": success,
                "total_recipients": total_recipients,
                "successful_batches": successful_batches,
                "total_batches": len(range(0, total_recipients, batch_size)),
                "responses": all_responses
            }
                    
        except Exception as e:
            api_logger.error(f"SMS sending error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_single_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Send SMS to a single recipient"""
        result = await self.send_sms([phone], message)
        return result
    
    async def send_scheduled_sms(self, recipients: List[str], message: str, scheduled_date: str) -> Dict[str, Any]:
        """
        Send scheduled SMS using Arkesel API
        scheduled_date format: "2021-03-17 07:00 AM"
        """
        return await self.send_sms(recipients, message, scheduled_date=scheduled_date)
    
    async def send_sms_with_webhook(self, recipients: List[str], message: str, callback_url: str) -> Dict[str, Any]:
        """
        Send SMS with delivery webhook using Arkesel API
        """
        return await self.send_sms(recipients, message, callback_url=callback_url)
    
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
