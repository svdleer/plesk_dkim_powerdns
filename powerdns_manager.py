#!/usr/bin/env python3
"""
PowerDNS API Management Script
Handles DNS record operations via PowerDNS REST API
"""

import os
import json
import requests
from typing import Dict, Optional, List
from urllib.parse import urljoin


class PowerDNSManager:
    """Manager for PowerDNS operations via REST API"""
    
    def __init__(self, server_url: str, api_key: str):
        """
        Initialize PowerDNS Manager
        
        Args:
            server_url: PowerDNS API server URL (e.g., http://powerdns.example.com:8081)
            api_key: PowerDNS API key
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make API request to PowerDNS"""
        url = urljoin(self.server_url, f"/api/v1/{endpoint}")
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"PowerDNS API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            raise
    
    def get_servers(self) -> List[Dict]:
        """Get list of PowerDNS servers"""
        try:
            response = self._make_request('GET', 'servers')
            return response.json()
        except Exception as e:
            print(f"Failed to get servers: {e}")
            return []
    
    def get_zones(self, server_id: str = 'localhost') -> List[Dict]:
        """Get list of zones for a server"""
        try:
            response = self._make_request('GET', f'servers/{server_id}/zones')
            return response.json()
        except Exception as e:
            print(f"Failed to get zones: {e}")
            return []
    
    def get_zone(self, zone_name: str, server_id: str = 'localhost') -> Optional[Dict]:
        """Get zone information"""
        try:
            response = self._make_request('GET', f'servers/{server_id}/zones/{zone_name}')
            return response.json()
        except Exception as e:
            print(f"Failed to get zone {zone_name}: {e}")
            return None
    
    def create_or_update_record(self, zone_name: str, record_name: str, record_type: str, 
                               content: str, ttl: int = 300, server_id: str = 'localhost') -> bool:
        """
        Create or update a DNS record
        
        Args:
            zone_name: Zone name (e.g., "example.com.")
            record_name: Record name (e.g., "default._domainkey.example.com.")
            record_type: Record type (e.g., "TXT")
            content: Record content
            ttl: Time to live
            server_id: PowerDNS server ID
            
        Returns:
            bool: Success status
        """
        # Ensure zone name ends with dot
        if not zone_name.endswith('.'):
            zone_name += '.'
        
        # Ensure record name ends with dot
        if not record_name.endswith('.'):
            record_name += '.'
        
        # Prepare the RRset (Resource Record Set)
        rrsets_data = {
            "rrsets": [
                {
                    "name": record_name,
                    "type": record_type,
                    "changetype": "REPLACE",
                    "records": [
                        {
                            "content": content,
                            "disabled": False
                        }
                    ],
                    "ttl": ttl
                }
            ]
        }
        
        try:
            response = self._make_request('PATCH', f'servers/{server_id}/zones/{zone_name}', rrsets_data)
            print(f"Successfully created/updated {record_type} record for {record_name}")
            return True
        except Exception as e:
            print(f"Failed to create/update record {record_name}: {e}")
            return False
    
    def delete_record(self, zone_name: str, record_name: str, record_type: str, 
                     server_id: str = 'localhost') -> bool:
        """Delete a DNS record"""
        # Ensure zone name ends with dot
        if not zone_name.endswith('.'):
            zone_name += '.'
        
        # Ensure record name ends with dot
        if not record_name.endswith('.'):
            record_name += '.'
        
        rrsets_data = {
            "rrsets": [
                {
                    "name": record_name,
                    "type": record_type,
                    "changetype": "DELETE"
                }
            ]
        }
        
        try:
            response = self._make_request('PATCH', f'servers/{server_id}/zones/{zone_name}', rrsets_data)
            print(f"Successfully deleted {record_type} record for {record_name}")
            return True
        except Exception as e:
            print(f"Failed to delete record {record_name}: {e}")
            return False
    
    def get_records(self, zone_name: str, server_id: str = 'localhost') -> List[Dict]:
        """Get all records for a zone"""
        try:
            zone_info = self.get_zone(zone_name, server_id)
            if zone_info and 'rrsets' in zone_info:
                return zone_info['rrsets']
            return []
        except Exception as e:
            print(f"Failed to get records for zone {zone_name}: {e}")
            return []
    
    def find_dkim_records(self, zone_name: str, server_id: str = 'localhost') -> List[Dict]:
        """Find DKIM records in a zone"""
        records = self.get_records(zone_name, server_id)
        dkim_records = []
        
        for record in records:
            if record.get('type') == 'TXT' and '._domainkey.' in record.get('name', ''):
                dkim_records.append(record)
        
        return dkim_records
    
    def create_dkim_record(self, dkim_record_info: Dict, server_id: str = 'localhost') -> bool:
        """
        Create DKIM record from Plesk DKIM information
        
        Args:
            dkim_record_info: Dict containing DKIM record information from Plesk
            server_id: PowerDNS server ID
        """
        domain = dkim_record_info['domain']
        zone_name = domain if domain.endswith('.') else f"{domain}."
        
        return self.create_or_update_record(
            zone_name=zone_name,
            record_name=dkim_record_info['name'],
            record_type=dkim_record_info['type'],
            content=dkim_record_info['content'],
            ttl=dkim_record_info.get('ttl', 300),
            server_id=server_id
        )


def main():
    """Example usage"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize PowerDNS manager
    powerdns_url = os.getenv('POWERDNS_SERVER_URL')
    powerdns_key = os.getenv('POWERDNS_API_KEY')
    
    if not powerdns_url or not powerdns_key:
        print("Please set POWERDNS_SERVER_URL and POWERDNS_API_KEY in your .env file")
        return
    
    powerdns = PowerDNSManager(powerdns_url, powerdns_key)
    
    # Example: Get servers
    print("Fetching PowerDNS servers...")
    servers = powerdns.get_servers()
    print(f"Found {len(servers)} servers")
    
    # Example: Get zones
    print("Fetching zones...")
    zones = powerdns.get_zones()
    print(f"Found {len(zones)} zones")
    
    # Example: Create a DKIM record (uncomment and modify as needed)
    # dkim_info = {
    #     'domain': 'example.com',
    #     'name': 'default._domainkey.example.com',
    #     'type': 'TXT',
    #     'content': '"v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY_HERE"',
    #     'ttl': 300
    # }
    # powerdns.create_dkim_record(dkim_info)


if __name__ == "__main__":
    main()
