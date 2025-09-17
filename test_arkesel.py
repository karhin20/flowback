#!/usr/bin/env python3
"""
Test script for Arkesel SMS integration
Based on official Arkesel documentation
"""
import asyncio
import httpx
import json
from services.sms_service import SMSService

async def test_arkesel_integration():
    """Test the Arkesel SMS service implementation"""
    
    # Initialize SMS service
    sms_service = SMSService()
    
    print("🔧 Arkesel SMS Service Test")
    print("=" * 50)
    
    # Check configuration
    print(f"API Key configured: {'✅' if sms_service.api_key else '❌'}")
    print(f"Sender ID configured: {'✅' if sms_service.sender_id else '❌'}")
    print(f"Service configured: {'✅' if sms_service.is_configured() else '❌'}")
    
    if not sms_service.is_configured():
        print("\n❌ SMS service not configured. Please set ARKESEL_API_KEY and ARKESEL_SENDER_ID environment variables.")
        return
    
    print(f"\n📱 Testing with Sender ID: {sms_service.sender_id}")
    print(f"🔑 API Key: {sms_service.api_key[:10]}...")
    
    # Test phone number formatting
    test_phones = [
        "0241234567",      # Ghana format
        "+233241234567",   # International format
        "233241234567",    # 233 format
        "241234567",       # 9-digit format
        "024 123 4567",    # With spaces
        "+233 24 123 4567" # International with spaces
    ]
    
    print(f"\n📞 Testing phone number formatting:")
    for phone in test_phones:
        # Test the formatting logic
        cleaned = ''.join(filter(str.isdigit, phone))
        if cleaned.startswith('0'):
            formatted = '233' + cleaned[1:]
        elif cleaned.startswith('233'):
            formatted = cleaned
        elif len(cleaned) == 9:
            formatted = '233' + cleaned
        else:
            formatted = cleaned
        
        print(f"  {phone:20} → {formatted}")
    
    # Test SMS sending (commented out to avoid sending real SMS)
    print(f"\n📤 SMS sending test (commented out to avoid real SMS):")
    print("  Uncomment the lines below to test real SMS sending")
    
    # Uncomment these lines to test real SMS sending:
    # test_recipients = ["233553995047", "233544919953"]  # Replace with test numbers
    # test_message = "Test message from GWL Customers system"
    # 
    # print(f"  Sending test SMS to {len(test_recipients)} recipients...")
    # result = await sms_service.send_sms(test_recipients, test_message)
    # print(f"  Result: {json.dumps(result, indent=2)}")
    
    print(f"\n✅ Arkesel integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_arkesel_integration())
