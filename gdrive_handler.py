'''
gdrive_handler.py - Module for handling Google Drive downloads
'''

import requests
import re
import uuid
import os
import json
import time
import random
import urllib.parse
from urllib.parse import parse_qs, urlparse
import platform
import shutil

def get_download_url_and_filename(file_id):
    """
    Gets the direct download URL, cookies, and filename for a Google Drive file
    
    Args:
        file_id (str): The Google Drive file ID
        
    Returns:
        tuple: (download_url, cookies_dict, filename)
    """
    session = requests.Session()
    
    # First try to get filename from the file view page
    file_view_url = f"https://drive.google.com/file/d/{file_id}/view"
    file_view_response = session.get(file_view_url)
    
    filename = None
    
    # Extract filename from file view page (more reliable)
    if file_view_response.status_code == 200:
        # Check several possible patterns
        filename_patterns = [
            r'<meta property="og:title" content="([^"]+)">',
            r'<title>([^<]+) - Google Drive</title>',
            r'"title":"([^"]+)"'
        ]
        
        for pattern in filename_patterns:
            match = re.search(pattern, file_view_response.text)
            if match:
                filename = match.group(1).strip()
                print(f"Found filename from file view: {filename}")
                break
    
    # Now get the download URL
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    response = session.get(url)
    
    # Try to extract filename from the download page as fallback
    if not filename:
        # Try multiple patterns for filename
        filename_patterns = [
            r'<span class="uc-name-size"><a[^>]*>([^<]+)</a>',
            r'<span class="uc-name-size">\s*<a[^>]*>([^<]+)</a>',
            r'filename="([^"]+)"',
            r'<h2>([^<]+)</h2>'
        ]
        
        for pattern in filename_patterns:
            match = re.search(pattern, response.text)
            if match:
                filename = match.group(1).strip()
                print(f"Found filename from download page: {filename}")
                break
    
    # Check if we're dealing with the virus scan warning page
    if "Google Drive can't scan this file for viruses" in response.text:
        print("Detected virus scan warning page for large file")
        
        # Extract the direct download URL from the HTML
        form_action = re.search(r'<form id="download-form" action="([^"]+)"', response.text)
        confirm_value = re.search(r'<input type="hidden" name="confirm" value="([^"]+)"', response.text)
        
        if form_action and confirm_value:
            confirm = confirm_value.group(1)
            # Create direct download URL with UUID to avoid caching issues
            direct_url = f"https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}"
            return direct_url, session.cookies.get_dict(), filename
    
    # If we reach here, try the normal approach
    for key, value in session.cookies.items():
        if key.startswith('download_warning_'):
            return f"https://drive.google.com/uc?export=download&confirm={value}&id={file_id}", session.cookies.get_dict(), filename
    
    # If no download warning cookie, just return the original URL
    return url, session.cookies.get_dict(), filename

def build_aria2c_options(download_url, cookies, filename=None, file_id=None):
    """
    Builds aria2c options for a Google Drive download
    
    Args:
        download_url (str): The direct download URL
        cookies (dict): Cookies for authentication
        filename (str, optional): The filename to save as
        file_id (str, optional): The file ID (used as fallback filename)
        
    Returns:
        tuple: (cookie_header, output_option)
    """
    # Build cookie header
    cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    
    # Prepare output filename option
    if filename:
        # Make sure filename is safe for command line
        safe_filename = filename.replace('"', '\\"').replace('*', '_').replace('?', '_').replace('|', '_').replace(':', '_')
        output_option = f'-o "{safe_filename}"'
    else:
        # If filename can't be determined, use the file ID
        output_option = f'-o "gdrive_{file_id}"'
    
    return cookie_header, output_option

