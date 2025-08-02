#!/usr/bin/env python3
"""
Test alternative DKIM API methods for Plesk
"""

import os
from dotenv import load_dotenv
from plesk_xml_api import PleskXMLAPIClient

def test_dkim_alternatives():
    """Test different DKIM API approaches"""
    
    load_dotenv()
    
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_username = os.getenv('PLESK_USERNAME')
    plesk_password = os.getenv('PLESK_PASSWORD')
    
    client = PleskXMLAPIClient(plesk_url, None, plesk_username, plesk_password)
    domain = "oudheidkameralblasserdam.nl"
    site_id = 229
    
    print(f"Testing alternative DKIM methods for {domain}")
    print("=" * 60)
    
    # Test 1: Try direct DKIM operation
    print("1. Testing direct DKIM get operation...")
    xml_request1 = f"""<?xml version="1.0" encoding="UTF-8"?>
    <packet>
        <dkim>
            <get>
                <filter>
                    <site-id>{site_id}</site-id>
                </filter>
            </get>
        </dkim>
    </packet>"""
    
    try:
        root = client._make_xml_request(xml_request1)
        print("✅ DKIM operation worked!")
        import xml.etree.ElementTree as ET
        print(ET.tostring(root, encoding='unicode'))
    except Exception as e:
        print(f"❌ DKIM operation failed: {e}")
    
    print("\n" + "-" * 40)
    
    # Test 2: Try mail domain-specific DKIM
    print("2. Testing mail domain DKIM operation...")
    xml_request2 = f"""<?xml version="1.0" encoding="UTF-8"?>
    <packet>
        <mail>
            <domain>
                <get_dkim>
                    <filter>
                        <site-id>{site_id}</site-id>
                    </filter>
                </get_dkim>
            </domain>
        </mail>
    </packet>"""
    
    try:
        root = client._make_xml_request(xml_request2)
        print("✅ Mail domain DKIM worked!")
        print(ET.tostring(root, encoding='unicode'))
    except Exception as e:
        print(f"❌ Mail domain DKIM failed: {e}")
    
    print("\n" + "-" * 40)
    
    # Test 3: Check if DKIM is available in general
    print("3. Testing server capabilities for DKIM...")
    xml_request3 = """<?xml version="1.0" encoding="UTF-8"?>
    <packet>
        <server>
            <get>
                <stat>
                    <version/>
                </stat>
            </get>
        </server>
    </packet>"""
    
    try:
        root = client._make_xml_request(xml_request3)
        print("✅ Server info retrieved")
        # Look for DKIM-related capabilities
        version_info = root.find('.//version')
        if version_info is not None:
            print("Server version info available - checking for DKIM support...")
    except Exception as e:
        print(f"❌ Server info failed: {e}")

if __name__ == "__main__":
    test_dkim_alternatives()
