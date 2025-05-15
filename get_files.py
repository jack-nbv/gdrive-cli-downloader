'''
Specialized script to analyze and list files in Google Drive folders
'''

import sys
import requests
import re
import json
import random
import time

def get_folder_contents_direct(folder_id):
    """
    Use multiple techniques to try to get folder contents
    """
    print(f"Attempting to access folder: {folder_id}")
    
    # Method 1: Direct web folder access
    url = f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing"
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Upgrade-Insecure-Requests": "1",
    }
    
    response = requests.get(url, headers=headers)
    print(f"Response status: {response.status_code}")
    print(f"Content length: {len(response.text)} bytes")
    
    # Save the HTML for analysis (useful for debugging)
    with open("folder_page.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved HTML response to folder_page.html for analysis")
    
    # Method 2: Try to extract folder info from Javascript data
    print("\nAnalyzing page for folder information...")
    
    # Look for file IDs and names
    file_ids = re.findall(r'data-id=["\']([a-zA-Z0-9_-]{28,})["\']', response.text)
    file_names = re.findall(r'aria-label=["\']([^"\']+)["\'].*?data-id', response.text)
    
    # Look for metadata blocks
    metadata_blocks = re.findall(r'metadata":\s*(\[.*?\])\s*}[,)]', response.text)
    
    if file_ids:
        print(f"Found {len(file_ids)} potential file IDs on the page:")
        for i, file_id in enumerate(file_ids[:10]):  # Show first 10
            print(f"- {file_id}")
        if len(file_ids) > 10:
            print(f"... and {len(file_ids) - 10} more")
    else:
        print("No file IDs found on the page")
    
    if file_names:
        print(f"\nFound {len(file_names)} potential file names on the page:")
        for i, name in enumerate(file_names[:10]):  # Show first 10
            print(f"- {name}")
        if len(file_names) > 10:
            print(f"... and {len(file_names) - 10} more")
    else:
        print("No file names found on the page")
    
    # Method 3: Try to extract file info from raw metadata
    data_blocks = re.findall(r'"(\[[a-zA-Z0-9_-]{28,}",.*?)"', response.text)
    if data_blocks:
        print(f"\nFound {len(data_blocks)} data blocks that might contain file info:")
        for i, block in enumerate(data_blocks[:5]):  # Show first 5
            print(f"- {block[:100]}...")
        if len(data_blocks) > 5:
            print(f"... and {len(data_blocks) - 5} more")
    else:
        print("\nNo data blocks found that might contain file info")
    
    # Method 4: Look for direct file paths or references
    file_refs = re.findall(r'href=["\']\/(?:file|open)\?id=([a-zA-Z0-9_-]{28,})["\']', response.text)
    if file_refs:
        print(f"\nFound {len(file_refs)} direct file references:")
        for i, ref in enumerate(file_refs[:10]):  # Show first 10
            print(f"- {ref}")
        if len(file_refs) > 10:
            print(f"... and {len(file_refs) - 10} more")
    else:
        print("\nNo direct file references found")
    
    # Method 5: Try an alternative API approach with iframe
    print("\nAttempting alternative iframe approach...")
    iframe_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    iframe_response = requests.get(iframe_url, headers=headers)
    
    print(f"Iframe response status: {iframe_response.status_code}")
    print(f"Iframe content length: {len(iframe_response.text)} bytes")
    
    # Save the iframe HTML for analysis
    with open("folder_iframe.html", "w", encoding="utf-8") as f:
        f.write(iframe_response.text)
    print("Saved iframe HTML response to folder_iframe.html for analysis")
    
    # Extract file entries from iframe
    iframe_file_entries = re.findall(r'href="https://drive\.google\.com/file/d/([^/]+)/[^"]*"[^>]*>(.*?)</a>', iframe_response.text)
    if iframe_file_entries:
        print(f"\nFound {len(iframe_file_entries)} files in iframe:")
        for i, (file_id, file_name) in enumerate(iframe_file_entries):
            print(f"{i+1}. {file_name.strip()} - ID: {file_id}")
    else:
        print("\nNo files found in iframe")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get_files.py FOLDER_ID")
        sys.exit(1)
    
    folder_id = sys.argv[1]
    get_folder_contents_direct(folder_id) 