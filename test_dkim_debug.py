#!/usr/bin/env python3
"""
Test specific DKIM operations to find the correct XML structure
"""

import os
from dotenv import load_dotenv
from plesk_xml_api import PleskXMLAPIClient

def test_dkim_operations():
    """Test different approaches to DKIM operations"""
    
    load_dotenv()
    
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_username = os.getenv('PLESK_USERNAME')
    plesk_password = os.getenv('PLESK_PASSWORD')
    
    if not all([plesk_url, plesk_username, plesk_password]):
        print("Missing credentials")
        return
    
    client = PleskXMLAPIClient(plesk_url, None, plesk_username, plesk_password)
    domain = "oudheidkameralblasserdam.nl"
    site_id = 229  # We know this from previous test
    
    print(f"Testing DKIM operations for {domain} (site-id: {site_id})")
    print("=" * 60)
    
    # Test 1: Try to get current mail preferences to see available options
    print("1. Getting all mail preferences to see available options...")
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
        root = client._make_xml_request(xml_request)
        print("Raw response:")
        import xml.etree.ElementTree as ET
        print(ET.tostring(root, encoding='unicode'))
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 2: Try webspace-name instead of site-id
    print("2. Trying with webspace-name instead of site-id...")
    xml_request2 = f"""<?xml version="1.0" encoding="UTF-8"?>
    <packet>
        <mail>
            <get_prefs>
                <filter>
                    <webspace-name>{domain}</webspace-name>
                </filter>
            </get_prefs>
        </mail>
    </packet>"""
    
    try:
        root = client._make_xml_request(xml_request2)
        print("Raw response:")
        print(ET.tostring(root, encoding='unicode'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_dkim_operations()