def is_folder(drive_id):
    """
    Check if the provided Google Drive ID is a folder
    
    Args:
        drive_id (str): The Google Drive ID
    
    Returns:
        bool: True if it's a folder, False otherwise
    """
    # First, try to get the file info directly
    file_url = f"https://drive.google.com/file/d/{drive_id}/view"
    file_response = requests.get(file_url)
    
    # If the file URL returns success and contains file ID, it's a file
    if file_response.status_code == 200 and "drive_site_file_id" in file_response.text:
        return False
    
    # Try folder URL next
    folder_url = f"https://drive.google.com/drive/folders/{drive_id}"
    folder_response = requests.get(folder_url)
    
    # If the URL loads successfully and contains folder-specific metadata
    if folder_response.status_code == 200 and "drive_site_folder_id" in folder_response.text:
        return True
    
    # Try embedded folder view
    iframe_url = f"https://drive.google.com/embeddedfolderview?id={drive_id}#list"
    iframe_response = requests.get(iframe_url)
    
    # If the iframe content has file entries, it's a folder
    if "flip-entry-title" in iframe_response.text:
        return True
    
    # If nothing matched so far, try getting a download URL
    # If we can get a direct download URL, it's most likely a file
    test_url = f"https://drive.google.com/uc?id={drive_id}&export=download"
    session = requests.Session()
    test_response = session.get(test_url)
    
    # Check if we get any download cookies or download link  
    for key in session.cookies.keys():
        if key.startswith('download_warning_'):
            return False
            
    # Check if the page contains the filename, which would indicate it's a file
    if re.search(r'<span class="uc-name-size"><a[^>]*>([^<]+)</a>', test_response.text):
        return False
        
    # If we can't definitively determine it's a file, default to assuming it's a folder
    # but only if we got a 200 response for the folder URL
    return folder_response.status_code == 200

def get_folder_name(folder_id):
    """
    Gets the name of the Google Drive folder
    
    Args:
        folder_id (str): The Google Drive folder ID
    
    Returns:
        str: The folder name or None if not found
    """
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    response = requests.get(url)
    
    # Extract folder name from title
    title_match = re.search(r'<title>([^<]+) - Google Drive</title>', response.text)
    if title_match:
        return title_match.group(1).strip()
    
    # Alternative extraction method
    folder_name_match = re.search(r'<meta property="og:title" content="([^"]+)"', response.text)
    if folder_name_match:
        return folder_name_match.group(1).strip()
    
    # Try using the embedded folder view
    iframe_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    iframe_response = requests.get(iframe_url)
    
    # Look for title in the iframe
    iframe_title_match = re.search(r'<title>([^<]+)</title>', iframe_response.text)
    if iframe_title_match:
        title = iframe_title_match.group(1).strip()
        if title != "Google Drive: Sign-in":
            return title
    
    return f"gdrive_folder_{folder_id}"

def extract_files_from_iframe(content):
    """
    Extract file information from Google Drive's embedded folder view
    
    Args:
        content (str): HTML content of the embedded folder view
        
    Returns:
        list: List of file dictionaries with id, name, type
    """
    files = []
    
    # Find file entries with their IDs and titles
    file_entries = re.findall(r'href="https://drive\.google\.com/file/d/([^/]+)/[^"]*"[^>]*>(.*?)</a>', content)
    
    for file_id, file_html in file_entries:
        # Extract the file name using regex
        name_match = re.search(r'<div class="flip-entry-title">(.*?)</div>', file_html)
        file_name = name_match.group(1) if name_match else f"unknown_file_{file_id}"
        
        # Determine if it's a folder or file (all items in iframe are files)
        files.append({
            "id": file_id,
            "name": file_name,
            "type": "file"
        })
    
    # Look for folders in the iframe (they have a different pattern)
    folder_entries = re.findall(r'href="https://drive\.google\.com/embeddedfolderview\?id=([^&]+)&[^"]*"[^>]*>(.*?)</a>', content)
    for folder_id, folder_html in folder_entries:
        # Extract the folder name using regex
        name_match = re.search(r'<div class="flip-entry-title">(.*?)</div>', folder_html)
        folder_name = name_match.group(1) if name_match else f"unknown_folder_{folder_id}"
        
        files.append({
            "id": folder_id,
            "name": folder_name,
            "type": "folder"
        })
    
    return files

