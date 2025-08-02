# SSL Warnings Notice

## About the "Unverified HTTPS request" Warning

You may see warnings like:
```
InsecureRequestWarning: Unverified HTTPS request is being made to host 'aron.avant.nl'. 
Adding certificate verification is strongly advised.
```

**This is normal and expected** for this development setup.

## Why This Happens

- Plesk servers often use self-signed SSL certificates
- The scripts disable SSL verification (`verify=False`) to work with these certificates
- This allows the connection to work without SSL certificate validation

## For Production Use

If you want to enable SSL verification:

1. **Install proper SSL certificates** on your Plesk server
2. **Update the scripts** to enable verification:
   ```python
   self.session.verify = True  # Instead of False
   ```

## Security Note

- For internal/development use: SSL warnings are acceptable
- For production/public use: Consider proper SSL certificates
- The connection is still encrypted, just not certificate-verified

## Disable Warnings (Optional)

The scripts already include code to suppress these warnings:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

This is included in:
- `plesk_xml_api.py`
- `plesk_xml_explorer.py`
- All diagnostic tools
