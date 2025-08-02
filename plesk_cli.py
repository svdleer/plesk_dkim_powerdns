#!/usr/bin/env python3
"""
Plesk CLI Utility for DKIM operations using XML API
Command-line interface for managing DKIM via Plesk XML API
"""

import os
import sys
import argparse
from typing import List, Dict
from plesk_xml_api import PleskXMLAPIClient


class PleskDKIMCLI:
    """CLI interface for Plesk DKIM operations"""
    
    def __init__(self, server_url: str, api_key: str = None, username: str = None, password: str = None):
        """Initialize CLI with Plesk credentials"""
        self.client = PleskXMLAPIClient(server_url, api_key, username, password)
    
    def list_domains(self) -> bool:
        """List all domains and their DKIM status"""
        print("📋 Listing all domains and DKIM status...")
        print("-" * 70)
        
        try:
            domains = self.client.get_domains()
            if not domains:
                print("No domains found")
                return False
            
            for domain in domains:
                domain_name = domain['name']
                print(f"\n🌐 Domain: {domain_name}")
                
                # Get DKIM status
                dkim_info = self.client.get_dkim_record_info(domain_name)
                if dkim_info:
                    print(f"   ✅ DKIM: Enabled")
                    print(f"   🔑 Selector: {dkim_info['selector']}")
                    print(f"   📝 DNS Record: {dkim_info['dns_record_name']}")
                else:
                    mail_settings = self.client.get_mail_settings(domain_name)
                    if mail_settings:
                        dkim_status = mail_settings.get('dkim_status', 'false')
                        if dkim_status.lower() == 'true':
                            print(f"   ⚠️  DKIM: Enabled but key retrieval failed")
                        else:
                            print(f"   ❌ DKIM: Disabled")
                    else:
                        print(f"   ❓ DKIM: Status unknown (mail not configured)")
            
            print(f"\n📊 Total domains: {len(domains)}")
            return True
            
        except Exception as e:
            print(f"❌ Error listing domains: {e}")
            return False
    
    def enable_dkim(self, domain: str, selector: str = "default", key_size: int = 1024) -> bool:
        """Enable DKIM for a domain"""
        print(f"🔐 Enabling DKIM for domain: {domain}")
        print(f"   Selector: {selector}")
        print(f"   Key size: {key_size} bits")
        
        try:
            success = self.client.enable_dkim(domain, selector, key_size)
            if success:
                print(f"✅ DKIM successfully enabled for {domain}")
                
                # Try to get the DNS record information
                print("\n📝 Retrieving DNS record information...")
                dkim_info = self.client.get_dkim_record_info(domain)
                if dkim_info:
                    print(f"DNS Record Details:")
                    print(f"   Name: {dkim_info['dns_record_name']}")
                    print(f"   Type: TXT")
                    print(f"   Content: {dkim_info['dns_record_content']}")
                    print(f"\n💡 Add this record to your DNS zone to complete DKIM setup")
                else:
                    print("⚠️  DKIM enabled but could not retrieve DNS record details")
                
                return True
            else:
                print(f"❌ Failed to enable DKIM for {domain}")
                return False
                
        except Exception as e:
            print(f"❌ Error enabling DKIM: {e}")
            return False
    
    def disable_dkim(self, domain: str) -> bool:
        """Disable DKIM for a domain"""
        print(f"🔓 Disabling DKIM for domain: {domain}")
        
        try:
            success = self.client.disable_dkim(domain)
            if success:
                print(f"✅ DKIM successfully disabled for {domain}")
                print("💡 Don't forget to remove the DKIM DNS record from your DNS zone")
                return True
            else:
                print(f"❌ Failed to disable DKIM for {domain}")
                return False
                
        except Exception as e:
            print(f"❌ Error disabling DKIM: {e}")
            return False
    
    def get_dkim_record(self, domain: str) -> bool:
        """Get DKIM DNS record for a domain"""
        print(f"📋 Getting DKIM record for domain: {domain}")
        
        try:
            dkim_info = self.client.get_dkim_record_info(domain)
            if dkim_info:
                print(f"\n✅ DKIM is enabled for {domain}")
                print(f"DNS Record Details:")
                print(f"   Name: {dkim_info['dns_record_name']}")
                print(f"   Type: TXT")
                print(f"   Content: {dkim_info['dns_record_content']}")
                print(f"   Selector: {dkim_info['selector']}")
                
                # Also output in a format suitable for copy-paste
                print(f"\n📋 Copy-paste format:")
                print(f"{dkim_info['dns_record_name']} IN TXT {dkim_info['dns_record_content']}")
                
                return True
            else:
                print(f"❌ DKIM is not enabled for {domain}")
                return False
                
        except Exception as e:
            print(f"❌ Error getting DKIM record: {e}")
            return False
    
    def verify_domain(self, domain: str) -> bool:
        """Verify DKIM configuration for a domain"""
        print(f"🔍 Verifying DKIM configuration for domain: {domain}")
        
        try:
            # Check if domain exists
            domains = self.client.get_domains()
            domain_exists = any(d['name'] == domain for d in domains)
            
            if not domain_exists:
                print(f"❌ Domain {domain} not found in Plesk")
                return False
            
            print(f"✅ Domain {domain} found in Plesk")
            
            # Check mail settings
            mail_settings = self.client.get_mail_settings(domain)
            if not mail_settings:
                print(f"⚠️  Mail service not configured for {domain}")
                return False
            
            print(f"✅ Mail service configured")
            
            # Check DKIM status
            dkim_info = self.client.get_dkim_record_info(domain)
            if dkim_info:
                print(f"✅ DKIM enabled with selector '{dkim_info['selector']}'")
                print(f"✅ Public key retrieved successfully")
                print(f"📝 DNS record: {dkim_info['dns_record_name']}")
                
                # Additional verification could include DNS lookup here
                print(f"\n💡 To complete verification, ensure the DNS record is published:")
                print(f"   dig TXT {dkim_info['dns_record_name']}")
                
                return True
            else:
                dkim_status = mail_settings.get('dkim_status', 'false')
                if dkim_status.lower() == 'true':
                    print(f"⚠️  DKIM appears enabled but public key retrieval failed")
                else:
                    print(f"❌ DKIM not enabled")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying domain: {e}")
            return False