def extract_file_data(content):
    """
    Extracts file data from Google Drive HTML content using multiple methods
    
    Args:
        content (str): HTML content of Google Drive folder page
        
    Returns:
        list: List of file dictionaries with id, name, type
    """
    files = []
    
    # Method 1: Extract from metadata in JSON format
    json_data = re.search(r'window\[\'_DRIVE_ivd\'\]\s*=\s*\'(.*?)\'', content)
    if json_data:
        try:
            # Convert escaped characters in the JSON string
            data_str = json_data.group(1).replace('\\\\', '\\')
            
            # Try to find file entries in the JSON data
            entries = re.findall(r'\["([a-zA-Z0-9_-]{28,})",\[("[a-zA-Z0-9_-]+"|null)', data_str)
            for file_id, file_type in entries:
                # Now extract the file name for this ID
                name_match = re.search(rf'\["{file_id}",[^\]]+\],\["([^"]+)"', data_str)
                if name_match:
                    file_name = name_match.group(1)
                    files.append({
                        "id": file_id,
                        "name": file_name,
                        "type": "folder" if "folder" in file_type.lower() else "file"
                    })
        except Exception as e:
            print(f"Error extracting file data from JSON: {e}")
    
    # Method 2: Extract from the HTML directly using different patterns
    # Look for data-id attributes
    file_entries = re.findall(r'data-id="([^"]+)"[^>]*data-target="([^"]+)"[^>]*aria-label="([^"]+)"', content)
    for file_id, file_type, file_name in file_entries:
        if len(file_id) >= 25:  # Valid Drive IDs are at least 25 chars
            # Clean file name (remove 'Google Drive File: ' prefix if present)
            clean_name = re.sub(r'^Google Drive (File|Folder): ', '', file_name)
            files.append({
                "id": file_id,
                "name": clean_name,
                "type": "folder" if "folder" in file_type.lower() else "file"
            })
    
    # Method 3: Look for data in aria-label attributes
    label_entries = re.findall(r'aria-label="([^"]+)"[^>]*href="[^"]*\/(?:file|folders)\/([a-zA-Z0-9_-]{28,})', content)
    for label, file_id in label_entries:
        # Determine if it's a file or folder from the href
        is_folder = "folders" in label.lower() or "/folders/" in content
        files.append({
            "id": file_id,
            "name": label.replace("Google Drive File: ", "").replace("Google Drive Folder: ", ""),
            "type": "folder" if is_folder else "file"
        })
    
    # Method 4: Direct API info extraction
    file_entries = re.findall(r'\["([a-zA-Z0-9_-]{28,})",[^\]]*\],\["([^"]+)"\]', content)
    for file_id, file_name in file_entries:
        # Try to determine if it's a folder from the context
        is_folder = f'"{file_id}",["folder' in content or f'"{file_id}",[["folder' in content
        files.append({
            "id": file_id,
            "name": file_name,
            "type": "folder" if is_folder else "file"
        })
    
    return files

def get_folder_contents_api(folder_id):
    """
    Gets folder contents using direct API access
    
    Args:
        folder_id (str): The Google Drive folder ID
        
    Returns:
        list: List of file dictionaries with id, name, type
    """
    # Generate API parameters
    num = 100  # Number of files to fetch
    key = "AIzaSyC1eQ1xj69IdTMeKDzq6r_86LH7pJMCmag"  # Default API key from Google Drive
    
    # First try to get a valid key from a Google Drive page
    try:
        resp = requests.get("https://drive.google.com")
        key_match = re.search(r'\"key\":\s*\"([^\"]+)\"', resp.text)
        if key_match:
            key = key_match.group(1)
    except Exception:
        pass
    
    # Create headers with random User-Agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
    ]
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://drive.google.com/drive/folders/{folder_id}"
    }
    
    # Build the API URL
    url = (f"https://clients6.google.com/drive/v2beta/files?openDrive=false&reason=102&syncType=0&errorRecovery=false"
           f"&q=trashed%20%3D%20false%20and%20'{folder_id}'%20in%20parents&fields=kind%2CnextPageToken%2Citems(kind%2CfileSize%2Ctitle%2Cid%2CmimeType%2CmodifiedDate%2CcreatedDate%2CdownloadUrl%2CfileExtension%2CoriginalFilename%2CdrivePath)"
           f"&appDataFilter=NO_APP_DATA&spaces=drive&maxResults={num}&orderBy=folder%2Ctitle_natural%20asc"
           f"&key={key}")
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if "items" in data:
            files = []
            for item in data["items"]:
                file_type = "folder" if item.get("mimeType") == "application/vnd.google-apps.folder" else "file"
                files.append({
                    "id": item.get("id"),
                    "name": item.get("title"),
                    "type": file_type
                })
            return files
        else:
            return []
    except Exception as e:
        print(f"Error accessing folder API: {e}")
        return []

