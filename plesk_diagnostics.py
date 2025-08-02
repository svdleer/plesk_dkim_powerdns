#!/usr/bin/env python3
"""
Plesk API Diagnostics Tool
Tests connectivity and discovers correct API endpoints
"""

import os
import sys
import requests
import socket
from urllib.parse import urlparse
from dotenv import load_dotenv


class PleskDiagnostics:
    """Diagnostic tools for Plesk API connectivity"""
    
    def __init__(self, server_url: str, api_key: str):
        """Initialize with server details"""
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.parsed_url = urlparse(self.server_url)
        
    def test_basic_connectivity(self) -> bool:
        """Test basic network connectivity to the server"""
        print(f"🔍 Testing basic connectivity to {self.parsed_url.hostname}:{self.parsed_url.port}")
        
        try:
            # Test socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((self.parsed_url.hostname, self.parsed_url.port or 8443))
            sock.close()
            
            if result == 0:
                print(f"✅ TCP connection successful to {self.parsed_url.hostname}:{self.parsed_url.port or 8443}")
                return True
            else:
                print(f"❌ TCP connection failed to {self.parsed_url.hostname}:{self.parsed_url.port or 8443}")
                print(f"   Error code: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Network connectivity test failed: {e}")
            return False
    
    def test_https_response(self) -> bool:
        """Test HTTPS response from the server"""
        print(f"🔍 Testing HTTPS response from {self.server_url}")
        
        try:
            # Test basic HTTPS connection to root
            session = requests.Session()
            session.verify = False  # Ignore SSL for testing
            
            response = session.get(f"{self.server_url}/", timeout=10)
            print(f"✅ HTTPS response received (Status: {response.status_code})")
            
            # Check if it looks like Plesk
            if 'plesk' in response.text.lower() or 'panel' in response.text.lower():
                print(f"✅ Response appears to be from Plesk")
            else:
                print(f"⚠️  Response doesn't appear to be from Plesk")
                
            return True
            
        except requests.exceptions.ConnectTimeout:
            print(f"❌ Connection timeout to {self.server_url}")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error: {e}")
            return False
        except Exception as e:
            print(f"❌ HTTPS test failed: {e}")
            return False
    
    def test_xml_api_endpoint(self) -> bool:
        """Test the XML API endpoint specifically"""
        print(f"🔍 Testing XML API endpoint")
        
        endpoints_to_try = [
            "/enterprise/control/agent.php",  # Standard endpoint
            "/api/v2/",                       # REST API v2
            "/api/",                          # Generic API
        ]
        
        session = requests.Session()
        session.verify = False
        session.headers.update({
            'HTTP_AUTH_LOGIN': self.api_key,
            'HTTP_AUTH_PASSWD': '',
            'Content-Type': 'text/xml; charset=UTF-8'
        })
        
        for endpoint in endpoints_to_try:
            url = f"{self.server_url}{endpoint}"
            print(f"   Trying: {endpoint}")
            
            try:
                # For XML API, try a simple request
                if endpoint.endswith('agent.php'):
                    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
                    <packet>
                        <server>
                            <get>
                                <stat/>
                            </get>
                        </server>
                    </packet>"""
                    response = session.post(url, data=xml_data, timeout=10)
                else:
                    response = session.get(url, timeout=10)
                
                print(f"      Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"   ✅ Endpoint responding: {endpoint}")
                    if 'xml' in response.headers.get('content-type', '').lower():
                        print(f"      Response appears to be XML")
                    return True
                elif response.status_code == 401:
                    print(f"   🔐 Authentication required (good sign): {endpoint}")
                elif response.status_code == 403:
                    print(f"   🔐 Access forbidden (API key issue?): {endpoint}")
                else:
                    print(f"   ⚠️  Unexpected status: {response.status_code}")
                    
            except requests.exceptions.ConnectTimeout:
                print(f"      ❌ Timeout")
            except requests.exceptions.ConnectionError:
                print(f"      ❌ Connection refused")
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        return False
    
    def test_rest_api_endpoint(self) -> bool:
        """Test the REST API endpoint"""
        print(f"🔍 Testing REST API endpoint")
        
        session = requests.Session()
        session.verify = False
        session.headers.update({
            'X-API-Key': self.api_key,
            'Accept': 'application/json'
        })
        
        endpoint = "/api/v2/server"
        url = f"{self.server_url}{endpoint}"
        
        try:
            response = session.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ REST API responding")
                return True
            elif response.status_code == 401:
                print(f"🔐 Authentication required (check API key)")
            elif response.status_code == 403:
                print(f"🔐 Access forbidden (API key permissions?)")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ REST API test failed: {e}")
        
        return False
    
    def check_common_issues(self) -> None:
        """Check for common configuration issues"""
        print(f"🔍 Checking for common issues")
        
        # Check URL format
        if not self.server_url.startswith(('http://', 'https://')):
            print(f"❌ Server URL should start with http:// or https://")
        
        # Check port
        if self.parsed_url.port:
            if self.parsed_url.port != 8443:
                print(f"⚠️  Non-standard port {self.parsed_url.port} (Plesk usually uses 8443)")
        else:
            print(f"⚠️  No port specified (Plesk usually uses :8443)")
        
        # Check hostname resolution
        try:
            socket.gethostbyname(self.parsed_url.hostname)
            print(f"✅ Hostname {self.parsed_url.hostname} resolves")
        except socket.gaierror:
            print(f"❌ Hostname {self.parsed_url.hostname} does not resolve")
        
        # Check API key format
        if not self.api_key:
            print(f"❌ API key is empty")
        elif len(self.api_key) < 10:
            print(f"⚠️  API key seems too short (got {len(self.api_key)} chars)")
        else:
            print(f"✅ API key appears to be valid length ({len(self.api_key)} chars)")
    
    def suggest_fixes(self) -> None:
        """Suggest potential fixes"""
        print(f"\n💡 Potential fixes:")
        print(f"   1. Verify the Plesk server URL and port (usually :8443)")
        print(f"   2. Check if the API key has the correct permissions")
        print(f"   3. Ensure the Plesk server allows API access from your IP")
        print(f"   4. Check firewall settings on the Plesk server")
        print(f"   5. Try accessing the Plesk panel directly: {self.server_url}")
        print(f"   6. Verify XML API is enabled in Plesk Tools & Settings")
        print(f"   7. Try different authentication methods:")
        print(f"      - Use login/password instead of API key")
        print(f"      - Generate a new API key")
        
        print(f"\n🔧 Quick tests you can try:")
        print(f"   curl -k {self.server_url}")
        print(f"   telnet {self.parsed_url.hostname} {self.parsed_url.port or 8443}")
        
    def run_full_diagnostics(self) -> None:
        """Run complete diagnostic suite"""
        print(f"🚀 Plesk API Diagnostics")
        print(f"=" * 60)
        print(f"Server: {self.server_url}")
        print(f"API Key: {'*' * (len(self.api_key) - 4) + self.api_key[-4:] if len(self.api_key) > 4 else '****'}")
        print(f"=" * 60)
        
        # Run tests
        connectivity_ok = self.test_basic_connectivity()
        https_ok = self.test_https_response() if connectivity_ok else False
        xml_api_ok = self.test_xml_api_endpoint() if connectivity_ok else False
        rest_api_ok = self.test_rest_api_endpoint() if connectivity_ok else False
        
        print(f"\n" + "=" * 60)
        print(f"📊 Summary:")
        print(f"   Basic connectivity: {'✅' if connectivity_ok else '❌'}")
        print(f"   HTTPS response: {'✅' if https_ok else '❌'}")
        print(f"   XML API: {'✅' if xml_api_ok else '❌'}")
        print(f"   REST API: {'✅' if rest_api_ok else '❌'}")
        
        # Check common issues
        print(f"\n")
        self.check_common_issues()
        
        # Suggest fixes if needed
        if not all([connectivity_ok, xml_api_ok]):
            self.suggest_fixes()


def main():
    """Run diagnostics"""
    load_dotenv()
    
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_key = os.getenv('PLESK_API_KEY')
    
    if not plesk_url or not plesk_key:
        print("❌ Missing environment variables:")
        print("   PLESK_SERVER_URL and PLESK_API_KEY required")
        print("   Please check your .env file")
        sys.exit(1)
    
    diagnostics = PleskDiagnostics(plesk_url, plesk_key)
    diagnostics.run_full_diagnostics()


if __name__ == "__main__":
    main()
