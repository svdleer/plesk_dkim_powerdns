#!/usr/bin/env python3
"""
Enhanced DKIM Automation Script
Uses Plesk XML API for better DKIM support and PowerDNS REST API
"""

import os
import sys
import argparse
from typing import List, Dict, Optional
from plesk_xml_api import PleskXMLAPIClient
from powerdns_manager import PowerDNSManager


class EnhancedDKIMAutomation:
    """Enhanced automation class using XML API for Plesk"""
    
    def __init__(self, plesk_url: str, plesk_key: str = None, powerdns_url: str = '', 
                 powerdns_key: str = '', plesk_username: str = None, plesk_password: str = None):
        """Initialize with API credentials"""
        self.plesk = PleskXMLAPIClient(plesk_url, plesk_key, plesk_username, plesk_password)
        self.powerdns = PowerDNSManager(powerdns_url, powerdns_key) if powerdns_url and powerdns_key else None
    
    def enable_dkim_full_workflow(self, domain: str, selector: str = "default", 
                                 key_size: int = 1024, server_id: str = 'localhost') -> bool:
        """
        Complete DKIM enablement workflow using XML API:
        1. Enable DKIM in Plesk via XML API
        2. Get the DKIM DNS record
        3. Create the record in PowerDNS
        """
        print(f"🚀 Starting enhanced DKIM enablement for domain: {domain}")
        
        # Step 1: Enable DKIM in Plesk using XML API
        print("Step 1: Enabling DKIM in Plesk (XML API)...")
        if not self.plesk.enable_dkim(domain, selector, key_size):
            print("❌ Failed to enable DKIM in Plesk")
            return False
        
        # Step 2: Get DKIM record from Plesk
        print("Step 2: Retrieving DKIM record from Plesk...")
        dkim_info = self.plesk.get_dkim_record_info(domain)
        if not dkim_info:
            print("❌ Failed to retrieve DKIM record from Plesk")
            return False
        
        print(f"📝 DKIM record details:")
        print(f"   Name: {dkim_info['dns_record_name']}")
        print(f"   Type: TXT")
        print(f"   Content: {dkim_info['dns_record_content']}")
        print(f"   Selector: {dkim_info['selector']}")
        
        # Step 3: Create DNS record in PowerDNS
        if self.powerdns:
            print("Step 3: Creating DKIM record in PowerDNS...")
            
            # Prepare record for PowerDNS
            dkim_record = {
                'domain': domain,
                'name': dkim_info['dns_record_name'],
                'type': 'TXT',
                'content': dkim_info['dns_record_content'],
                'ttl': 300
            }
            
            if not self.powerdns.create_dkim_record(dkim_record, server_id):
                print("❌ Failed to create DKIM record in PowerDNS")
                return False
            
            print(f"   🌐 PowerDNS server: {server_id}")
        else:
            print("Step 3: PowerDNS not configured, skipping DNS record creation")
            print(f"   💡 Manually add this DNS record:")
            print(f"   Name: {dkim_info['dns_record_name']}")
            print(f"   Type: TXT")
            print(f"   Content: {dkim_info['dns_record_content']}")
        
        print(f"✅ DKIM successfully enabled for {domain}")
        print(f"   🔑 Selector: {selector}")
        print(f"   🔐 Key size: {key_size} bits")
        print(f"   📝 DNS record: {dkim_info['dns_record_name']}")
        
        return True
    
    def disable_dkim_full_workflow(self, domain: str, server_id: str = 'localhost') -> bool:
        """
        Complete DKIM disablement workflow:
        1. Get current DKIM record info
        2. Disable DKIM in Plesk
        3. Remove DNS record from PowerDNS
        """
        print(f"🔓 Starting DKIM disablement for domain: {domain}")
        
        # Step 1: Get current DKIM record info
        print("Step 1: Getting current DKIM record info...")
        dkim_info = self.plesk.get_dkim_record_info(domain)
        
        # Step 2: Disable DKIM in Plesk
        print("Step 2: Disabling DKIM in Plesk...")
        if not self.plesk.disable_dkim(domain):
            print("❌ Failed to disable DKIM in Plesk")
            return False
        
        # Step 3: Remove DNS record from PowerDNS (if we have the record info)
        if dkim_info and self.powerdns:
            print("Step 3: Removing DKIM record from PowerDNS...")
            zone_name = domain if domain.endswith('.') else f"{domain}."
            record_name = dkim_info['dns_record_name']
            if not self.powerdns.delete_record(zone_name, record_name, 'TXT', server_id):
                print("⚠️  Failed to remove DKIM record from PowerDNS")
                print(f"   You may need to manually remove: {record_name}")
        elif dkim_info:
            print("Step 3: PowerDNS not configured")
            print(f"   💡 Manually remove this DNS record: {dkim_info['dns_record_name']}")
        else:
            print("Step 3: No DKIM record info available, skipping DNS cleanup")
        
        print(f"✅ DKIM successfully disabled for {domain}")
        return True
    
    def list_domain_dkim_status(self) -> List[Dict]:
        """List DKIM status for all domains using XML API"""
        domains = self.plesk.get_domains()
        dkim_status = []
        
        print(f"📊 Checking DKIM status for {len(domains)} domains...")
        
        for domain in domains:
            domain_name = domain.get('name', '')
            if domain_name:
                dkim_info = self.plesk.get_dkim_record_info(domain_name)
                status = {
                    'domain': domain_name,
                    'dkim_enabled': dkim_info is not None,
                    'selector': dkim_info.get('selector', '') if dkim_info else '',
                    'dns_record_name': dkim_info.get('dns_record_name', '') if dkim_info else '',
                    'has_public_key': bool(dkim_info and dkim_info.get('public_key'))
                }
                dkim_status.append(status)
        
        return dkim_status
    
    def verify_dkim_dns_records(self, domain: str, server_id: str = 'localhost') -> Dict:
        """Verify DKIM DNS records in PowerDNS match Plesk configuration"""
        print(f"🔍 Verifying DKIM configuration for {domain}...")
        
        # Get DKIM info from Plesk
        plesk_dkim = self.plesk.get_dkim_record_info(domain)
        if not plesk_dkim:
            return {
                'status': 'error', 
                'message': 'DKIM not enabled in Plesk or unable to retrieve record'
            }
        
        print(f"✅ DKIM enabled in Plesk with selector '{plesk_dkim['selector']}'")
        
        # Check PowerDNS
        if not self.powerdns:
            return {
                'status': 'info',
                'message': 'PowerDNS not configured - only checking Plesk configuration'
            }
        
        zone_name = domain if domain.endswith('.') else f"{domain}."
        powerdns_records = self.powerdns.find_dkim_records(zone_name, server_id)
        
        if not powerdns_records:
            return {
                'status': 'mismatch',
                'message': f"No DKIM records found in PowerDNS zone {zone_name}"
            }
        
        # Look for matching record
        expected_name = plesk_dkim['dns_record_name']
        if not expected_name.endswith('.'):
            expected_name += '.'
            
        matching_record = None
        for record in powerdns_records:
            record_name = record.get('name', '')
            if record_name == expected_name:
                matching_record = record
                break
        
        if not matching_record:
            return {
                'status': 'mismatch',
                'message': f"DKIM record {expected_name} not found in PowerDNS"
            }
        
        print(f"✅ DKIM record found in PowerDNS: {expected_name}")
        
        # Compare content (basic check - extract public key part)
        powerdns_content = matching_record.get('records', [{}])[0].get('content', '')
        plesk_content = plesk_dkim['dns_record_content']
        
        # Extract public key from both for comparison
        def extract_public_key(content):
            """Extract the p= value from DKIM record"""
            if 'p=' in content:
                start = content.find('p=') + 2
                end = content.find(';', start)
                if end == -1:
                    end = content.find('"', start)
                if end == -1:
                    end = len(content)
                return content[start:end].strip()
            return content
        
        plesk_key = extract_public_key(plesk_content)
        powerdns_key = extract_public_key(powerdns_content)
        
        if plesk_key and powerdns_key and (plesk_key in powerdns_key or powerdns_key in plesk_key):
            return {
                'status': 'match', 
                'message': 'DKIM records match between Plesk and PowerDNS',
                'details': {
                    'plesk_selector': plesk_dkim['selector'],
                    'dns_record': expected_name,
                    'powerdns_server': server_id
                }
            }
        else:
            return {
                'status': 'mismatch',
                'message': 'DKIM record content differs between Plesk and PowerDNS',
                'details': {
                    'plesk_content': plesk_content[:100] + '...' if len(plesk_content) > 100 else plesk_content,
                    'powerdns_content': powerdns_content[:100] + '...' if len(powerdns_content) > 100 else powerdns_content
                }
            }
    
    def get_dkim_record_for_manual_dns(self, domain: str) -> Optional[Dict]:
        """Get DKIM record information for manual DNS setup"""
        dkim_info = self.plesk.get_dkim_record_info(domain)
        if not dkim_info:
            return None
        
        return {
            'domain': domain,
            'record_name': dkim_info['dns_record_name'],
            'record_type': 'TXT',
            'record_content': dkim_info['dns_record_content'],
            'selector': dkim_info['selector'],
            'ttl_recommendation': 300
        }


