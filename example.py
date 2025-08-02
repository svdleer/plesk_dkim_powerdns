#!/usr/bin/env python3
"""
Example usage script for DKIM automation
This script demonstrates how to use the DKIM automation classes
"""

import os
from dotenv import load_dotenv
from plesk_dkim import PleskDKIMManager
from powerdns_manager import PowerDNSManager
from dkim_automation import DKIMAutomation


def example_usage():
    """Example of using the DKIM automation"""
    
    # Load environment variables
    load_dotenv()
    
    # Check if environment variables are set
    required_vars = ['PLESK_SERVER_URL', 'PLESK_API_KEY', 'POWERDNS_SERVER_URL', 'POWERDNS_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease copy .env.example to .env and configure your settings")
        return
    
    print("🚀 DKIM Automation Example")
    print("=" * 50)
    
    # Initialize the automation
    automation = DKIMAutomation(
        plesk_url=os.getenv('PLESK_SERVER_URL'),
        plesk_key=os.getenv('PLESK_API_KEY'),
        powerdns_url=os.getenv('POWERDNS_SERVER_URL'),
        powerdns_key=os.getenv('POWERDNS_API_KEY')
    )
    
    # Example 1: List all domains and their DKIM status
    print("\n📋 Listing all domains and DKIM status:")
    try:
        domains_status = automation.list_domain_dkim_status()
        if domains_status:
            for status in domains_status:
                dkim_status = "✅ Enabled" if status['dkim_enabled'] else "❌ Disabled"
                print(f"   {status['domain']:<30} {dkim_status}")
                if status['dkim_enabled']:
                    print(f"      Selector: {status['selector']}")
        else:
            print("   No domains found or unable to retrieve domain list")
    except Exception as e:
        print(f"   Error listing domains: {e}")
    
    # Example 2: Test connectivity
    print("\n🔗 Testing API connectivity:")
    
    # Test Plesk connectivity
    try:
        plesk_domains = automation.plesk.get_domains()
        print(f"   Plesk: ✅ Connected ({len(plesk_domains)} domains found)")
    except Exception as e:
        print(f"   Plesk: ❌ Connection failed - {e}")
    
    # Test PowerDNS connectivity
    try:
        powerdns_servers = automation.powerdns.get_servers()
        print(f"   PowerDNS: ✅ Connected ({len(powerdns_servers)} servers found)")
    except Exception as e:
        print(f"   PowerDNS: ❌ Connection failed - {e}")
    
    print("\n" + "=" * 50)
    print("✨ Example completed!")
    print("\nTo enable DKIM for a domain, run:")
    print("   python dkim_automation.py enable --domain yourdomain.com")
    print("\nTo see all available commands, run:")
    print("   python dkim_automation.py --help")


if __name__ == "__main__":
    example_usage()