def get_files_from_iframe(folder_id):
    """
    Get files from Google Drive folder using embedded folder view
    
    Args:
        folder_id (str): The Google Drive folder ID
        
    Returns:
        list: List of file dictionaries with id, name, type
    """
    # Generate a user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Access the embedded folder view
    iframe_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    response = requests.get(iframe_url, headers=headers)
    
    if response.status_code == 200:
        # Try to directly extract file entries using regex
        try:
            # Get all file entries (files, not folders)
            file_entries = []
            
            # Method 1: Extract from the HTML directly
            entries = re.findall(r'<div class="flip-entry-([^"]+)".*?href="https://drive\.google\.com/file/d/([^/]+)/.*?<div class="flip-entry-title">(.*?)</div>', 
                                response.text, re.DOTALL)
            
            for entry_type, file_id, file_name in entries:
                file_entries.append({
                    "id": file_id,
                    "name": file_name.strip(),
                    "type": "file"
                })
            
            # If the first method fails, try a simpler approach
            if not file_entries:
                # Method 2: Extract file IDs and names separately
                file_ids = re.findall(r'href="https://drive\.google\.com/file/d/([^/]+)/', response.text)
                file_names = re.findall(r'<div class="flip-entry-title">(.*?)</div>', response.text)
                
                # Match them up if possible
                if len(file_ids) == len(file_names):
                    for i in range(len(file_ids)):
                        file_entries.append({
                            "id": file_ids[i],
                            "name": file_names[i].strip(),
                            "type": "file"
                        })
                else:
                    # Last resort: just use the IDs we found
                    for i, file_id in enumerate(file_ids):
                        name = file_names[i] if i < len(file_names) else f"file_{i+1}"
                        file_entries.append({
                            "id": file_id,
                            "name": name.strip(),
                            "type": "file"
                        })
            
            return file_entries
            
        except Exception as e:
            print(f"Error parsing iframe: {e}")
            # Fallback to the other extraction method
            return extract_files_from_iframe(response.text)
    else:
        print(f"Failed to access iframe view: Status code {response.status_code}")
        return []

