#!/usr/bin/env python3
"""
Simple API test script for the Insight Ops Flow Backend
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("🔍 Testing root endpoint...")
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint: {data['message']}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_customers_endpoints():
    """Test customers endpoints"""
    print("🔍 Testing customers endpoints...")
    
    # Test get customers
    try:
        response = requests.get(f"{API_BASE}/customers/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Get customers: {data['total']} customers found")
        else:
            print(f"❌ Get customers failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get customers error: {e}")
        return False
    
    # Test create customer
    try:
        customer_data = {
            "name": "Test Customer",
            "account_number": "TEST001",
            "phone": "1234567890",
            "status": "connected",
            "arrears": "0.00"
        }
        response = requests.post(f"{API_BASE}/customers/", json=customer_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Create customer: {data['name']} created")
            return data['id']  # Return customer ID for further tests
        else:
            print(f"❌ Create customer failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Create customer error: {e}")
        return None

def test_actions_endpoints(customer_id):
    """Test actions endpoints"""
    if not customer_id:
        print("⏭️ Skipping actions test - no customer ID")
        return False
    
    print("🔍 Testing actions endpoints...")
    
    try:
        action_data = {
            "customer_id": customer_id,
            "action": "warn",
            "reason": "Test warning action",
            "performed_by": "test_user",
            "source": "manual"
        }
        response = requests.post(f"{API_BASE}/actions/", json=action_data)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Create action: {data['action']} action created")
            return True
        else:
            print(f"❌ Create action failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Create action error: {e}")
        return False

def test_dashboard_endpoint():
    """Test dashboard endpoint"""
    print("🔍 Testing dashboard endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/customers/dashboard/data")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Dashboard data: {data['total_customers']} total customers")
            return True
        else:
            print(f"❌ Dashboard failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return False

def test_upload_endpoints():
    """Test upload endpoints"""
    print("🔍 Testing upload endpoints...")
    
    # Test validate customers
    try:
        test_customers = [
            {
                "name": "Test Customer 1",
                "account_number": "TEST002",
                "phone": "1234567891",
                "arrears": "100.00"
            },
            {
                "name": "Test Customer 2",
                "account_number": "TEST003",
                "phone": "1234567892",
                "arrears": "200.00"
            }
        ]
        
        response = requests.post(f"{API_BASE}/upload/validate-customers", json=test_customers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Validate customers: {data['valid_count']} valid, {data['error_count']} errors")
            return True
        else:
            print(f"❌ Validate customers failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Validate customers error: {e}")
        return False

def main():
    """Run all API tests"""
    print("🧪 Testing Insight Ops Flow Backend API\n")
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("Customers Endpoints", test_customers_endpoints),
        ("Dashboard Endpoint", test_dashboard_endpoint),
        ("Upload Endpoints", test_upload_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    customer_id = None
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_name == "Customers Endpoints":
            result = test_func()
            if result:
                customer_id = result
                passed += 1
        elif test_name == "Actions Endpoints":
            if test_actions_endpoints(customer_id):
                passed += 1
        else:
            if test_func():
                passed += 1
        
        time.sleep(0.5)  # Small delay between tests
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API tests passed! The backend is working correctly.")
    else:
        print("❌ Some API tests failed. Please check the server logs and configuration.")
    
    print(f"\n🌐 API Documentation: {BASE_URL}/docs")
    print(f"🔧 ReDoc Documentation: {BASE_URL}/redoc")

if __name__ == "__main__":
    main()
