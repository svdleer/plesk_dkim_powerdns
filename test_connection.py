#!/usr/bin/env python3
"""
Simple connection test script for Plesk server
"""

import os
import sys
import socket
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv


def test_connection():
    """Test connection to Plesk server"""
    load_dotenv()
    
    plesk_url = os.getenv('PLESK_SERVER_URL', 'https://aron.avant.nl:8443')
    parsed = urlparse(plesk_url)
    
    print(f"🔍 Testing connection to Plesk server")
    print(f"URL: {plesk_url}")
    print(f"Host: {parsed.hostname}")
    print(f"Port: {parsed.port or 8443}")
    print("-" * 50)
    
    # Test 1: Basic TCP connection
    print("1. Testing TCP connection...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((parsed.hostname, parsed.port or 8443))
        sock.close()
        
        if result == 0:
            print("   ✅ TCP connection successful")
        else:
            print(f"   ❌ TCP connection failed (error {result})")
            print("   This usually means:")
            print("     - Server is not running")
            print("     - Firewall blocking connection")
            print("     - Wrong port number")
            return False
    except Exception as e:
        print(f"   ❌ TCP test failed: {e}")
        return False
    
    # Test 2: HTTPS GET request
    print("\n2. Testing HTTPS response...")
    try:
        response = requests.get(plesk_url, verify=False, timeout=10)
        print(f"   ✅ HTTPS response received (status: {response.status_code})")
        
        if 'plesk' in response.text.lower() or 'panel' in response.text.lower():
            print("   ✅ Response appears to be from Plesk")
        else:
            print("   ⚠️  Response doesn't look like Plesk")
            
    except requests.exceptions.ConnectTimeout:
        print("   ❌ Connection timeout")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection error")
        return False
    except Exception as e:
        print(f"   ❌ HTTPS test failed: {e}")
        return False
    
    print("\n✅ Basic connectivity successful!")
    print("\n💡 Next steps:")
    print("   1. Update your .env file with username/password:")
    print("      PLESK_USERNAME=admin")
    print("      PLESK_PASSWORD=your-admin-password")
    print("   2. Test the XML API:")
    print("      python plesk_cli.py list")
    
    return True


if __name__ == "__main__":
    if not test_connection():
        print("\n❌ Connection test failed")
        print("Please check:")
        print("  - Server URL and port")
        print("  - Firewall settings")
        print("  - Plesk service status")
        sys.exit(1)
    else:
        print("\n🎉 Connection test passed!")
        sys.exit(0)
