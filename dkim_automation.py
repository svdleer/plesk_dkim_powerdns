#!/usr/bin/env python3
"""
DKIM Automation Script
Automates DKIM enablement in Plesk and DNS record creation in PowerDNS
"""

import os
import sys
import argparse
from typing import List, Dict, Optional
from plesk_dkim import PleskDKIMManager
from powerdns_manager import PowerDNSManager


class DKIMAutomation:
    """Main automation class for DKIM operations"""
    
    def __init__(self, plesk_url: str, plesk_key: str, powerdns_url: str, powerdns_key: str):
        """Initialize with API credentials"""
        self.plesk = PleskDKIMManager(plesk_url, plesk_key)
        self.powerdns = PowerDNSManager(powerdns_url, powerdns_key)
    
    def enable_dkim_full_workflow(self, domain: str, selector: str = "default", 
                                 server_id: str = 'localhost') -> bool:
        """
        Complete DKIM enablement workflow:
        1. Enable DKIM in Plesk
        2. Get the DKIM DNS record
        3. Create the record in PowerDNS
        
        Args:
            domain: Domain name
            selector: DKIM selector
            server_id: PowerDNS server ID
            
        Returns:
            bool: Success status
        """
        print(f"Starting DKIM enablement for domain: {domain}")
        
        # Step 1: Enable DKIM in Plesk
        print("Step 1: Enabling DKIM in Plesk...")
        if not self.plesk.enable_dkim(domain, selector):
            print("Failed to enable DKIM in Plesk")
            return False
        
        # Step 2: Get DKIM record from Plesk
        print("Step 2: Retrieving DKIM record from Plesk...")
        dkim_record = self.plesk.get_dkim_dns_record_formatted(domain)
        if not dkim_record:
            print("Failed to retrieve DKIM record from Plesk")
            return False
        
        print(f"DKIM record details:")
        print(f"  Name: {dkim_record['name']}")
        print(f"  Type: {dkim_record['type']}")
        print(f"  Content: {dkim_record['content']}")
        print(f"  TTL: {dkim_record['ttl']}")
        
        # Step 3: Create DNS record in PowerDNS
        print("Step 3: Creating DKIM record in PowerDNS...")
        if not self.powerdns.create_dkim_record(dkim_record, server_id):
            print("Failed to create DKIM record in PowerDNS")
            return False
        
        print(f"✅ DKIM successfully enabled for {domain}")
        print(f"   Selector: {selector}")
        print(f"   DNS record created: {dkim_record['name']}")
        
        return True
    
    def disable_dkim_full_workflow(self, domain: str, server_id: str = 'localhost') -> bool:
        """
        Complete DKIM disablement workflow:
        1. Get current DKIM record info
        2. Disable DKIM in Plesk
        3. Remove DNS record from PowerDNS
        """
        print(f"Starting DKIM disablement for domain: {domain}")
        
        # Step 1: Get current DKIM record info
        print("Step 1: Getting current DKIM record info...")
        dkim_record = self.plesk.get_dkim_dns_record_formatted(domain)
        
        # Step 2: Disable DKIM in Plesk
        print("Step 2: Disabling DKIM in Plesk...")
        if not self.plesk.disable_dkim(domain):
            print("Failed to disable DKIM in Plesk")
            return False
        
        # Step 3: Remove DNS record from PowerDNS (if we have the record info)
        if dkim_record:
            print("Step 3: Removing DKIM record from PowerDNS...")
            zone_name = domain if domain.endswith('.') else f"{domain}."
            if not self.powerdns.delete_record(zone_name, dkim_record['name'], 'TXT', server_id):
                print("Failed to remove DKIM record from PowerDNS")
                return False
        
        print(f"✅ DKIM successfully disabled for {domain}")
        return True
    
    def list_domain_dkim_status(self) -> List[Dict]:
        """List DKIM status for all domains"""
        domains = self.plesk.get_domains()
        dkim_status = []
        
        for domain in domains:
            domain_name = domain.get('name', '')
            if domain_name:
                dkim_info = self.plesk.get_dkim_record(domain_name)
                status = {
                    'domain': domain_name,
                    'dkim_enabled': dkim_info is not None,
                    'selector': dkim_info.get('selector', '') if dkim_info else '',
                    'dns_record_name': f"{dkim_info.get('selector', '')}._domainkey.{domain_name}" if dkim_info else ''
                }
                dkim_status.append(status)
        
        return dkim_status
    
    def verify_dkim_dns_records(self, domain: str, server_id: str = 'localhost') -> Dict:
        """Verify DKIM DNS records in PowerDNS match Plesk configuration"""
        plesk_dkim = self.plesk.get_dkim_dns_record_formatted(domain)
        if not plesk_dkim:
            return {'status': 'error', 'message': 'DKIM not enabled in Plesk'}
        
        zone_name = domain if domain.endswith('.') else f"{domain}."
        powerdns_records = self.powerdns.find_dkim_records(zone_name, server_id)
        
        # Look for matching record
        matching_record = None
        for record in powerdns_records:
            if record.get('name') == plesk_dkim['name']:
                matching_record = record
                break
        
        if not matching_record:
            return {
                'status': 'mismatch',
                'message': f"DKIM record {plesk_dkim['name']} not found in PowerDNS"
            }
        
        # Compare content (basic check)
        powerdns_content = matching_record.get('records', [{}])[0].get('content', '')
        if plesk_dkim['content'] in powerdns_content or powerdns_content in plesk_dkim['content']:
            return {'status': 'match', 'message': 'DKIM records match'}
        else:
            return {
                'status': 'mismatch',
                'message': 'DKIM record content differs between Plesk and PowerDNS'
            }


