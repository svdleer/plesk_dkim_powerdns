#!/usr/bin/env python3
"""
Setup script for DKIM automation project
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description=""):
    """Run a shell command and handle errors"""
    if description:
        print(f"📦 {description}...")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        return False


def main():
    """Setup the project environment"""
    print("🚀 Setting up DKIM Automation Project")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected")
    
    # Create .env file if it doesn't exist
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from template...")
        env_file.write_text(env_example.read_text())
        print("   ✅ .env file created")
        print("   ⚠️  Please edit .env file with your actual API credentials")
    elif env_file.exists():
        print("📝 .env file already exists")
    else:
        print("⚠️  No .env.example file found")
    
    # Make scripts executable
    scripts = ['dkim_automation.py', 'plesk_dkim.py', 'powerdns_manager.py', 'example.py']
    for script in scripts:
        if os.path.exists(script):
            os.chmod(script, 0o755)
            print(f"   Made {script} executable")
    
    print("\n🎉 Setup completed!")
    print("\nNext steps:")
    print("1. Edit the .env file with your API credentials:")
    print("   nano .env")
    print("\n2. Test the connection:")
    print("   python example.py")
    print("\n3. Enable DKIM for a domain:")
    print("   python dkim_automation.py enable --domain yourdomain.com")
    print("\n4. See all available commands:")
    print("   python dkim_automation.py --help")


if __name__ == "__main__":
    main()
