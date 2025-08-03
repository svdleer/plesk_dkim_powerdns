# Plesk DKIM PowerDNS Automation

This project provides Python scripts to automate DKIM (DomainKeys Identified Mail) enablement in Plesk and DNS record management in PowerDNS using their respective REST APIs and SSH access.

## Features

- ✅ Enable/disable DKIM for domains in Plesk (API + SSH)
- ✅ Automatically create/update DKIM DNS records in PowerDNS
- ✅ **NEW**: SSH-based DKIM key extraction with sudo support
- ✅ **NEW**: Multiple fallback methods for reliable key retrieval  
- ✅ **NEW**: Comprehensive status checking across all systems
- ✅ Verify DKIM configuration consistency
- ✅ List DKIM status for all domains
- ✅ Command-line interface for easy automation
- ✅ Environment-based configuration

## New SSH Features

🆕 **Enhanced Access**: Direct SSH access to Plesk servers  
🆕 **Sudo Support**: Execute privileged commands for file system access  
🆕 **Key Extraction**: Multiple methods to retrieve DKIM keys  
🆝 **Fallback Logic**: Tries API first, falls back to SSH  
🆕 **Comprehensive Testing**: Test all connection methods  

## Quick Start

**For enhanced SSH functionality, see: [SSH_QUICKSTART.md](SSH_QUICKSTART.md)**

## Prerequisites

- Python 3.7+
- Plesk server with REST API access OR SSH access
- PowerDNS server with REST API enabled (optional)
- Valid credentials for your chosen access method

## Installation

1. Clone or download this repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment template and configure your settings:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` file with your actual API credentials:
   ```bash
   nano .env
   ```

## Configuration

Edit the `.env` file with your server details:

```env
# Plesk Configuration
PLESK_SERVER_URL=https://your-plesk-server.com:8443
PLESK_API_KEY=your-plesk-api-key

# PowerDNS Configuration
POWERDNS_SERVER_URL=http://your-powerdns-server:8081
POWERDNS_API_KEY=your-powerdns-api-key

# Optional: Default zone for PowerDNS operations
DEFAULT_ZONE=example.com
```

### Getting API Keys

#### Plesk API Key
1. Log in to Plesk Panel
2. Go to **Tools & Settings** > **API Keys**
3. Click **Create Key**
4. Set appropriate permissions (Mail settings, DNS management)
5. Copy the generated key

#### PowerDNS API Key
1. Configure PowerDNS API in `pdns.conf`:
   ```
   api=yes
   api-key=your-secret-api-key
   webserver=yes
   webserver-address=0.0.0.0
   webserver-port=8081
   ```
2. Restart PowerDNS service
3. Use the configured API key

## Usage

### Command Line Interface

The main automation script provides a command-line interface:

```bash
python dkim_automation.py <action> [options]
```

#### Available Actions

**Enable DKIM for a domain:**
```bash
python dkim_automation.py enable --domain example.com --selector default
```

**Disable DKIM for a domain:**
```bash
python dkim_automation.py disable --domain example.com
```

**List DKIM status for all domains:**
```bash
python dkim_automation.py list
```

**Verify DKIM configuration:**
```bash
python dkim_automation.py verify --domain example.com
```

#### Options

- `--domain, -d`: Specify the domain name
- `--selector, -s`: DKIM selector (default: "default")
- `--server-id`: PowerDNS server ID (default: "localhost")

### Python API Usage

You can also use the classes directly in your Python code:

```python
from dotenv import load_dotenv
import os
from plesk_dkim import PleskDKIMManager
from powerdns_manager import PowerDNSManager
from dkim_automation import DKIMAutomation

# Load environment variables
load_dotenv()

# Initialize managers
plesk = PleskDKIMManager(
    os.getenv('PLESK_SERVER_URL'),
    os.getenv('PLESK_API_KEY')
)

powerdns = PowerDNSManager(
    os.getenv('POWERDNS_SERVER_URL'),
    os.getenv('POWERDNS_API_KEY')
)

# Or use the automation class
automation = DKIMAutomation(
    os.getenv('PLESK_SERVER_URL'),
    os.getenv('PLESK_API_KEY'),
    os.getenv('POWERDNS_SERVER_URL'),
    os.getenv('POWERDNS_API_KEY')
)

# Enable DKIM for a domain
automation.enable_dkim_full_workflow('example.com')
```

## Scripts Overview

### `plesk_dkim.py`
Handles Plesk DKIM operations:
- Enable/disable DKIM for domains
- Retrieve DKIM public keys and DNS records
- Format DNS records for PowerDNS consumption

### `powerdns_manager.py`
Manages PowerDNS operations:
- Create/update/delete DNS records
- Query existing records
- Zone management

### `dkim_automation.py`
Main automation script that orchestrates:
- Complete DKIM enablement workflow
- DKIM disablement and cleanup
- Status reporting and verification
- Command-line interface

## Workflow

When enabling DKIM for a domain, the automation performs these steps:

1. **Enable DKIM in Plesk**
   - Generates DKIM key pair
   - Configures mail server settings

2. **Retrieve DKIM Record**
   - Gets the public key from Plesk
   - Formats as proper DNS TXT record

3. **Create DNS Record**
   - Adds TXT record to PowerDNS
   - Format: `selector._domainkey.domain.com`

## Example Output

```bash
$ python dkim_automation.py enable --domain example.com

Starting DKIM enablement for domain: example.com
Step 1: Enabling DKIM in Plesk...
DKIM enabled for example.com with selector 'default'
Step 2: Retrieving DKIM record from Plesk...
DKIM record details:
  Name: default._domainkey.example.com
  Type: TXT
  Content: "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC..."
  TTL: 300
Step 3: Creating DKIM record in PowerDNS...
Successfully created/updated TXT record for default._domainkey.example.com.
✅ DKIM successfully enabled for example.com
   Selector: default
   DNS record created: default._domainkey.example.com
```

## Error Handling

The scripts include comprehensive error handling:
- API connection errors
- Authentication failures
- Invalid domain names
- Missing DNS zones
- Network timeouts

## Security Notes

- Store API keys securely
- Use HTTPS for Plesk connections
- Restrict API key permissions to minimum required
- Consider firewall rules for API access
- The Plesk script disables SSL verification by default (adjust for production)

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors (Plesk)**
   - Modify `self.session.verify = False` in `plesk_dkim.py`
   - Or properly configure SSL certificates

2. **PowerDNS API Not Responding**
   - Verify API is enabled in `pdns.conf`
   - Check firewall settings
   - Confirm API key configuration

3. **Zone Not Found in PowerDNS**
   - Ensure the domain zone exists in PowerDNS
   - Check zone name format (with/without trailing dot)

4. **Permission Denied**
   - Verify API key permissions
   - Check user access levels in Plesk

### Debug Mode

For debugging, you can modify the scripts to enable verbose output:
- Add `import logging; logging.basicConfig(level=logging.DEBUG)`
- Use `response.text` to see raw API responses

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this automation tool.

## License

This project is provided as-is for educational and automation purposes. Use at your own risk and ensure you have proper backups before running in production environments.
