'''
gdrive_handler.py - Module for handling Google Drive downloads
'''

import requests
import re
import uuid

def get_download_url_and_filename(file_id):
    """
    Gets the direct download URL, cookies, and filename for a Google Drive file
    
    Args:
        file_id (str): The Google Drive file ID
        
    Returns:
        tuple: (download_url, cookies_dict, filename)
    """
    session = requests.Session()
    
    # First request to get the warning page
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    response = session.get(url)
    
    # Try to extract filename from the page
    filename = None
    filename_match = re.search(r'<span class="uc-name-size"><a[^>]*>([^<]+)</a>', response.text)
    if filename_match:
        filename = filename_match.group(1)
        filename = filename.strip()
        print(f"Found filename: {filename}")
    
    # Check if we're dealing with the virus scan warning page
    if "Google Drive can't scan this file for viruses" in response.text:
        print("Detected virus scan warning page for large file")
        
        # Extract the direct download URL from the HTML
        form_action = re.search(r'<form id="download-form" action="([^"]+)"', response.text)
        confirm_value = re.search(r'<input type="hidden" name="confirm" value="([^"]+)"', response.text)
        
        if form_action and confirm_value:
            confirm = confirm_value.group(1)
            # Create direct download URL
            direct_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm={confirm}&uuid={uuid.uuid4()}"
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
        safe_filename = filename.replace('"', '\\"')
        output_option = f'-o "{safe_filename}"'
    else:
        # If filename can't be determined, use the file ID
        output_option = f'-o "gdrive_{file_id}"'
    
    return cookie_header, output_option 