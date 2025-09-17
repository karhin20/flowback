#!/usr/bin/env python3
"""
Generate a secure signup code for GWL Operations.
This script generates a random signup code that can be used for user registration.
"""

import secrets
import string
import sys

def generate_signup_code(length: int = 12) -> str:
    """Generate a secure random signup code."""
    # Use uppercase letters and numbers for better readability
    characters = string.ascii_uppercase + string.digits
    # Remove confusing characters (0, O, I, 1)
    characters = characters.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    
    return ''.join(secrets.choice(characters) for _ in range(length))

def main():
    if len(sys.argv) > 1:
        try:
            length = int(sys.argv[1])
        except ValueError:
            print("Error: Length must be a number")
            sys.exit(1)
    else:
        length = 12
    
    code = generate_signup_code(length)
    
    print("=" * 50)
    print("GWL Operations - Signup Code Generator")
    print("=" * 50)
    print(f"Generated Signup Code: {code}")
    print(f"Length: {len(code)} characters")
    print("=" * 50)
    print()
    print("To use this code:")
    print("1. Set the SIGNUP_CODE environment variable:")
    print(f"   export SIGNUP_CODE='{code}'")
    print()
    print("2. Or add it to your .env file:")
    print(f"   SIGNUP_CODE={code}")
    print()
    print("3. Restart your backend server")
    print("=" * 50)

if __name__ == "__main__":
    main()