def main():
    """Command line interface"""
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='Plesk DKIM CLI Utility (XML API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                              # List all domains
  %(prog)s enable --domain example.com       # Enable DKIM
  %(prog)s disable --domain example.com      # Disable DKIM
  %(prog)s record --domain example.com       # Get DNS record
  %(prog)s verify --domain example.com       # Verify configuration

Authentication:
  Set either PLESK_USERNAME/PLESK_PASSWORD or PLESK_API_KEY in .env file
        """
    )
    
    parser.add_argument('action', 
                       choices=['list', 'enable', 'disable', 'record', 'verify'],
                       help='Action to perform')
    parser.add_argument('--domain', '-d', 
                       help='Domain name')
    parser.add_argument('--selector', '-s', 
                       default='default',
                       help='DKIM selector (default: default)')
    parser.add_argument('--key-size', '-k', 
                       type=int, choices=[1024, 2048], default=1024,
                       help='RSA key size in bits (default: 1024)')
    
    args = parser.parse_args()
    
    # Get credentials from environment
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_key = os.getenv('PLESK_API_KEY')
    plesk_username = os.getenv('PLESK_USERNAME')
    plesk_password = os.getenv('PLESK_PASSWORD')
    
    if not plesk_url:
        print("❌ Missing required environment variable: PLESK_SERVER_URL")
        sys.exit(1)
    
    # Check authentication credentials
    if plesk_username and plesk_password:
        print(f"🔐 Using username/password authentication for {plesk_username}")
        cli = PleskDKIMCLI(plesk_url, None, plesk_username, plesk_password)
    elif plesk_key:
        print(f"🔐 Using API key authentication")
        cli = PleskDKIMCLI(plesk_url, plesk_key)
    else:
        print("❌ Missing authentication credentials:")
        print("   Set either PLESK_USERNAME/PLESK_PASSWORD or PLESK_API_KEY")
        print("   Please check your .env file")
        sys.exit(1)
    
    try:
        success = False
        
        if args.action == 'list':
            success = cli.list_domains()
        
        elif args.action == 'enable':
            if not args.domain:
                print("❌ Domain is required for enable action")
                sys.exit(1)
            success = cli.enable_dkim(args.domain, args.selector, args.key_size)
        
        elif args.action == 'disable':
            if not args.domain:
                print("❌ Domain is required for disable action")
                sys.exit(1)
            success = cli.disable_dkim(args.domain)
        
        elif args.action == 'record':
            if not args.domain:
                print("❌ Domain is required for record action")
                sys.exit(1)
            success = cli.get_dkim_record(args.domain)
        
        elif args.action == 'verify':
            if not args.domain:
                print("❌ Domain is required for verify action")
                sys.exit(1)
            success = cli.verify_domain(args.domain)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
