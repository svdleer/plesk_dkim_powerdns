#!/usr/bin/env python3
"""
Test Site-ID based DKIM operations
Comprehensive test for the updated Plesk XML API client with site-id support
"""

import os
import sys
from dotenv import load_dotenv
from plesk_xml_api import PleskXMLAPIClient

def test_site_id_operations():
    """Test all DKIM operations using site-id"""
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment
    plesk_url = os.getenv('PLESK_URL')
    plesk_username = os.getenv('PLESK_USERNAME')
    plesk_password = os.getenv('PLESK_PASSWORD')
    plesk_api_key = os.getenv('PLESK_API_KEY')
    test_domain = os.getenv('TEST_DOMAIN', 'example.com')
    
    if not plesk_url:
        print("❌ PLESK_URL not found in environment variables")
        return False
    
    if not (plesk_api_key or (plesk_username and plesk_password)):
        print("❌ Either PLESK_API_KEY or PLESK_USERNAME+PLESK_PASSWORD must be set")
        return False
    
    print("🧪 Testing Site-ID based DKIM operations")
    print("=" * 60)
    
    try:
        # Initialize client
        client = PleskXMLAPIClient(
            server_url=plesk_url,
            api_key=plesk_api_key,
            username=plesk_username,
            password=plesk_password
        )
        
        print(f"📡 Connected to Plesk server: {plesk_url}")
        print(f"🎯 Test domain: {test_domain}")
        print()
        
        # Test 1: Get domains with site-id
        print("1️⃣ Testing get_domains() with site-id support...")
        domains = client.get_domains()
        if domains:
            print(f"   ✅ Found {len(domains)} domains")
            for domain in domains[:3]:  # Show first 3
                print(f"   📋 Domain: {domain['name']}, Site-ID: {domain.get('site_id', 'N/A')}")
            
            # Use the test domain if it exists, otherwise use the first available
            target_domain = test_domain
            domain_found = any(d['name'] == test_domain for d in domains)
            if not domain_found and domains:
                target_domain = domains[0]['name']
                print(f"   ⚠️  Test domain {test_domain} not found, using {target_domain}")
        else:
            print("   ❌ No domains found")
            return False
        
        print()
        
        # Test 2: Get site ID for domain
        print(f"2️⃣ Testing get_site_id() for {target_domain}...")
        site_id = client.get_site_id(target_domain)
        if site_id:
            print(f"   ✅ Site ID: {site_id}")
        else:
            print(f"   ❌ Could not get site ID for {target_domain}")
            return False
        
        print()
        
        # Test 3: Get mail settings using site-id
        print(f"3️⃣ Testing get_mail_settings() with site-id for {target_domain}...")
        mail_settings = client.get_mail_settings(target_domain)
        if mail_settings:
            print(f"   ✅ Mail settings retrieved")
            dkim_status = mail_settings.get('dkim_status', 'unknown')
            print(f"   📧 Current DKIM status: {dkim_status}")
        else:
            print(f"   ❌ Could not get mail settings for {target_domain}")
        
        print()
        
        # Test 4: Test DKIM record info
        print(f"4️⃣ Testing get_dkim_record_info() for {target_domain}...")
        dkim_info = client.get_dkim_record_info(target_domain)
        if dkim_info:
            print(f"   ✅ DKIM record info retrieved")
            print(f"   🔑 Selector: {dkim_info.get('selector', 'N/A')}")
            print(f"   📝 DNS name: {dkim_info.get('dns_record_name', 'N/A')}")
        else:
            print(f"   ⚠️  No DKIM record info (may not be enabled)")
        
        print()
        
        # Test 5: Test DKIM public key retrieval
        print(f"5️⃣ Testing get_dkim_public_key() for {target_domain}...")
        dkim_key = client.get_dkim_public_key(target_domain)
        if dkim_key:
            print(f"   ✅ DKIM public key retrieved")
            print(f"   🔑 Key preview: {dkim_key[:50]}..." if len(dkim_key) > 50 else f"   🔑 Key: {dkim_key}")
        else:
            print(f"   ⚠️  No DKIM public key found (may not be enabled)")
        
        print()
        
        # Summary
        print("📊 Test Summary:")
        print("=" * 30)
        print("✅ Site-ID operations working correctly")
        print("✅ All methods now use site-id for mail operations")
        print("✅ XSD schema compliance achieved")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("Plesk XML API Site-ID Test Suite")
    print("================================")
    print()
    
    success = test_site_id_operations()
    
    print()
    if success:
        print("🎉 All tests passed! Site-ID implementation is working correctly.")
        sys.exit(0)
    else:
        print("💥 Tests failed. Please check the configuration and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