def list_files_in_folder(folder_id):
    """
    Lists all files in a Google Drive folder
    
    Args:
        folder_id (str): The Google Drive folder ID
    
    Returns:
        tuple: (list of file dicts, folder_name)
    """
    # 1. Get the folder name
    folder_name = get_folder_name(folder_id)
    print(f"Found folder: {folder_name}")
    
    # 2. First try the iframe method which has highest success rate
    iframe_files = get_files_from_iframe(folder_id)
    if iframe_files:
        print(f"Successfully accessed folder contents via iframe.")
        return iframe_files, folder_name
    
    # 3. Try the API method next
    api_files = get_folder_contents_api(folder_id)
    if api_files:
        print(f"Successfully accessed folder contents via API.")
        return api_files, folder_name
    
    # 4. If both methods above failed, try HTML parsing
    print("Iframe and API methods failed, trying HTML parsing...")
    
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = session.get(url, headers=headers)
    
    # Extract files using the utility function
    files = extract_file_data(response.text)
    
    # If no files detected, try an alternative URL format
    if not files:
        print("Trying alternative method to access folder contents...")
        alt_url = f"https://drive.google.com/drive/u/0/folders/{folder_id}"
        response = session.get(alt_url, headers=headers)
        files = extract_file_data(response.text)
    
    # Try to eliminate duplicate files and clean up file names
    unique_files = []
    seen_ids = set()
    
    for file in files:
        # Normalize and clean the file name
        file_id = file["id"].strip()
        file_name = file["name"].strip()
        
        # Skip files with problematic IDs
        if len(file_id) < 25 or '","' in file_id:
            continue
            
        # Clean up file names with artifacts
        file_name = re.sub(r'\[\s*"[^"]*"\s*,\s*\[.*$', '', file_name)
        file_name = file_name.rstrip('",')
        
        # Deduplicate by ID
        if file_id not in seen_ids:
            seen_ids.add(file_id)
            unique_files.append({
                "id": file_id,
                "name": file_name,
                "type": file["type"]
            })
    
    if not unique_files:
        print("Warning: Could not extract files from the folder. Google Drive structure might have changed.")
        print("Please try using the --debug option for more information.")
        
        # As a last resort, print some debug info
        print(f"Response status: {response.status_code}")
        print(f"Response length: {len(response.text)} characters")
    else:
        # Print detected files for debugging
        print("\nDetected files in folder:")
        for i, file in enumerate(unique_files):
            print(f"{i+1}. {file['name']} ({file['type']}) - ID: {file['id']}")
    
    return unique_files, folder_name

