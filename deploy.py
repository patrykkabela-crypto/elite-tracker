import sys
import os
import aiohttp
import asyncio
import ftplib
from pathlib import Path

"""
Automated Deployer for WispByte Hosting / Pterodactyl Panel
-----------------------------------------------------------
Usage:
  1. Fill in your SFTP details below (found on WispByte -> Settings -> SFTP Details)
  2. Run `python deploy.py` or double-click `deploy.bat`
"""

# WispByte SFTP Configuration (Find in WispByte -> Server -> Settings)
SFTP_HOST = "sftp.wispbyte.com"  # Replace with WispByte SFTP Server Address
SFTP_PORT = 2022                 # WispByte SFTP Port
SFTP_USER = "your_sftp_username" # Replace with your WispByte SFTP Username
SFTP_PASS = "your_wispbyte_password" # Replace with your WispByte Password

# Files to upload
FILES_TO_UPLOAD = [
    "config.py",
    "cops_api.py",
    "cops_tracker.py",
    "bot.py",
    "main.py",
    "requirements.txt",
    ".env"
]

def deploy_via_sftp():
    try:
        import paramiko
    except ImportError:
        print("Installing paramiko for automated SFTP transfer...")
        os.system("pip install paramiko")
        import paramiko

    print(f"🚀 Connecting to WispByte SFTP server {SFTP_HOST}:{SFTP_PORT}...")
    
    transport = paramiko.Transport((SFTP_HOST, int(SFTP_PORT)))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    print("✅ Connected! Uploading files to WispByte server...")
    
    for filename in FILES_TO_UPLOAD:
        if os.path.exists(filename):
            print(f" 📤 Uploading {filename}...")
            sftp.put(filename, filename)
        else:
            print(f" ⚠️ Warning: {filename} not found locally.")

    sftp.close()
    transport.close()
    print("🎉 All files uploaded automatically to WispByte!")

if __name__ == "__main__":
    if SFTP_USER == "your_sftp_username":
        print("=============================================================")
        print("⚠️ AUTOMATED DEPLOYMENT SETUP REQUIRED")
        print("=============================================================")
        print("To auto-upload files to WispByte, open deploy.py and set:")
        print("  - SFTP_HOST (e.g. sftp.wispbyte.com)")
        print("  - SFTP_USER (Found in WispByte -> Settings -> SFTP Details)")
        print("  - SFTP_PASS (Your WispByte Account Password)")
        print("=============================================================")
    else:
        deploy_via_sftp()
