#!/usr/bin/env python3
"""
Plesk XML API Client for DKIM operations
Provides more comprehensive DKIM functionality via XML API
"""

import os
import xml.etree.ElementTree as ET
import requests
import urllib3
from typing import Dict, Optional, List
import base64

# Disable SSL warnings for development (remove in production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PleskXMLAPIClient:
    """Plesk XML API client for DKIM operations"""
    
    def __init__(self, server_url: str, api_key: str, username: str = None, password: str = None):
        """
        Initialize Plesk XML API client
        
        Args:
            server_url: Plesk server URL (e.g., https://plesk.example.com:8443)
            api_key: Plesk API key (or None if using username/password)
            username: Plesk admin username (alternative to API key)
            password: Plesk admin password (alternative to API key)
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.username = username
        self.password = password
        
        self.session = requests.Session()
        
        # Set up authentication headers
        if api_key:
            # API key authentication for XML API - Plesk standard format
            self.session.headers.update({
                'Content-Type': 'text/xml; charset=UTF-8',
                'KEY': api_key,
                'HTTP_PRETTY_PRINT': 'TRUE'
            })
            print(f"DEBUG: Using API key: {api_key[:8]}...{api_key[-4:]} (KEY header)")
        elif username and password:
            # Username/password authentication for XML API
            self.session.headers.update({
                'Content-Type': 'text/xml; charset=UTF-8',
                'HTTP_AUTH_LOGIN': username,
                'HTTP_AUTH_PASSWD': password,
                'HTTP_PRETTY_PRINT': 'TRUE'
            })
            print(f"DEBUG: Using username/password: {username}/{'*' * len(password)}")
        else:
            raise ValueError("Either api_key or username/password must be provided")
        
        # Disable SSL verification for self-signed certificates (adjust as needed)
        self.session.verify = False
        
        # Plesk XML API endpoint (confirmed working)
        self.xml_endpoint = "/enterprise/control/agent.php"
        
    def _make_xml_request(self, xml_data: str) -> ET.Element:
        """Make XML API request to Plesk"""
        url = f"{self.server_url}{self.xml_endpoint}"
        
        try:
            response = self.session.post(url, data=xml_data, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            # Check for API errors in the response
            status_elem = root.find('.//status')
            if status_elem is not None and status_elem.text == 'error':
                error_elem = root.find('.//errtext')
                error_msg = error_elem.text if error_elem is not None else 'Unknown API error'
                raise Exception(f"API error: {error_msg}")
            
            return root
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed for {self.xml_endpoint}: {e}")
        except ET.ParseError as e:
            raise Exception(f"XML parsing error: {e}")
    
    def get_site_id(self, domain_name: str) -> Optional[int]:
        """Get site ID for a domain name - required for mail operations"""
        print(f"🔍 Getting site ID for {domain_name}...")
        
        xml_request = """<?xml version="1.0" encoding="UTF-8"?>
        <packet>
            <site>
                <get>
                    <filter/>
                    <dataset>
                        <gen_info/>
                    </dataset>
                </get>
            </site>
        </packet>"""
        
        try:
            root = self._make_xml_request(xml_request)
            
            for site_result in root.findall('.//site/get/result'):
                status = site_result.find('status').text if site_result.find('status') is not None else 'unknown'
                if status == 'ok':
                    site_info = site_result.find('data/gen_info')
                    if site_info is not None:
                        name = site_info.find('name')
                        site_id = site_result.find('id')
                        if name is not None and site_id is not None and name.text == domain_name:
                            print(f"   Found site ID {site_id.text} for {domain_name}")
                            return int(site_id.text)
            
            print(f"   Site ID not found for {domain_name}")
            return None
            
        except Exception as e:
            print(f"Failed to get site ID for {domain_name}: {e}")
            return None
    def get_domains(self) -> List[Dict]:
        """Get list of domains using XML API"""
        xml_request = """<?xml version="1.0" encoding="UTF-8"?>
        <packet>
            <site>
                <get>
                    <filter/>
                    <dataset>
                        <gen_info/>
                    </dataset>
                </get>
            </site>
        </packet>"""
        
        try:
            root = self._make_xml_request(xml_request)
            domains = []
            
            for site_result in root.findall('.//site/get/result'):
                status = site_result.find('status').text if site_result.find('status') is not None else 'unknown'
                if status == 'ok':
                    site_info = site_result.find('data/gen_info')
                    site_id = site_result.find('id')
                    if site_info is not None and site_id is not None:
                        name = site_info.find('name')
                        if name is not None:
                            domains.append({
                                'name': name.text,
                                'site_id': int(site_id.text),
                                'status': status,
                                'type': 'site'
                            })
            
            return domains
            
        except Exception as e:
            print(f"Failed to get domains via XML API: {e}")
            return []
    
    def get_mail_settings(self, domain_name: str) -> Optional[Dict]:
        """Get mail settings for a domain using site-id"""
        # First get the site ID
        site_id = self.get_site_id(domain_name)
        if not site_id:
            return None
        
        xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
        <packet>
            <mail>
                <get_prefs>
                    <filter>
                        <site-id>{site_id}</site-id>
                    </filter>
                </get_prefs>
            </mail>
        </packet>"""
        
        try:
            root = self._make_xml_request(xml_request)
            
            result = root.find('.//mail/get_prefs/result')
            if result is not None:
                status = result.find('status').text if result.find('status') is not None else 'error'
                if status == 'ok':
                    prefs = result.find('prefs')
                    if prefs is not None:
                        settings = {'site_id': site_id}
                        for pref in prefs:
                            settings[pref.tag] = pref.text
                        return settings
                else:
                    error_msg = result.find('errtext')
                    error_text = error_msg.text if error_msg is not None else 'Unknown error'
                    print(f"Failed to get mail settings: {error_text}")
            
            return None
            
        except Exception as e:
            print(f"Failed to get mail settings for {domain_name}: {e}")
            return None
    
    def enable_dkim(self, domain_name: str, selector: str = "default", key_size: int = 1024) -> bool:
        """
        Enable DKIM for a domain using XML API with site-id
        Note: DKIM is controlled via the spam-protect-sign preference (DomainKeys/DKIM)
        
        Args:
            domain_name: Domain name
            selector: DKIM selector (may not be configurable via this method)
            key_size: RSA key size (may not be configurable via this method)
        """
        # Get the site ID first
        site_id = self.get_site_id(domain_name)
        if not site_id:
            print(f"Cannot enable DKIM: site ID not found for {domain_name}")
            return False
        
        xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
        <packet>
            <mail>
                <set_prefs>
                    <filter>
                        <site-id>{site_id}</site-id>
                    </filter>
                    <prefs>
                        <spam-protect-sign>true</spam-protect-sign>
                    </prefs>
                </set_prefs>
            </mail>
        </packet>"""
        
        try:
            root = self._make_xml_request(xml_request)
            
            result = root.find('.//mail/set_prefs/result')
            if result is not None:
                status = result.find('status').text if result.find('status') is not None else 'error'
                if status == 'ok':
                    print(f"DKIM/DomainKeys enabled for {domain_name} (site-id: {site_id})")
                    return True
                else:
                    error_msg = result.find('errtext')
                    error_text = error_msg.text if error_msg is not None else 'Unknown error'
                    print(f"Failed to enable DKIM: {error_text}")
            
            return False
            
        except Exception as e:
            print(f"Failed to enable DKIM for {domain_name}: {e}")
            return False
    
    def disable_dkim(self, domain_name: str) -> bool:
        """Disable DKIM for a domain using site-id (via spam-protect-sign)"""
        # Get the site ID first
        site_id = self.get_site_id(domain_name)
        if not site_id:
            print(f"Cannot disable DKIM: site ID not found for {domain_name}")
            return False
        
        xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
        <packet>
            <mail>
                <set_prefs>
                    <filter>
                        <site-id>{site_id}</site-id>
                    </filter>
                    <prefs>
                        <spam-protect-sign>false</spam-protect-sign>
                    </prefs>
                </set_prefs>
            </mail>
        </packet>"""
        
        try:
            root = self._make_xml_request(xml_request)
            
            result = root.find('.//mail/set_prefs/result')
            if result is not None:
                status = result.find('status').text if result.find('status') is not None else 'error'
                if status == 'ok':
                    print(f"DKIM/DomainKeys disabled for {domain_name} (site-id: {site_id})")
                    return True
                else:
                    error_msg = result.find('errtext')
                    error_text = error_msg.text if error_msg is not None else 'Unknown error'
                    print(f"Failed to disable DKIM: {error_text}")
            
            return False
            
        except Exception as e:
            print(f"Failed to disable DKIM for {domain_name}: {e}")
            return False
    
    def get_dkim_public_key(self, domain_name: str) -> Optional[str]:
        """Get DKIM public key for a domain using site-id"""
        # Get the site ID first
        site_id = self.get_site_id(domain_name)
        if not site_id:
            print(f"Cannot get DKIM key: site ID not found for {domain_name}")
            return None
        
        xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
        <packet>
            <mail>
                <get_dkim_key>
                    <filter>
                        <site-id>{site_id}</site-id>
                    </filter>
                </get_dkim_key>
            </mail>
        </packet>"""
        
        try:
            root = self._make_xml_request(xml_request)
            
            result = root.find('.//mail/get_dkim_key/result')
            if result is not None:
                status = result.find('status').text if result.find('status') is not None else 'error'
                if status == 'ok':
                    key_element = result.find('key')
                    if key_element is not None:
                        return key_element.text
                else:
                    error_msg = result.find('errtext')
                    error_text = error_msg.text if error_msg is not None else 'Unknown error'
                    print(f"Failed to get DKIM key: {error_text}")
            
            return None
            
        except Exception as e:
            print(f"Failed to get DKIM key for {domain_name}: {e}")
            return None
    
    def get_dkim_record_info(self, domain_name: str) -> Optional[Dict]:
        """Get complete DKIM record information"""
        # First get mail settings to check if DKIM is enabled
        mail_settings = self.get_mail_settings(domain_name)
        if not mail_settings:
            return None
        
        # Check if DKIM/DomainKeys is enabled via spam-protect-sign
        dkim_enabled = mail_settings.get('spam-protect-sign', 'false').lower() == 'true'
        if not dkim_enabled:
            print(f"DKIM/DomainKeys is not enabled for {domain_name}")
            return None
        
        # Try to get DKIM public key
        public_key = self.get_dkim_public_key(domain_name)
        
        if not public_key:
            return None
        
        # Use default selector - may not be configurable via XML API
        selector = "default"
        
        # Clean the public key for DNS record
        key_lines = public_key.strip().split('\n')
        clean_key = ''.join([line.strip() for line in key_lines 
                           if not line.startswith('-----')])
        
        return {
            'domain': domain_name,
            'selector': selector,
            'public_key': clean_key,
            'enabled': True,
            'dns_record_name': f"{selector}._domainkey.{domain_name}",
            'dns_record_content': f'"v=DKIM1; k=rsa; p={clean_key}"'
        }


def main():
    """Example usage of XML API"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize XML API client with flexible authentication
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_key = os.getenv('PLESK_API_KEY')
    plesk_username = os.getenv('PLESK_USERNAME')
    plesk_password = os.getenv('PLESK_PASSWORD')
    
    if not plesk_url:
        print("Please set PLESK_SERVER_URL in your .env file")
        return
    
    # Determine authentication method
    if plesk_username and plesk_password:
        print("Using username/password authentication")
        xml_client = PleskXMLAPIClient(plesk_url, None, plesk_username, plesk_password)
    elif plesk_key:
        print("Using API key authentication")
        xml_client = PleskXMLAPIClient(plesk_url, plesk_key)
    else:
        print("Please set either PLESK_USERNAME/PLESK_PASSWORD or PLESK_API_KEY in your .env file")
        return
    
    # Example: Get domains
    print("Fetching domains via XML API...")
    domains = xml_client.get_domains()
    print(f"Found {len(domains)} domains")
    
    # Example usage (uncomment as needed):
    # domain_name = "example.com"
    # print(f"Getting mail settings for {domain_name}...")
    # settings = xml_client.get_mail_settings(domain_name)
    # print(f"Mail settings: {settings}")
    
    # print(f"Getting DKIM info for {domain_name}...")
    # dkim_info = xml_client.get_dkim_record_info(domain_name)
    # print(f"DKIM info: {dkim_info}")


if __name__ == "__main__":
    main()
