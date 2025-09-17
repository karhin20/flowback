#!/usr/bin/env python3
"""
Test script to verify the backend setup
"""
import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test if environment variables are properly configured"""
    load_dotenv()
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SECRET_KEY",
        "ARKESEL_API_KEY",
        "ARKESEL_SENDER_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease check your .env file and ensure all required variables are set.")
        return False
    else:
        print("✅ All required environment variables are configured")
        return True

def test_imports():
    """Test if all required modules can be imported"""
    try:
        import fastapi
        print("✅ FastAPI imported successfully")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")
        return False
    
    try:
        import supabase
        print("✅ Supabase imported successfully")
    except ImportError as e:
        print(f"❌ Supabase import failed: {e}")
        return False
    
    try:
        import pandas
        print("✅ Pandas imported successfully")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import openpyxl
        print("✅ OpenPyXL imported successfully")
    except ImportError as e:
        print(f"❌ OpenPyXL import failed: {e}")
        return False
    
    return True

def test_app_import():
    """Test if the main app can be imported"""
    try:
        from index import app
        print("✅ Main app imported successfully")
        return True
    except Exception as e:
        print(f"❌ Main app import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Insight Ops Flow Backend Setup\n")
    
    tests = [
        ("Environment Variables", test_environment),
        ("Module Imports", test_imports),
        ("App Import", test_app_import)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"   Test failed: {test_name}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The backend is ready to run.")
        print("\nTo start the server, run:")
        print("   python start.py")
        print("\nOr:")
        print("   uvicorn index:app --reload")
    else:
        print("❌ Some tests failed. Please fix the issues before running the server.")
        sys.exit(1)

if __name__ == "__main__":
    main()