def main():
    """Enhanced command line interface"""
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='Enhanced DKIM Automation for Plesk (XML API) and PowerDNS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s enable --domain example.com              # Enable DKIM with default settings
  %(prog)s enable --domain example.com --key-size 2048  # Enable with 2048-bit key
  %(prog)s disable --domain example.com             # Disable DKIM
  %(prog)s list                                      # List all domains
  %(prog)s verify --domain example.com              # Verify configuration
  %(prog)s record --domain example.com              # Get DNS record for manual setup
        """
    )
    
    parser.add_argument('action', 
                       choices=['enable', 'disable', 'list', 'verify', 'record'], 
                       help='Action to perform')
    parser.add_argument('--domain', '-d', 
                       help='Domain name')
    parser.add_argument('--selector', '-s', 
                       default='default', 
                       help='DKIM selector (default: default)')
    parser.add_argument('--key-size', '-k', 
                       type=int, choices=[1024, 2048], default=1024,
                       help='RSA key size in bits (default: 1024)')
    parser.add_argument('--server-id', 
                       default='localhost', 
                       help='PowerDNS server ID (default: localhost)')
    
    args = parser.parse_args()
    
    # Get credentials from environment
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_key = os.getenv('PLESK_API_KEY')
    plesk_username = os.getenv('PLESK_USERNAME')
    plesk_password = os.getenv('PLESK_PASSWORD')
    powerdns_url = os.getenv('POWERDNS_SERVER_URL')
    powerdns_key = os.getenv('POWERDNS_API_KEY')
    
    if not plesk_url:
        print("❌ Missing required environment variable: PLESK_SERVER_URL")
        sys.exit(1)
    
    # Check Plesk authentication
    if not ((plesk_username and plesk_password) or plesk_key):
        print("❌ Missing Plesk authentication credentials:")
        print("   Set either PLESK_USERNAME/PLESK_PASSWORD or PLESK_API_KEY")
        sys.exit(1)
    
    # PowerDNS is optional for some operations
    powerdns_required = args.action in ['enable', 'disable', 'verify']
    if powerdns_required and not all([powerdns_url, powerdns_key]):
        print("⚠️  PowerDNS not configured - some operations will be limited")
        print("   To enable full automation, set POWERDNS_SERVER_URL and POWERDNS_API_KEY")
    
    # Show authentication method
    if plesk_username and plesk_password:
        print(f"🔐 Using username/password authentication for {plesk_username}")
    else:
        print(f"🔐 Using API key authentication")
    
    # Initialize automation
    automation = EnhancedDKIMAutomation(plesk_url, plesk_key, 
                                       powerdns_url or '', powerdns_key or '',
                                       plesk_username, plesk_password)
    
    try:
        success = False
        
        if args.action == 'enable':
            if not args.domain:
                print("❌ Domain is required for enable action")
                sys.exit(1)
            success = automation.enable_dkim_full_workflow(
                args.domain, args.selector, args.key_size, args.server_id)
        
        elif args.action == 'disable':
            if not args.domain:
                print("❌ Domain is required for disable action")
                sys.exit(1)
            success = automation.disable_dkim_full_workflow(args.domain, args.server_id)
        
        elif args.action == 'list':
            print("📋 DKIM Status for all domains:")
            print("-" * 80)
            status_list = automation.list_domain_dkim_status()
            for status in status_list:
                enabled_str = "✅ Enabled" if status['dkim_enabled'] else "❌ Disabled"
                print(f"{status['domain']:<30} {enabled_str}")
                if status['dkim_enabled']:
                    print(f"{'':>30} 🔑 Selector: {status['selector']}")
                    print(f"{'':>30} 📝 DNS: {status['dns_record_name']}")
                    key_status = "✅" if status['has_public_key'] else "⚠️"
                    print(f"{'':>30} 🔐 Public Key: {key_status}")
            success = True
        
        elif args.action == 'verify':
            if not args.domain:
                print("❌ Domain is required for verify action")
                sys.exit(1)
            result = automation.verify_dkim_dns_records(args.domain, args.server_id)
            print(f"\n🔍 Verification result for {args.domain}:")
            print(f"   {result['message']}")
            if result['status'] == 'match':
                print("   ✅ DKIM configuration is consistent")
                if 'details' in result:
                    details = result['details']
                    print(f"   🔑 Selector: {details.get('plesk_selector')}")
                    print(f"   📝 DNS Record: {details.get('dns_record')}")
            else:
                print("   ❌ DKIM configuration has issues")
                if 'details' in result:
                    print("   📋 Details:", result['details'])
            success = result['status'] in ['match', 'error']
        
        elif args.action == 'record':
            if not args.domain:
                print("❌ Domain is required for record action")
                sys.exit(1)
            record_info = automation.get_dkim_record_for_manual_dns(args.domain)
            if record_info:
                print(f"📝 DKIM DNS Record for {args.domain}:")
                print(f"   Name: {record_info['record_name']}")
                print(f"   Type: {record_info['record_type']}")
                print(f"   Content: {record_info['record_content']}")
                print(f"   TTL: {record_info['ttl_recommendation']} (recommended)")
                print(f"   Selector: {record_info['selector']}")
                print(f"\n📋 DNS Zone File Format:")
                print(f"{record_info['record_name']} {record_info['ttl_recommendation']} IN {record_info['record_type']} {record_info['record_content']}")
                success = True
            else:
                print(f"❌ DKIM not enabled for {args.domain} or unable to retrieve record")
                success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
