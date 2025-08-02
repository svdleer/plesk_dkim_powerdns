#!/usr/bin/env python3
"""
Plesk DKIM Management Script
Handles DKIM operations via Plesk REST API
"""

import os
import json
import requests
from typing import Dict, Optional, List
from urllib.parse import urljoin
import xml.etree.ElementTree as ET


class PleskDKIMManager:
    """Manager for Plesk DKIM operations via REST API"""
    
    def __init__(self, server_url: str, api_key: str):
        """
        Initialize Plesk DKIM Manager
        
        Args:
            server_url: Plesk server URL (e.g., https://plesk.example.com:8443)
            api_key: Plesk API key
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        # Disable SSL verification for self-signed certificates (adjust as needed)
        self.session.verify = False
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make API request to Plesk"""
        url = urljoin(self.server_url, f"/api/v2/{endpoint}")
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            raise
    
    def get_domains(self) -> List[Dict]:
        """Get list of domains"""
        try:
            response = self._make_request('GET', 'domains')
            return response.json()
        except Exception as e:
            print(f"Failed to get domains: {e}")
            return []
    
    def get_domain_info(self, domain_name: str) -> Optional[Dict]:
        """Get domain information"""
        try:
            response = self._make_request('GET', f'domains/{domain_name}')
            return response.json()
        except Exception as e:
            print(f"Failed to get domain info for {domain_name}: {e}")
            return None
    
    def enable_dkim(self, domain_name: str, selector: str = "default") -> bool:
        """
        Enable DKIM for a domain
        
        Args:
            domain_name: Domain name
            selector: DKIM selector (default: "default")
            
        Returns:
            bool: Success status
        """
        data = {
            "enabled": True,
            "selector": selector
        }
        
        try:
            response = self._make_request('PUT', f'domains/{domain_name}/mail/dkim', data)
            print(f"DKIM enabled for {domain_name} with selector '{selector}'")
            return True
        except Exception as e:
            print(f"Failed to enable DKIM for {domain_name}: {e}")
            return False
    
    def disable_dkim(self, domain_name: str) -> bool:
        """Disable DKIM for a domain"""
        data = {"enabled": False}
        
        try:
            response = self._make_request('PUT', f'domains/{domain_name}/mail/dkim', data)
            print(f"DKIM disabled for {domain_name}")
            return True
        except Exception as e:
            print(f"Failed to disable DKIM for {domain_name}: {e}")
            return False
    
    def get_dkim_record(self, domain_name: str) -> Optional[Dict]:
        """
        Get DKIM DNS record for a domain
        
        Returns:
            Dict with DKIM record information including public key
        """
        try:
            response = self._make_request('GET', f'domains/{domain_name}/mail/dkim')
            dkim_info = response.json()
            
            if dkim_info.get('enabled'):
                return {
                    'domain': domain_name,
                    'selector': dkim_info.get('selector', 'default'),
                    'public_key': dkim_info.get('public_key', ''),
                    'dns_record': dkim_info.get('dns_record', ''),
                    'enabled': dkim_info.get('enabled', False)
                }
            else:
                print(f"DKIM is not enabled for {domain_name}")
                return None
                
        except Exception as e:
            print(f"Failed to get DKIM record for {domain_name}: {e}")
            return None
    
    def get_dkim_dns_record_formatted(self, domain_name: str) -> Optional[Dict]:
        """
        Get DKIM DNS record in a format suitable for PowerDNS
        
        Returns:
            Dict with formatted DNS record information
        """
        dkim_info = self.get_dkim_record(domain_name)
        if not dkim_info:
            return None
        
        selector = dkim_info['selector']
        public_key = dkim_info['public_key']
        
        # Format the TXT record value according to DKIM standards
        txt_record_value = f'"v=DKIM1; k=rsa; p={public_key}"'
        
        return {
            'name': f"{selector}._domainkey.{domain_name}",
            'type': 'TXT',
            'content': txt_record_value,
            'ttl': 300,
            'domain': domain_name,
            'selector': selector
        }


def main():
    """Example usage"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize Plesk manager
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_key = os.getenv('PLESK_API_KEY')
    
    if not plesk_url or not plesk_key:
        print("Please set PLESK_SERVER_URL and PLESK_API_KEY in your .env file")
        return
    
    plesk = PleskDKIMManager(plesk_url, plesk_key)
    
    # Example: Get domains
    print("Fetching domains...")
    domains = plesk.get_domains()
    print(f"Found {len(domains)} domains")
    
    # Example: Enable DKIM for a domain (uncomment and modify as needed)
    # domain_name = "example.com"
    # print(f"Enabling DKIM for {domain_name}...")
    # plesk.enable_dkim(domain_name)
    
    # Example: Get DKIM record
    # dkim_record = plesk.get_dkim_dns_record_formatted(domain_name)
    # if dkim_record:
    #     print(f"DKIM DNS record: {dkim_record}")


if __name__ == "__main__":
    main()
