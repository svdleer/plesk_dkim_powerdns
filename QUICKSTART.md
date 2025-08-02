# DKIM Automation - Quick Start Guide

## What This Does

This project automates the process of:
1. Enabling DKIM (email authentication) on your Plesk server
2. Automatically creating the required DNS records in PowerDNS
3. Managing and verifying DKIM configurations

## Quick Setup

1. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your actual API details
   ```

2. **Install Dependencies** (already done)
   ```bash
   # Virtual environment and packages are already set up
   ```

3. **Test Connection**
   ```bash
   # Basic connectivity test
   python test_connection.py
   
   # Explore XML API structure for your Plesk version
   python plesk_xml_explorer.py
   
   # Test full setup
   python example.py
   ```

## Usage Examples

### Enhanced XML API Version (Recommended)

#### Enable DKIM for a domain
```bash
# Basic enablement (1024-bit key, default selector)
python dkim_automation_enhanced.py enable --domain example.com

# With custom settings
python dkim_automation_enhanced.py enable --domain example.com --key-size 2048 --selector mail
```

#### Disable DKIM for a domain
```bash
python dkim_automation_enhanced.py disable --domain example.com
```

#### List all domains and their DKIM status
```bash
python dkim_automation_enhanced.py list
```

#### Verify DKIM configuration
```bash
python dkim_automation_enhanced.py verify --domain example.com
```

#### Get DNS record for manual setup
```bash
python dkim_automation_enhanced.py record --domain example.com
```

### Plesk-Only CLI Utility

#### Use Plesk CLI for Plesk-only operations
```bash
# List domains and DKIM status
python plesk_cli.py list

# Enable DKIM (Plesk only)
python plesk_cli.py enable --domain example.com --key-size 2048

# Get DNS record details
python plesk_cli.py record --domain example.com

# Verify Plesk configuration
python plesk_cli.py verify --domain example.com
```

## What You Need

### Plesk Server
- Plesk Panel with REST API access
- API key with permissions for:
  - Mail settings management
  - Domain management

### PowerDNS Server
- PowerDNS with REST API enabled
- API key configured in pdns.conf

## Environment Variables Required

```env
# Plesk Server
PLESK_SERVER_URL=https://your-plesk-server.com:8443

# Plesk Authentication - Choose ONE method:
# Method 1: Username/Password (RECOMMENDED for XML API)
PLESK_USERNAME=admin
PLESK_PASSWORD=your-admin-password

# Method 2: API Key (for REST API)
PLESK_API_KEY=your-plesk-api-key

# PowerDNS Server (optional for some operations)
POWERDNS_SERVER_URL=http://your-powerdns-server:8081
POWERDNS_API_KEY=your-powerdns-api-key
```

## What Happens When You Enable DKIM

1. **Plesk Operations:**
   - Generates DKIM key pair for the domain
   - Configures mail server to sign outgoing emails
   - Provides the public key for DNS publication

2. **PowerDNS Operations:**
   - Creates a TXT record at `selector._domainkey.domain.com`
   - Record contains the DKIM public key
   - Sets appropriate TTL for quick propagation

3. **Result:**
   - Emails from your domain will be DKIM-signed
   - Recipients can verify email authenticity
   - Improved email deliverability

## Security Notes

- Keep your API keys secure
- Use HTTPS for Plesk connections
- Restrict API access to specific IPs if possible
- Test in a development environment first

## Troubleshooting

If you encounter issues:

1. **Check API connectivity:**
   ```bash
   python plesk_diagnostics.py  # Run diagnostics
   python example.py            # Test basic connection
   ```

2. **Authentication Issues:**
   - **XML API (Recommended)**: Use `PLESK_USERNAME` and `PLESK_PASSWORD`
   - **REST API**: Use `PLESK_API_KEY` 
   - Verify credentials by logging into Plesk Panel manually

3. **Connection Refused Error:**
   - Check if Plesk server is accessible: `curl -k https://your-server:8443`
   - Verify firewall allows connections on port 8443
   - Ensure XML API is enabled in Plesk: Tools & Settings → API Access

4. **API Permissions:**
   - Ensure the user has Administrator privileges
   - Check API access is allowed for your IP address
   - Verify XML API is not restricted to specific IPs

5. **PowerDNS Issues:**
   - Check DNS zone exists in PowerDNS for your domain
   - Verify PowerDNS API is enabled and accessible
   - Test PowerDNS API: `curl -H "X-API-Key: your-key" http://powerdns-server:8081/api/v1/servers`

6. **SSL Certificate Issues:**
   - Scripts disable SSL verification by default for development
   - You'll see warnings like "Unverified HTTPS request" - this is normal
   - For production, configure proper SSL certificates
   - Or modify `self.session.verify = True` in the scripts

7. **XML API Structure Issues:**
   - Different Plesk versions use different XML structures
   - Run `python plesk_xml_explorer.py` to discover the correct structure
   - The explorer will test different methods and show what works

## File Structure

### Main Scripts
- `dkim_automation_enhanced.py` - **Main automation script (XML API)** 
- `plesk_cli.py` - **Plesk-only CLI utility (XML API)**
- `plesk_xml_api.py` - Plesk XML API client
- `powerdns_manager.py` - PowerDNS REST API operations

### Legacy/Alternative
- `dkim_automation.py` - Original automation script (REST API)
- `plesk_dkim.py` - Plesk REST API operations (limited DKIM support)

### Configuration & Examples
- `example.py` - Test connectivity and examples
- `plesk_xml_explorer.py` - **Discover correct XML API structure**
- `test_connection.py` - Simple connection test
- `plesk_diagnostics.py` - Full diagnostics tool
- `requirements.txt` - Python dependencies
- `.env.example` - Environment template
- `README.md` - Full documentation

Ready to get started? Edit your `.env` file and run `python example.py`!
