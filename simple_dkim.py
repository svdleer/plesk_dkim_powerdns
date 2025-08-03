#!/usr/bin/env python3
"""
Simplified DKIM Manager for Plesk
Based on proven XML API calls that work
"""

import os
import sys
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import urllib3
import subprocess
import re
import socket
import dns.resolver
import dns.exception

# Import PowerDNS manager
from powerdns_manager import PowerDNSManager

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SimplePleskDKIM:
    """Simple Plesk DKIM manager using proven XML API calls"""
    
    def __init__(self, plesk_url: str, api_key: str, ssh_hostname: str = None, ssh_username: str = 'admin', ssh_key_path: str = None, powerdns_manager: PowerDNSManager = None):
        """
        Initialize with Plesk server URL and API key
        
        Args:
            plesk_url: Full Plesk URL (e.g., https://server.com:8443/enterprise/control/agent.php)
            api_key: Plesk API key
            ssh_hostname: SSH hostname for DKIM key extraction (optional)
            ssh_username: SSH username (default: admin)
            ssh_key_path: Path to SSH private key (optional)
            powerdns_manager: PowerDNS manager instance for DNS record creation (optional)
        """
        self.plesk_url = plesk_url
        self.api_key = api_key
        self.ssh_hostname = ssh_hostname
        self.ssh_username = ssh_username
        self.ssh_key_path = ssh_key_path
        self.powerdns_manager = powerdns_manager
    
    def run_prechecks(self) -> Dict[str, any]:
        """
        Run comprehensive prechecks for Plesk and PowerDNS connectivity
        
        Returns:
            Dict with check results and any issues found
        """
        print("🔍 Running prechecks...")
        results = {
            'overall_status': True,
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Check 1: Plesk XML API connectivity
        print("   📡 Testing Plesk XML API connectivity...")
        try:
            domains = self.get_all_domains()
            if domains:
                results['checks']['plesk_api'] = {
                    'status': True,
                    'message': f"✅ Connected successfully - found {len(domains)} domains"
                }
            else:
                results['checks']['plesk_api'] = {
                    'status': False,
                    'message': "❌ API connected but no domains found"
                }
                results['overall_status'] = False
                results['errors'].append("No domains found - check API permissions")
        except Exception as e:
            results['checks']['plesk_api'] = {
                'status': False,
                'message': f"❌ API connection failed: {str(e)}"
            }
            results['overall_status'] = False
            results['errors'].append(f"Plesk API connection failed: {str(e)}")
        
        # Check 2: SSH connectivity (if configured)
        if self.ssh_hostname:
            print("   🔐 Testing SSH connectivity...")
            try:
                success, stdout, stderr = self._execute_ssh_command("echo 'SSH test'", use_sudo=False)
                if success:
                    results['checks']['ssh'] = {
                        'status': True,
                        'message': "✅ SSH connection successful"
                    }
                else:
                    results['checks']['ssh'] = {
                        'status': False,
                        'message': f"❌ SSH connection failed: {stderr}"
                    }
                    results['overall_status'] = False
                    results['errors'].append(f"SSH connection failed: {stderr}")
            except Exception as e:
                results['checks']['ssh'] = {
                    'status': False,
                    'message': f"❌ SSH test failed: {str(e)}"
                }
                results['overall_status'] = False
                results['errors'].append(f"SSH test failed: {str(e)}")
        else:
            results['checks']['ssh'] = {
                'status': True,
                'message': "⚠️  SSH not configured - DKIM key extraction will not work"
            }
            results['warnings'].append("SSH not configured - DKIM key extraction will not work")
        
        # Check 3: DKIM key directory access (if SSH available)
        if self.ssh_hostname and results['checks']['ssh']['status']:
            print("   🔑 Testing DKIM key directory access...")
            try:
                # Test multiple possible DKIM key directories with sudo
                dkim_directories = [
                    "/etc/domainkeys",
                    "/var/qmail/control/domainkeys", 
                    "/opt/psa/var/modules/domainkeys",
                    "/usr/local/psa/var/modules/domainkeys"
                ]
                
                accessible_dirs = []
                for dkim_dir in dkim_directories:
                    success, stdout, stderr = self._execute_ssh_command(f"ls -la {dkim_dir} 2>/dev/null | head -3", use_sudo=True)
                    if success and stdout.strip():
                        accessible_dirs.append(dkim_dir)
                
                if accessible_dirs:
                    results['checks']['dkim_keys'] = {
                        'status': True,
                        'message': f"✅ DKIM key directories accessible: {', '.join(accessible_dirs)}"
                    }
                else:
                    results['checks']['dkim_keys'] = {
                        'status': False,
                        'message': "❌ No DKIM key directories accessible"
                    }
                    results['warnings'].append("No DKIM key directories accessible - key extraction may fail")
            except Exception as e:
                results['checks']['dkim_keys'] = {
                    'status': False,
                    'message': f"❌ DKIM key directory test failed: {str(e)}"
                }
                results['warnings'].append("DKIM key directory test failed")
        
        # Check 4: PowerDNS connectivity (if configured)
        if self.powerdns_manager:
            print("   🌐 Testing PowerDNS connectivity...")
            try:
                # Try to get server information via PowerDNS manager
                test_result = self.powerdns_manager.test_connection()
                if test_result:
                    results['checks']['powerdns'] = {
                        'status': True,
                        'message': "✅ PowerDNS connection successful"
                    }
                else:
                    results['checks']['powerdns'] = {
                        'status': False,
                        'message': "❌ PowerDNS connection failed"
                    }
                    results['warnings'].append("PowerDNS connection failed - DNS record management will not work")
            except Exception as e:
                results['checks']['powerdns'] = {
                    'status': False,
                    'message': f"❌ PowerDNS test failed: {str(e)}"
                }
                results['warnings'].append(f"PowerDNS test failed: {str(e)}")
        else:
            results['checks']['powerdns'] = {
                'status': True,
                'message': "⚠️  PowerDNS not configured - DNS record management will not work"
            }
            results['warnings'].append("PowerDNS not configured - DNS record management will not work")
        
        # Check 5: OpenSSL availability (if SSH available)
        if self.ssh_hostname and results['checks']['ssh']['status']:
            print("   🔧 Testing OpenSSL availability...")
            try:
                success, stdout, stderr = self._execute_ssh_command("openssl version", use_sudo=False)
                if success and "OpenSSL" in stdout:
                    results['checks']['openssl'] = {
                        'status': True,
                        'message': f"✅ OpenSSL available: {stdout.strip()}"
                    }
                else:
                    results['checks']['openssl'] = {
                        'status': False,
                        'message': "❌ OpenSSL not available"
                    }
                    results['warnings'].append("OpenSSL not available - DKIM key extraction will fail")
            except Exception as e:
                results['checks']['openssl'] = {
                    'status': False,
                    'message': f"❌ OpenSSL test failed: {str(e)}"
                }
                results['warnings'].append("OpenSSL test failed")
        
        return results
    
    def get_server_ip(self) -> Optional[str]:
        """Get the IP address of the current Plesk server"""
        try:
            # Try to resolve the hostname to get the server IP
            if self.ssh_hostname:
                return socket.gethostbyname(self.ssh_hostname)
            return None
        except socket.gaierror:
            return None
    
    def validate_domain_dns(self, domain: str) -> Dict[str, any]:
        """
        Validate domain DNS configuration before enabling DKIM
        
        Args:
            domain: Domain name to validate
            
        Returns:
            Dict with validation results
        """
        print(f"🔍 Validating DNS configuration for {domain}...")
        
        validation_results = {
            'domain': domain,
            'valid': True,
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Get server IP for comparison
        server_ip = self.get_server_ip()
        if not server_ip:
            validation_results['warnings'].append(f"Could not determine server IP for {self.ssh_hostname}")
        
        # Check 1: A record validation
        print(f"   🌐 Checking A record for {domain}...")
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 10
            resolver.lifetime = 10
            
            a_records = resolver.resolve(domain, 'A')
            domain_ips = [str(rdata) for rdata in a_records]
            
            if domain_ips:
                validation_results['checks']['a_record'] = {
                    'status': True,
                    'ips': domain_ips,
                    'message': f"✅ A record found: {', '.join(domain_ips)}"
                }
                
                # Check if domain points to this server
                if server_ip and server_ip in domain_ips:
                    validation_results['checks']['a_record']['points_to_server'] = True
                    validation_results['checks']['a_record']['message'] += f" (points to this server: {server_ip})"
                elif server_ip:
                    validation_results['checks']['a_record']['points_to_server'] = False
                    validation_results['warnings'].append(f"Domain A record ({', '.join(domain_ips)}) does not point to this server ({server_ip})")
                else:
                    validation_results['checks']['a_record']['points_to_server'] = None
                    validation_results['warnings'].append("Cannot verify if domain points to this server (server IP unknown)")
            else:
                validation_results['checks']['a_record'] = {
                    'status': False,
                    'message': "❌ No A record found"
                }
                validation_results['valid'] = False
                validation_results['errors'].append("No A record found for domain")
                
        except dns.exception.DNSException as e:
            validation_results['checks']['a_record'] = {
                'status': False,
                'message': f"❌ A record lookup failed: {str(e)}"
            }
            validation_results['valid'] = False
            validation_results['errors'].append(f"A record lookup failed: {str(e)}")
        
        # Check 2: NS record validation
        print(f"   🏛️  Checking NS records for {domain}...")
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 10
            resolver.lifetime = 10
            
            ns_records = resolver.resolve(domain, 'NS')
            nameservers = [str(rdata).rstrip('.').lower() for rdata in ns_records]
            
            # Expected nameservers
            expected_ns = ['ns1.avant-int.nl', 'ns2.avant-int.nl']
            
            if nameservers:
                validation_results['checks']['ns_records'] = {
                    'status': True,
                    'nameservers': nameservers,
                    'message': f"✅ NS records found: {', '.join(nameservers)}"
                }
                
                # Check if using expected nameservers
                valid_ns = any(ns in expected_ns for ns in nameservers)
                if valid_ns:
                    validation_results['checks']['ns_records']['valid_ns'] = True
                    matching_ns = [ns for ns in nameservers if ns in expected_ns]
                    validation_results['checks']['ns_records']['message'] += f" (using expected NS: {', '.join(matching_ns)})"
                else:
                    validation_results['checks']['ns_records']['valid_ns'] = False
                    validation_results['warnings'].append(f"Domain uses unexpected nameservers. Expected: {', '.join(expected_ns)}, Found: {', '.join(nameservers)}")
            else:
                validation_results['checks']['ns_records'] = {
                    'status': False,
                    'message': "❌ No NS records found"
                }
                validation_results['warnings'].append("No NS records found for domain")
                
        except dns.exception.DNSException as e:
            validation_results['checks']['ns_records'] = {
                'status': False,
                'message': f"❌ NS record lookup failed: {str(e)}"
            }
            validation_results['warnings'].append(f"NS record lookup failed: {str(e)}")
        
        # Check 3: MX record validation (optional but informative)
        print(f"   📧 Checking MX records for {domain}...")
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 10
            resolver.lifetime = 10
            
            mx_records = resolver.resolve(domain, 'MX')
            mx_hosts = [f"{rdata.preference} {str(rdata.exchange).rstrip('.')}" for rdata in mx_records]
            
            if mx_hosts:
                validation_results['checks']['mx_records'] = {
                    'status': True,
                    'mx_hosts': mx_hosts,
                    'message': f"✅ MX records found: {', '.join(mx_hosts)}"
                }
            else:
                validation_results['checks']['mx_records'] = {
                    'status': False,
                    'message': "⚠️  No MX records found"
                }
                validation_results['warnings'].append("No MX records found - email may not work for this domain")
                
        except dns.exception.DNSException as e:
            validation_results['checks']['mx_records'] = {
                'status': False,
                'message': f"ℹ️  MX record lookup failed: {str(e)}"
            }
        
        return validation_results
        
    def send_rpc_request(self, xml_payload: str) -> ET.Element:
        """Send XML-RPC request to Plesk - using your proven approach"""
        response = requests.post(
            self.plesk_url,
            data=xml_payload,
            headers={
                'Content-Type': 'text/xml',
                'KEY': self.api_key
            },
            verify=False  # WARNING: Insecure; use True with proper SSL
        )
        response.raise_for_status()
        return ET.fromstring(response.content)
    
    def get_all_domains(self) -> List[Dict[str, str]]:
        """Get all domains with their site IDs - using working XML from sil5.py"""
        xml_get_domains = '''<?xml version="1.0" encoding="UTF-8"?>
<packet version="1.6.9.1">
  <webspace>
    <get>
      <filter/>
      <dataset>
        <gen_info/>
      </dataset>
    </get>
  </webspace>
</packet>
'''
        
        tree = self.send_rpc_request(xml_get_domains)
        
        domains = []
        for result in tree.findall(".//result"):
            site_id = result.findtext("id")
            domain = result.findtext(".//gen_info/name")
            if domain and site_id:
                domains.append({"name": domain, "id": site_id})
        
        return domains
    
    def _execute_ssh_command(self, command: str, use_sudo: bool = True) -> Tuple[bool, str, str]:
        """Execute command via SSH"""
        if not self.ssh_hostname:
            return False, "", "SSH hostname not configured"
            
        if use_sudo:
            command = f"sudo {command}"
            
        ssh_cmd = ["ssh"]
        
        # Add SSH key if provided
        if self.ssh_key_path:
            ssh_cmd.extend(["-i", self.ssh_key_path])
            
        # Add SSH options
        ssh_cmd.extend([
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10"
        ])
        
        ssh_cmd.extend([f"{self.ssh_username}@{self.ssh_hostname}", command])
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "SSH command timed out"
        except Exception as e:
            return False, "", f"SSH execution error: {e}"
    
    def get_dkim_public_key_via_ssh(self, domain: str, selector: str = "default") -> Optional[str]:
        """Extract DKIM public key using SSH and OpenSSL command"""
        if not self.ssh_hostname:
            return None
            
        print(f"🔑 Extracting DKIM public key for {domain} via SSH...")
        
        # Try the exact command you suggested: sudo openssl rsa -in /etc/domainkeys/<domain>/default -pubout
        key_path = f"/etc/domainkeys/{domain}/{selector}"
        command = f"openssl rsa -in {key_path} -pubout"
        
        success, stdout, stderr = self._execute_ssh_command(command)
        
        if success and stdout.strip():
            # Clean the OpenSSL output to get just the key content
            key_content = self._clean_public_key_for_dns(stdout)
            if key_content:
                print(f"✅ DKIM public key extracted for {domain}")
                return key_content
        
        # Try alternative paths if the standard one doesn't work
        alternative_paths = [
            f"/var/qmail/control/domainkeys/{domain}/{selector}",
            f"/opt/psa/var/modules/domainkeys/{domain}/{selector}",
            f"/usr/local/psa/var/modules/domainkeys/{domain}/{selector}",
            f"/etc/domainkeys/{domain}/default",
            f"/var/qmail/control/domainkeys/{domain}/default"
        ]
        
        for alt_path in alternative_paths:
            command = f"openssl rsa -in {alt_path} -pubout"
            success, stdout, stderr = self._execute_ssh_command(command)
            
            if success and stdout.strip():
                key_content = self._clean_public_key_for_dns(stdout)
                if key_content:
                    print(f"✅ DKIM public key extracted from {alt_path}")
                    return key_content
        
        print(f"❌ Could not extract DKIM public key for {domain}")
        return None
    
    def _clean_public_key_for_dns(self, pem_output: str) -> Optional[str]:
        """Clean OpenSSL PEM output and format for DNS TXT record"""
        if not pem_output:
            return None
        
        # Remove PEM headers/footers and whitespace/newlines
        key_content = pem_output.replace('-----BEGIN PUBLIC KEY-----', '')
        key_content = key_content.replace('-----END PUBLIC KEY-----', '')
        key_content = key_content.replace('-----BEGIN RSA PUBLIC KEY-----', '')
        key_content = key_content.replace('-----END RSA PUBLIC KEY-----', '')
        key_content = re.sub(r'\s+', '', key_content)  # Remove all whitespace and newlines
        
        if len(key_content) > 100 and re.match(r'^[A-Za-z0-9+/=]+$', key_content):
            return key_content
        
        return None
    
    def create_dkim_dns_records(self, domain: str, selector: str = "default") -> Dict[str, any]:
        """Create DKIM DNS records in PowerDNS"""
        if not self.powerdns_manager:
            return {
                'success': False,
                'error': 'PowerDNS manager not configured'
            }
        
        # Get the DKIM public key
        public_key = self.get_dkim_public_key_via_ssh(domain, selector)
        if not public_key:
            return {
                'success': False,
                'error': 'Could not extract DKIM public key'
            }
        
        # Create the DKIM TXT record info
        dkim_record_name = f"{selector}._domainkey.{domain}"
        dkim_record_content = f'"v=DKIM1; k=rsa; p={public_key}"'
        
        dkim_record_info = {
            'domain': domain,
            'selector': selector,
            'name': dkim_record_name,
            'type': 'TXT',
            'content': dkim_record_content,
            'ttl': 3600
        }
        
        print(f"📝 Creating DKIM DNS records for {domain}...")
        
        # Create the main DKIM record
        success1 = self.powerdns_manager.create_dkim_record(dkim_record_info)
        
        # Create the _domainkey policy record
        domainkey_record_name = f"_domainkey.{domain}"
        domainkey_record_content = '"o=-"'
        
        success2 = self.powerdns_manager.create_or_update_record(
            zone_name=f"{domain}.",
            record_name=domainkey_record_name,
            record_type='TXT',
            content=domainkey_record_content,
            ttl=3600
        )
        
        results = {
            'success': success1 and success2,
            'dkim_record': {
                'name': dkim_record_name,
                'content': dkim_record_content,
                'created': success1
            },
            'domainkey_record': {
                'name': domainkey_record_name,
                'content': domainkey_record_content,
                'created': success2
            }
        }
        
        if success1:
            print(f"✅ DKIM TXT record created: {dkim_record_name}")
        else:
            print(f"❌ Failed to create DKIM TXT record for {domain}")
            
        if success2:
            print(f"✅ _domainkey TXT record created: {domainkey_record_name}")
        else:
            print(f"❌ Failed to create _domainkey TXT record for {domain}")
        
        return results
    
    def remove_dkim_dns_records(self, domain: str, selector: str = "default") -> Dict[str, any]:
        """Remove DKIM DNS records from PowerDNS"""
        if not self.powerdns_manager:
            return {
                'success': False,
                'error': 'PowerDNS manager not configured'
            }
        
        print(f"🗑️  Removing DKIM DNS records for {domain}...")
        
        # Remove the DKIM TXT record
        dkim_record_name = f"{selector}._domainkey.{domain}"
        success1 = self.powerdns_manager.delete_record(
            zone_name=f"{domain}.",
            record_name=dkim_record_name,
            record_type='TXT'
        )
        
        # Remove the _domainkey policy record
        domainkey_record_name = f"_domainkey.{domain}"
        success2 = self.powerdns_manager.delete_record(
            zone_name=f"{domain}.",
            record_name=domainkey_record_name,
            record_type='TXT'
        )
        
        results = {
            'success': success1 and success2,
            'dkim_record': {
                'name': dkim_record_name,
                'removed': success1
            },
            'domainkey_record': {
                'name': domainkey_record_name,
                'removed': success2
            }
        }
        
        if success1:
            print(f"✅ DKIM TXT record removed: {dkim_record_name}")
        else:
            print(f"❌ Failed to remove DKIM TXT record for {domain}")
            
        if success2:
            print(f"✅ _domainkey TXT record removed: {domainkey_record_name}")
        else:
            print(f"❌ Failed to remove _domainkey TXT record for {domain}")
        
        return results
    
    def get_site_id(self, domain_name: str) -> Optional[str]:
        """Get site ID for a domain"""
        domains = self.get_all_domains()
        for domain_info in domains:
            if domain_info['name'] == domain_name:
                return domain_info['id']
        return None

    def get_dkim_status(self, domain_name: str) -> Dict[str, str]:
        """Get DKIM status and record for a domain - using valid mail preferences XML"""
        # First get the site ID
        site_id = self.get_site_id(domain_name)
        if not site_id:
            return {
                'domain': domain_name,
                'enabled': False,
                'txt_record': None,
                'status': 'error',
                'error': 'Site ID not found'
            }
        
        xml_get_mail_prefs = f'''<?xml version="1.0" encoding="UTF-8"?>
<packet version="1.6.9.1">
  <mail>
    <get_prefs>
      <filter>
        <site-id>{site_id}</site-id>
      </filter>
    </get_prefs>
  </mail>
</packet>
'''
        
        try:
            tree = self.send_rpc_request(xml_get_mail_prefs)
            
            # Remove the debug output for cleaner operation
            result = tree.find('.//mail/get_prefs/result')
            
            if result is not None:
                status = result.findtext('status')
                if status == 'ok':
                    prefs = result.find('prefs')
                    if prefs is not None:
                        spam_protect_sign = prefs.findtext('spam-protect-sign', 'false')
                        dkim_enabled = spam_protect_sign.lower() == 'true'
                        
                        # If DKIM is enabled and SSH is available, try to get the actual TXT record
                        txt_record = None
                        if dkim_enabled:
                            if self.ssh_hostname:
                                # Try to get the actual DKIM public key via SSH
                                public_key = self.get_dkim_public_key_via_ssh(domain_name)
                                if public_key:
                                    txt_record = f'v=DKIM1; k=rsa; p={public_key}'
                                else:
                                    txt_record = "DKIM enabled (key extraction via SSH failed)"
                            else:
                                txt_record = "DKIM enabled (SSH not configured for key retrieval)"
                        
                        return {
                            'domain': domain_name,
                            'enabled': dkim_enabled,
                            'txt_record': txt_record,
                            'status': 'success'
                        }
                else:
                    error_text = result.findtext('errtext', 'Unknown error')
                    return {
                        'domain': domain_name,
                        'enabled': False,
                        'txt_record': None,
                        'status': 'error',
                        'error': error_text
                    }
            
            return {
                'domain': domain_name,
                'enabled': False,
                'txt_record': None,
                'status': 'error',
                'error': 'No result found'
            }
            
        except Exception as e:
            return {
                'domain': domain_name,
                'enabled': False,
                'txt_record': None,
                'status': 'error',
                'error': str(e)
            }
    
    def enable_dkim(self, domain_name: str, skip_dns_validation: bool = False) -> Dict[str, str]:
        """Enable DKIM for a domain using spam-protect-sign"""
        
        # DNS validation before enabling DKIM (unless skipped)
        if not skip_dns_validation:
            print(f"🔍 Performing DNS validation before enabling DKIM...")
            dns_validation = self.validate_domain_dns(domain_name)
            
            # Display validation results
            for check_name, check_result in dns_validation['checks'].items():
                print(f"   {check_result['message']}")
            
            # Show warnings
            if dns_validation['warnings']:
                print(f"   ⚠️  DNS Validation Warnings:")
                for warning in dns_validation['warnings']:
                    print(f"      - {warning}")
            
            # Show errors and potentially block
            if dns_validation['errors']:
                print(f"   ❌ DNS Validation Errors:")
                for error in dns_validation['errors']:
                    print(f"      - {error}")
            
            # Decide whether to proceed
            critical_issues = dns_validation['errors']
            a_record_missing = not dns_validation['checks'].get('a_record', {}).get('status', False)
            
            if critical_issues or a_record_missing:
                return {
                    'domain': domain_name,
                    'status': 'error',
                    'error': 'DNS validation failed - domain configuration issues detected',
                    'dns_validation': dns_validation
                }
            
            # Check NS records - warn but allow to proceed
            ns_issues = not dns_validation['checks'].get('ns_records', {}).get('valid_ns', True)
            if ns_issues:
                print(f"   ⚠️  Warning: Domain may not be using expected nameservers, but proceeding...")
        
        # First get the site ID
        site_id = self.get_site_id(domain_name)
        if not site_id:
            return {
                'domain': domain_name, 
                'status': 'error', 
                'error': 'Site ID not found'
            }
        
        xml_enable_dkim = f'''<?xml version="1.0" encoding="UTF-8"?>
<packet version="1.6.9.1">
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
</packet>
'''
        
        try:
            result_tree = self.send_rpc_request(xml_enable_dkim)
            result = result_tree.find('.//mail/set_prefs/result')
            
            if result is not None:
                status = result.findtext('status')
                if status == "ok":
                    return {'domain': domain_name, 'status': 'success', 'action': 'enabled'}
                else:
                    error_text = result.findtext('errtext', 'Unknown error')
                    return {'domain': domain_name, 'status': 'error', 'error': error_text}
            
            return {'domain': domain_name, 'status': 'error', 'error': 'No result found'}
                
        except Exception as e:
            return {'domain': domain_name, 'status': 'error', 'error': str(e)}
    
    def disable_dkim(self, domain_name: str) -> Dict[str, str]:
        """Disable DKIM for a domain using spam-protect-sign"""
        # First get the site ID
        site_id = self.get_site_id(domain_name)
        if not site_id:
            return {
                'domain': domain_name, 
                'status': 'error', 
                'error': 'Site ID not found'
            }
        
        xml_disable_dkim = f'''<?xml version="1.0" encoding="UTF-8"?>
<packet version="1.6.9.1">
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
</packet>
'''
        
        try:
            result_tree = self.send_rpc_request(xml_disable_dkim)
            result = result_tree.find('.//mail/set_prefs/result')
            
            if result is not None:
                status = result.findtext('status')
                if status == "ok":
                    # Also remove DNS records if PowerDNS is configured
                    if self.powerdns_manager:
                        print(f"🗑️  Removing DNS records from PowerDNS...")
                        dns_removal_result = self.remove_dkim_dns_records(domain_name)
                        
                        if dns_removal_result['success']:
                            print(f"✅ DNS records removed successfully!")
                        else:
                            print(f"⚠️  DNS record removal failed: {dns_removal_result.get('error', 'Unknown error')}")
                    
                    return {'domain': domain_name, 'status': 'success', 'action': 'disabled'}
                else:
                    error_text = result.findtext('errtext', 'Unknown error')
                    return {'domain': domain_name, 'status': 'error', 'error': error_text}
            
            return {'domain': domain_name, 'status': 'error', 'error': 'No result found'}
                
        except Exception as e:
            return {'domain': domain_name, 'status': 'error', 'error': str(e)}
    
    def get_domain_report(self) -> List[Dict]:
        """Get complete DKIM report for all domains"""
        print("🔍 Getting all domains...")
        domains = self.get_all_domains()
        print(f"✅ Found {len(domains)} domains")
        
        report = []
        for domain_info in domains:
            domain_name = domain_info['name']
            site_id = domain_info['id']
            
            print(f"   Checking DKIM for {domain_name}...")
            dkim_status = self.get_dkim_status(domain_name)
            
            report.append({
                'domain': domain_name,
                'site_id': site_id,
                'dkim_enabled': dkim_status['enabled'],
                'dkim_record': dkim_status['txt_record'],
                'status': dkim_status['status'],
                'error': dkim_status.get('error')
            })
        
        return report


def create_multi_server_manager() -> Dict[str, SimplePleskDKIM]:
    """Create managers for all servers from environment config"""
    load_dotenv()
    
    # Get hostnames list
    hostnames_str = os.getenv('PLESK_HOSTNAMES', '')
    if not hostnames_str:
        raise ValueError("PLESK_HOSTNAMES not found in environment")
    
    hostnames = [h.strip() for h in hostnames_str.split(',')]
    
    # SSH configuration (optional)
    ssh_username = os.getenv('PLESK_SSH_USERNAME', 'admin')
    ssh_key_path = os.getenv('PLESK_SSH_KEY_PATH')  # Optional
    
    # PowerDNS configuration (optional)
    powerdns_url = os.getenv('POWERDNS_SERVER_URL')
    powerdns_key = os.getenv('POWERDNS_API_KEY')
    powerdns_manager = None
    
    if powerdns_url and powerdns_key:
        try:
            # For PowerDNS via SSH, we need to use localhost URL and SSH to cora.avant.nl
            powerdns_ssh_host = "cora.avant.nl"  # The server where PowerDNS API is running
            local_powerdns_url = "http://localhost:8081"  # Local PowerDNS URL on the remote server
            
            powerdns_manager = PowerDNSManager(
                server_url=local_powerdns_url,
                api_key=powerdns_key,
                ssh_hostname=powerdns_ssh_host,
                ssh_username=ssh_username,
                ssh_key_path=ssh_key_path
            )
            print(f"✅ PowerDNS SSH integration enabled: {powerdns_ssh_host} -> {local_powerdns_url}")
        except Exception as e:
            print(f"⚠️  PowerDNS configuration failed: {e}")
            powerdns_manager = None
    else:
        print("⚠️  PowerDNS not configured (POWERDNS_SERVER_URL and POWERDNS_API_KEY required)")
    
    managers = {}
    for hostname in hostnames:
        # Get API key for this server
        api_key_var = f"{hostname.split('.')[0].upper()}_XML_API_KEY"
        api_key = os.getenv(api_key_var)
        
        if not api_key:
            print(f"⚠️  Warning: {api_key_var} not found, skipping {hostname}")
            continue
        
        plesk_url = f'https://{hostname}:8443/enterprise/control/agent.php'
        
        # Create manager with SSH support for DKIM key extraction and PowerDNS integration
        managers[hostname] = SimplePleskDKIM(
            plesk_url=plesk_url, 
            api_key=api_key,
            ssh_hostname=hostname,  # Use same hostname for SSH
            ssh_username=ssh_username,
            ssh_key_path=ssh_key_path,
            powerdns_manager=powerdns_manager
        )
    
    return managers


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python simple_dkim.py precheck           # Run system prechecks")
        print("  python simple_dkim.py validate-dns <domain> # Validate domain DNS configuration")
        print("  python simple_dkim.py report              # Get DKIM status for all domains")
        print("  python simple_dkim.py enable <domain>     # Enable DKIM for a domain")
        print("  python simple_dkim.py enable <domain> --skip-dns # Enable DKIM without DNS validation")
        print("  python simple_dkim.py disable <domain>    # Disable DKIM for a domain")
        print("  python simple_dkim.py status <domain>     # Get DKIM status for specific domain")
        print("  python simple_dkim.py create-dns <domain> # Create DNS records for DKIM-enabled domain")
        print("  python simple_dkim.py remove-dns <domain> # Remove DNS records for a domain")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        managers = create_multi_server_manager()
        
        if command == "precheck":
            # Run comprehensive prechecks across all servers
            print("🚀 Running System Prechecks")
            print("=" * 60)
            
            all_checks_passed = True
            all_warnings = []
            all_errors = []
            
            for hostname, manager in managers.items():
                print(f"\n📊 Server: {hostname}")
                print("-" * 40)
                
                try:
                    results = manager.run_prechecks()
                    
                    # Display individual check results
                    for check_name, check_result in results['checks'].items():
                        print(f"   {check_result['message']}")
                    
                    # Collect overall status
                    if not results['overall_status']:
                        all_checks_passed = False
                    
                    all_warnings.extend(results['warnings'])
                    all_errors.extend(results['errors'])
                    
                except Exception as e:
                    print(f"❌ Error running prechecks for {hostname}: {e}")
                    all_checks_passed = False
                    all_errors.append(f"Precheck failed for {hostname}: {e}")
            
            # Summary
            print(f"\n🏁 Precheck Summary")
            print("=" * 40)
            
            if all_checks_passed:
                print("✅ All critical checks passed!")
            else:
                print("❌ Some critical checks failed!")
            
            if all_warnings:
                print(f"\n⚠️  Warnings ({len(all_warnings)}):")
                for warning in set(all_warnings):  # Remove duplicates
                    print(f"   - {warning}")
            
            if all_errors:
                print(f"\n❌ Errors ({len(all_errors)}):")
                for error in set(all_errors):  # Remove duplicates
                    print(f"   - {error}")
            
            if all_checks_passed:
                print(f"\n🎉 System is ready for DKIM automation!")
            else:
                print(f"\n🔧 Please fix the errors above before using DKIM automation.")
                sys.exit(1)
        
        elif command == "validate-dns" and len(sys.argv) == 3:
            domain = sys.argv[2]
            print(f"🔍 Validating DNS configuration for {domain}")
            
            for hostname, manager in managers.items():
                try:
                    # Check if domain exists on this server first
                    domains = manager.get_all_domains()
                    domain_exists = any(d['name'] == domain for d in domains)
                    
                    if domain_exists:
                        print(f"\n📊 Server: {hostname}")
                        validation_results = manager.validate_domain_dns(domain)
                        
                        # Display validation results
                        for check_name, check_result in validation_results['checks'].items():
                            print(f"   {check_result['message']}")
                        
                        # Show warnings
                        if validation_results['warnings']:
                            print(f"\n⚠️  DNS Validation Warnings:")
                            for warning in validation_results['warnings']:
                                print(f"   - {warning}")
                        
                        # Show errors
                        if validation_results['errors']:
                            print(f"\n❌ DNS Validation Errors:")
                            for error in validation_results['errors']:
                                print(f"   - {error}")
                        
                        # Overall result
                        if validation_results['valid']:
                            print(f"\n✅ DNS configuration is valid for DKIM")
                        else:
                            print(f"\n❌ DNS configuration has issues that need to be resolved")
                        
                        break
                except Exception as e:
                    continue
            else:
                print(f"❌ Domain {domain} not found on any server")
        
        elif command == "report":
            # Full report across all servers
            print("🚀 Starting DKIM Report for All Servers")
            print("=" * 60)
            
            for hostname, manager in managers.items():
                print(f"\n📊 Server: {hostname}")
                print("-" * 40)
                
                try:
                    report = manager.get_domain_report()
                    
                    # Summary stats
                    total = len(report)
                    enabled = len([r for r in report if r['dkim_enabled']])
                    disabled = total - enabled
                    
                    print(f"\n📈 Summary for {hostname}:")
                    print(f"   Total domains: {total}")
                    print(f"   DKIM enabled: {enabled}")
                    print(f"   DKIM disabled: {disabled}")
                    
                    # Show disabled domains (candidates for enabling)
                    disabled_domains = [r for r in report if not r['dkim_enabled']]
                    if disabled_domains:
                        print(f"\n📝 Domains without DKIM ({len(disabled_domains)}):")
                        for domain_info in disabled_domains[:10]:  # Show first 10
                            print(f"   - {domain_info['domain']}")
                        if len(disabled_domains) > 10:
                            print(f"   ... and {len(disabled_domains) - 10} more")
                    
                except Exception as e:
                    print(f"❌ Error processing {hostname}: {e}")
        
        elif command == "status" and len(sys.argv) == 3:
            domain = sys.argv[2]
            print(f"🔍 Checking DKIM status for {domain}")
            
            for hostname, manager in managers.items():
                try:
                    # Check if domain exists on this server first
                    domains = manager.get_all_domains()
                    domain_exists = any(d['name'] == domain for d in domains)
                    
                    if domain_exists:
                        print(f"\n📊 Server: {hostname}")
                        status = manager.get_dkim_status(domain)
                        
                        if status['status'] == 'success':
                            enabled_text = "✅ ENABLED" if status['enabled'] else "❌ DISABLED"
                            print(f"   DKIM Status: {enabled_text}")
                            
                            if status['txt_record']:
                                print(f"   TXT Record: {status['txt_record'][:100]}...")
                            else:
                                print(f"   TXT Record: Not available")
                        else:
                            print(f"   Error: {status['error']}")
                        break
                except Exception as e:
                    continue
            else:
                print(f"❌ Domain {domain} not found on any server")
        
        elif command == "enable" and len(sys.argv) >= 3:
            domain = sys.argv[2]
            skip_dns_validation = len(sys.argv) > 3 and sys.argv[3] == "--skip-dns"
            
            if skip_dns_validation:
                print(f"🔐 Enabling DKIM for {domain} (skipping DNS validation)")
            else:
                print(f"🔐 Enabling DKIM for {domain}")
            
            for hostname, manager in managers.items():
                try:
                    # Check if domain exists on this server first
                    domains = manager.get_all_domains()
                    domain_exists = any(d['name'] == domain for d in domains)
                    
                    if domain_exists:
                        print(f"\n📊 Server: {hostname}")
                        result = manager.enable_dkim(domain, skip_dns_validation=skip_dns_validation)
                        
                        if result['status'] == 'success':
                            print(f"✅ DKIM enabled for {domain}")
                            
                            # Get the DKIM status and TXT record
                            status = manager.get_dkim_status(domain)
                            if status['txt_record']:
                                print(f"📝 TXT Record: {status['txt_record']}")
                            
                            # Automatically create DNS records if PowerDNS is configured
                            if manager.powerdns_manager:
                                print(f"\n🌐 Creating DNS records in PowerDNS...")
                                dns_result = manager.create_dkim_dns_records(domain)
                                
                                if dns_result['success']:
                                    print(f"✅ DNS records created successfully!")
                                    print(f"   DKIM Record: {dns_result['dkim_record']['name']}")
                                    print(f"   _domainkey Record: {dns_result['domainkey_record']['name']}")
                                else:
                                    print(f"❌ DNS record creation failed: {dns_result.get('error', 'Unknown error')}")
                            else:
                                print(f"ℹ️  PowerDNS not configured - manual DNS record creation required")
                        else:
                            print(f"❌ Error: {result['error']}")
                            if 'dns_validation' in result:
                                print(f"💡 Tip: Use 'python simple_dkim.py validate-dns {domain}' for detailed DNS information")
                                print(f"💡 Or use 'python simple_dkim.py enable {domain} --skip-dns' to bypass validation")
                        break
                except Exception as e:
                    continue
            else:
                print(f"❌ Domain {domain} not found on any server")
        
        elif command == "disable" and len(sys.argv) == 3:
            domain = sys.argv[2]
            print(f"🔓 Disabling DKIM for {domain}")
            
            for hostname, manager in managers.items():
                try:
                    # Check if domain exists on this server first
                    domains = manager.get_all_domains()
                    domain_exists = any(d['name'] == domain for d in domains)
                    
                    if domain_exists:
                        print(f"\n📊 Server: {hostname}")
                        result = manager.disable_dkim(domain)
                        
                        if result['status'] == 'success':
                            print(f"✅ DKIM disabled for {domain}")
                        else:
                            print(f"❌ Error: {result['error']}")
                        break
                except Exception as e:
                    continue
            else:
                print(f"❌ Domain {domain} not found on any server")
        
        elif command == "create-dns" and len(sys.argv) == 3:
            domain = sys.argv[2]
            print(f"🌐 Creating DNS records for {domain}")
            
            for hostname, manager in managers.items():
                try:
                    # Check if domain exists on this server first
                    domains = manager.get_all_domains()
                    domain_exists = any(d['name'] == domain for d in domains)
                    
                    if domain_exists:
                        print(f"\n📊 Server: {hostname}")
                        
                        # Check if DKIM is enabled first
                        status = manager.get_dkim_status(domain)
                        if not status['enabled']:
                            print(f"❌ DKIM is not enabled for {domain}. Enable it first with: python simple_dkim.py enable {domain}")
                            break
                        
                        # Create DNS records
                        if manager.powerdns_manager:
                            dns_result = manager.create_dkim_dns_records(domain)
                            
                            if dns_result['success']:
                                print(f"✅ DNS records created successfully!")
                                print(f"   DKIM Record: {dns_result['dkim_record']['name']}")
                                print(f"   Content: {dns_result['dkim_record']['content'][:80]}...")
                                print(f"   _domainkey Record: {dns_result['domainkey_record']['name']}")
                                print(f"   Content: {dns_result['domainkey_record']['content']}")
                            else:
                                print(f"❌ DNS record creation failed: {dns_result.get('error', 'Unknown error')}")
                        else:
                            print(f"❌ PowerDNS not configured. Set POWERDNS_SERVER_URL and POWERDNS_API_KEY in your environment.")
                        break
                except Exception as e:
                    continue
            else:
                print(f"❌ Domain {domain} not found on any server")
        
        elif command == "remove-dns" and len(sys.argv) == 3:
            domain = sys.argv[2]
            print(f"🗑️  Removing DNS records for {domain}")
            
            for hostname, manager in managers.items():
                try:
                    # Check if domain exists on this server first
                    domains = manager.get_all_domains()
                    domain_exists = any(d['name'] == domain for d in domains)
                    
                    if domain_exists:
                        print(f"\n📊 Server: {hostname}")
                        
                        # Remove DNS records
                        if manager.powerdns_manager:
                            dns_result = manager.remove_dkim_dns_records(domain)
                            
                            if dns_result['success']:
                                print(f"✅ DNS records removed successfully!")
                                print(f"   DKIM Record: {dns_result['dkim_record']['name']} - {'Removed' if dns_result['dkim_record']['removed'] else 'Failed'}")
                                print(f"   _domainkey Record: {dns_result['domainkey_record']['name']} - {'Removed' if dns_result['domainkey_record']['removed'] else 'Failed'}")
                            else:
                                print(f"❌ DNS record removal failed: {dns_result.get('error', 'Unknown error')}")
                        else:
                            print(f"❌ PowerDNS not configured. Set POWERDNS_SERVER_URL and POWERDNS_API_KEY in your environment.")
                        break
                except Exception as e:
                    continue
            else:
                print(f"❌ Domain {domain} not found on any server")
        
        else:
            print("❌ Invalid command or missing arguments")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
