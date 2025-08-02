#!/usr/bin/env python3
"""
Plesk XML API Explorer
Helps discover the correct XML structure for your Plesk version
"""

import os
import xml.etree.ElementTree as ET
import requests
import urllib3
from dotenv import load_dotenv

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PleskXMLExplorer:
    """Explore Plesk XML API structure"""
    
    def __init__(self, server_url: str, username: str, password: str):
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'text/xml; charset=UTF-8',
            'HTTP_AUTH_LOGIN': username,
            'HTTP_AUTH_PASSWD': password,
        })
        self.session.verify = False  # Disable SSL verification
        
    def _make_request(self, xml_data: str) -> ET.Element:
        """Make XML API request"""
        url = f"{self.server_url}/enterprise/control/agent.php"
        
        try:
            response = self.session.post(url, data=xml_data, timeout=30)
            response.raise_for_status()
            
            print(f"✅ Request successful (Status: {response.status_code})")
            root = ET.fromstring(response.text)
            return root
            
        except Exception as e:
            print(f"❌ Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text[:500]}")
            raise
    
    def test_server_info(self):
        """Test basic server info request"""
        print("🔍 Testing server info request...")
        
        xml_request = """<?xml version="1.0" encoding="UTF-8"?>
        <packet>
            <server>
                <get>
                    <stat/>
                </get>
            </server>
        </packet>"""
        
        try:
            root = self._make_request(xml_request)
            
            # Pretty print the response
            print("📋 Server info response:")
            self._pretty_print_xml(root)
            return True
            
        except Exception as e:
            print(f"Server info test failed: {e}")
            return False
    
    def test_domain_listing(self):
        """Test different ways to list domains"""
        print("\n🔍 Testing domain listing methods...")
        
        methods = [
            ("webspace", """<?xml version="1.0" encoding="UTF-8"?>
            <packet>
                <webspace>
                    <get>
                        <filter/>
                        <dataset>
                            <gen_info/>
                        </dataset>
                    </get>
                </webspace>
            </packet>"""),
            
            ("site", """<?xml version="1.0" encoding="UTF-8"?>
            <packet>
                <site>
                    <get>
                        <filter/>
                        <dataset>
                            <gen_info/>
                        </dataset>
                    </get>
                </site>
            </packet>"""),
            
            ("domain", """<?xml version="1.0" encoding="UTF-8"?>
            <packet>
                <domain>
                    <get>
                        <filter/>
                        <dataset>
                            <gen_info/>
                        </dataset>
                    </get>
                </domain>
            </packet>""")
        ]
        
        successful_methods = []
        
        for method_name, xml_request in methods:
            print(f"\n📋 Testing {method_name} method...")
            try:
                root = self._make_request(xml_request)
                
                # Check for results
                results = root.findall(f'.//{method_name}/get/result')
                if results:
                    print(f"✅ {method_name} method works! Found {len(results)} items")
                    successful_methods.append(method_name)
                    
                    # Show first result
                    for i, result in enumerate(results[:2]):  # Show first 2
                        status = result.find('status')
                        if status is not None and status.text == 'ok':
                            gen_info = result.find('data/gen_info')
                            if gen_info is not None:
                                name = gen_info.find('name')
                                if name is not None:
                                    print(f"   Item {i+1}: {name.text}")
                else:
                    print(f"⚠️  {method_name} method returned no results")
                    
            except Exception as e:
                print(f"❌ {method_name} method failed: {e}")
        
        return successful_methods
    
    def test_mail_operations(self, domain_name: str):
        """Test mail operations for a specific domain"""
        print(f"\n🔍 Testing mail operations for {domain_name}...")
        
        methods = [
            ("webspace-name", f"""<?xml version="1.0" encoding="UTF-8"?>
            <packet>
                <mail>
                    <get_prefs>
                        <filter>
                            <webspace-name>{domain_name}</webspace-name>
                        </filter>
                    </get_prefs>
                </mail>
            </packet>"""),
            
            ("site-name", f"""<?xml version="1.0" encoding="UTF-8"?>
            <packet>
                <mail>
                    <get_prefs>
                        <filter>
                            <site-name>{domain_name}</site-name>
                        </filter>
                    </get_prefs>
                </mail>
            </packet>"""),
            
            ("domain-name", f"""<?xml version="1.0" encoding="UTF-8"?>
            <packet>
                <mail>
                    <get_prefs>
                        <filter>
                            <domain-name>{domain_name}</domain-name>
                        </filter>
                    </get_prefs>
                </mail>
            </packet>""")
        ]
        
        for method_name, xml_request in methods:
            print(f"\n📋 Testing mail get_prefs with {method_name}...")
            try:
                root = self._make_request(xml_request)
                
                result = root.find('.//mail/get_prefs/result')
                if result is not None:
                    status = result.find('status')
                    if status is not None and status.text == 'ok':
                        print(f"✅ {method_name} works for mail operations!")
                        
                        # Show preferences
                        prefs = result.find('prefs')
                        if prefs is not None:
                            print("   Mail preferences found:")
                            for pref in prefs:
                                print(f"     {pref.tag}: {pref.text}")
                        return method_name
                    else:
                        error = result.find('errtext')
                        error_text = error.text if error else 'Unknown error'
                        print(f"❌ {method_name} failed: {error_text}")
                else:
                    print(f"⚠️  {method_name}: No result element found")
                    
            except Exception as e:
                print(f"❌ {method_name} failed with exception: {e}")
        
        return None
    
    def _pretty_print_xml(self, element, indent="  "):
        """Pretty print XML element"""
        def _indent_xml(elem, level=0):
            i = "\n" + level * indent
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + indent
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    _indent_xml(child, level + 1)
                if not child.tail or not child.tail.strip():
                    child.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
        
        _indent_xml(element)
        xml_str = ET.tostring(element, encoding='unicode')
        print(xml_str[:1000] + "..." if len(xml_str) > 1000 else xml_str)
    
    def generate_working_examples(self, successful_domain_method: str, successful_mail_method: str):
        """Generate working XML examples based on test results"""
        print(f"\n🎉 Generating working examples...")
        print(f"Domain listing method: {successful_domain_method}")
        print(f"Mail operations method: {successful_mail_method}")
        
        examples = {
            'list_domains': f"""<?xml version="1.0" encoding="UTF-8"?>
<packet>
    <{successful_domain_method}>
        <get>
            <filter/>
            <dataset>
                <gen_info/>
            </dataset>
        </get>
    </{successful_domain_method}>
</packet>""",
            
            'get_mail_prefs': f"""<?xml version="1.0" encoding="UTF-8"?>
<packet>
    <mail>
        <get_prefs>
            <filter>
                <{successful_mail_method}>DOMAIN_NAME</{successful_mail_method}>
            </filter>
        </get_prefs>
    </mail>
</packet>""",
            
            'enable_dkim': f"""<?xml version="1.0" encoding="UTF-8"?>
<packet>
    <mail>
        <set_prefs>
            <filter>
                <{successful_mail_method}>DOMAIN_NAME</{successful_mail_method}>
            </filter>
            <prefs>
                <dkim_status>true</dkim_status>
                <dkim_selector>default</dkim_selector>
                <dkim_key_size>1024</dkim_key_size>
            </prefs>
        </set_prefs>
    </mail>
</packet>""",
            
            'get_dkim_key': f"""<?xml version="1.0" encoding="UTF-8"?>
<packet>
    <mail>
        <get_dkim_key>
            <filter>
                <{successful_mail_method}>DOMAIN_NAME</{successful_mail_method}>
            </filter>
        </get_dkim_key>
    </mail>
</packet>"""
        }
        
        return examples