def download_folder(folder_id, output_dir=None, aria2c_args=""):
    """
    Downloads all files in a Google Drive folder
    
    Args:
        folder_id (str): The Google Drive folder ID
        output_dir (str, optional): Directory to save files to
        aria2c_args (str, optional): Additional aria2c arguments
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get list of files in the folder
        files, folder_name = list_files_in_folder(folder_id)
        
        if not files:
            print(f"No files found in folder {folder_id}")
            return False
        
        print(f"Found {len(files)} files/folders in '{folder_name}'")
        
        # Create output directory if specified or use folder name
        if not output_dir:
            output_dir = folder_name if folder_name else f"gdrive_folder_{folder_id}"
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        # Get the aria2c path
        aria2c_path = shutil.which("aria2c")
        
        # If not found in PATH, check local directories as fallback
        if not aria2c_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Check for aria2c in several locations
            possible_locations = [
                # Check in same directory
                os.path.join(script_dir, "aria2c.exe") if platform.system() == "Windows" else os.path.join(script_dir, "aria2c"),
                # Check in aria2 subfolder
                os.path.join(script_dir, "aria2", "aria2c.exe") if platform.system() == "Windows" else os.path.join(script_dir, "aria2", "aria2c"),
                # Check in bin subfolder
                os.path.join(script_dir, "bin", "aria2c.exe") if platform.system() == "Windows" else os.path.join(script_dir, "bin", "aria2c")
            ]
            
            # Try each location
            for path in possible_locations:
                if os.path.exists(path):
                    aria2c_path = path
                    break
        
        if not aria2c_path:
            print("Error: aria2c executable not found. Cannot download folder.")
            return False
        
        # Parse aria2c_args to check if it already contains --dir parameter
        args_list = aria2c_args.split()
        has_dir_param = False
        dir_param_value = None
        
        for i in range(len(args_list)):
            if i < len(args_list) - 1 and (args_list[i] == "--dir" or args_list[i] == "-d"):
                has_dir_param = True
                dir_param_value = args_list[i + 1].strip("'\"")
                break
        
        # Helper function to run commands on Windows using a batch file
        def run_windows_command(cmd):
            # For system aria2c, use the command as is; for local path, use the full path
            if aria2c_path == shutil.which("aria2c"):  # It's a system-installed aria2c
                cmd = cmd.replace('aria2c ', 'aria2c ')  # Keep as is
            else:
                cmd = cmd.replace('aria2c', f'"{aria2c_path}"')
                
            batch_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aria2c_folder_download.bat")
            with open(batch_file, "w") as f:
                f.write(f'@echo off\n{cmd}\n')
            
            print(f"Running command via batch file: {cmd}")
            return os.system(f'"{batch_file}"')
            
        # Download each file
        success_count = 0
        for i, file_info in enumerate(files):
            file_id = file_info["id"]
            file_name = file_info["name"]
            file_type = file_info["type"]
            
            print(f"\nProcessing [{i+1}/{len(files)}]: {file_name} ({file_type})")
            
            if file_type == "folder":
                # Recursively download sub-folders
                subfolder_dir = os.path.join(output_dir, file_name)
                print(f"Downloading subfolder to {subfolder_dir}...")
                download_folder(file_id, subfolder_dir, aria2c_args)
            else:
                # Download the file
                try:
                    # Get download URL and cookies
                    download_url, cookies, extracted_filename = get_download_url_and_filename(file_id)
                    
                    # Use the extracted filename if available, otherwise use the one from folder listing
                    filename_to_use = extracted_filename if extracted_filename else file_name
                    
                    # If we still don't have a filename, generate one based on ID
                    if not filename_to_use or filename_to_use.strip() == "":
                        filename_to_use = f"gdrive_file_{file_id}"
                        print(f"No filename found, using generated name: {filename_to_use}")
                    
                    # Build cookie header
                    cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                    
                    # Set output path, sanitize filename for command line
                    safe_filename = filename_to_use.replace('"', '\\"').replace('*', '_').replace('?', '_').replace('|', '_')
                    output_path = os.path.join(output_dir, safe_filename)
                    
                    # Prepare output option and aria2c args based on whether dir is already specified
                    if has_dir_param:
                        # If --dir is already in aria2c_args, just use the filename
                        output_option = f'-o "{safe_filename}"'
                    else:
                        # If no --dir parameter, use absolute path
                        output_option = f'-o "{output_path}"'
                        
                    # Add additional aria2c parameters for better reliability
                    reliability_options = "--max-tries=5 --retry-wait=5 --max-file-not-found=5 --connect-timeout=60"
                    
                    # Build and execute aria2c command
                    cmd = f'aria2c {aria2c_args} {reliability_options} {output_option} --header="Cookie: {cookie_header}" "{download_url}"'
                    print(f"Downloading: {filename_to_use}")
                    
                    # Use batch file approach on Windows
                    success = False
                    if platform.system() == "Windows":
                        success = (run_windows_command(cmd) == 0)
                    else:
                        # Replace aria2c with full path for Unix
                        cmd = cmd.replace('aria2c', f'"{aria2c_path}"')
                        success = (os.system(cmd) == 0)
                        
                    if success:
                        success_count += 1
                        print(f"Successfully downloaded: {filename_to_use}")
                    else:
                        print(f"Failed to download: {filename_to_use}")
                        
                        # Try alternative download URL format
                        alt_url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm=t"
                        
                        # Build and execute alternative command
                        cmd = f'aria2c {aria2c_args} {reliability_options} {output_option} --header="Cookie: {cookie_header}" "{alt_url}"'
                        print(f"Retrying with alternative URL...")
                        
                        # Use batch file approach on Windows
                        if platform.system() == "Windows":
                            success = (run_windows_command(cmd) == 0)
                        else:
                            # Replace aria2c with full path for Unix
                            cmd = cmd.replace('aria2c', f'"{aria2c_path}"')
                            success = (os.system(cmd) == 0)
                            
                        if success:
                            success_count += 1
                            print(f"Successfully downloaded: {filename_to_use} with alternative URL")
                except Exception as e:
                    print(f"Error downloading {file_name}: {str(e)}")
            
            # Small delay to avoid rate limiting
            time.sleep(1)
        
        print(f"\nFolder download complete: {success_count}/{len(files)} files downloaded successfully to {output_dir}")
        return True
        
    except Exception as e:
        print(f"Error downloading folder: {str(e)}")
        return False 