def main():
    """Command line interface"""
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='DKIM Automation for Plesk and PowerDNS')
    parser.add_argument('action', choices=['enable', 'disable', 'list', 'verify'], 
                       help='Action to perform')
    parser.add_argument('--domain', '-d', help='Domain name')
    parser.add_argument('--selector', '-s', default='default', help='DKIM selector (default: default)')
    parser.add_argument('--server-id', default='localhost', help='PowerDNS server ID (default: localhost)')
    
    args = parser.parse_args()
    
    # Get credentials from environment
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_key = os.getenv('PLESK_API_KEY')
    powerdns_url = os.getenv('POWERDNS_SERVER_URL')
    powerdns_key = os.getenv('POWERDNS_API_KEY')
    
    if not all([plesk_url, plesk_key, powerdns_url, powerdns_key]):
        print("❌ Missing required environment variables:")
        print("   PLESK_SERVER_URL, PLESK_API_KEY, POWERDNS_SERVER_URL, POWERDNS_API_KEY")
        print("   Please check your .env file")
        sys.exit(1)
    
    # Initialize automation
    automation = DKIMAutomation(plesk_url, plesk_key, powerdns_url, powerdns_key)
    
    try:
        if args.action == 'enable':
            if not args.domain:
                print("❌ Domain is required for enable action")
                sys.exit(1)
            success = automation.enable_dkim_full_workflow(args.domain, args.selector, args.server_id)
            sys.exit(0 if success else 1)
        
        elif args.action == 'disable':
            if not args.domain:
                print("❌ Domain is required for disable action")
                sys.exit(1)
            success = automation.disable_dkim_full_workflow(args.domain, args.server_id)
            sys.exit(0 if success else 1)
        
        elif args.action == 'list':
            print("DKIM Status for all domains:")
            print("-" * 60)
            status_list = automation.list_domain_dkim_status()
            for status in status_list:
                enabled_str = "✅ Enabled" if status['dkim_enabled'] else "❌ Disabled"
                print(f"{status['domain']:<30} {enabled_str}")
                if status['dkim_enabled']:
                    print(f"{'':>30} Selector: {status['selector']}")
                    print(f"{'':>30} DNS: {status['dns_record_name']}")
        
        elif args.action == 'verify':
            if not args.domain:
                print("❌ Domain is required for verify action")
                sys.exit(1)
            result = automation.verify_dkim_dns_records(args.domain, args.server_id)
            print(f"Verification result for {args.domain}: {result['message']}")
            if result['status'] == 'match':
                print("✅ DKIM configuration is consistent")
            else:
                print("❌ DKIM configuration has issues")
    
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