def main():
    """Main exploration function"""
    load_dotenv()
    
    # Get credentials
    plesk_url = os.getenv('PLESK_SERVER_URL')
    plesk_username = os.getenv('PLESK_USERNAME')
    plesk_password = os.getenv('PLESK_PASSWORD')
    
    if not all([plesk_url, plesk_username, plesk_password]):
        print("❌ Missing required environment variables:")
        print("   PLESK_SERVER_URL, PLESK_USERNAME, PLESK_PASSWORD")
        return
    
    print("🚀 Plesk XML API Explorer")
    print("=" * 50)
    print(f"Server: {plesk_url}")
    print(f"Username: {plesk_username}")
    print("=" * 50)
    
    explorer = PleskXMLExplorer(plesk_url, plesk_username, plesk_password)
    
    # Test 1: Server info
    if not explorer.test_server_info():
        print("❌ Basic server test failed. Check credentials and connectivity.")
        return
    
    # Test 2: Domain listing
    successful_domain_methods = explorer.test_domain_listing()
    if not successful_domain_methods:
        print("❌ No working domain listing methods found.")
        return
    
    # Get first domain for testing mail operations
    print(f"\n🔍 Using {successful_domain_methods[0]} method to get a domain for testing...")
    
    # Test 3: Mail operations (you might need to specify a domain)
    test_domain = input("\nEnter a domain name to test mail operations (or press Enter to skip): ").strip()
    
    if test_domain:
        successful_mail_method = explorer.test_mail_operations(test_domain)
        
        if successful_mail_method:
            examples = explorer.generate_working_examples(successful_domain_methods[0], successful_mail_method)
            
            print(f"\n📝 Working XML Examples:")
            print("=" * 50)
            for name, xml in examples.items():
                print(f"\n{name.upper()}:")
                print(xml)
        else:
            print("❌ No working mail operation methods found for this domain.")
    
    print(f"\n🎉 Exploration complete!")
    print(f"Working domain method: {successful_domain_methods[0] if successful_domain_methods else 'None'}")


if __name__ == "__main__":
    main()
