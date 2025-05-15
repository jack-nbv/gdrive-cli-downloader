'''
gcd.py - CLI wrapper for aria2c with Google Drive support
'''

import sys
import os
import shutil
import argparse
import platform
from gdrive_handler import (
    get_download_url_and_filename,
    build_aria2c_options,
    is_folder,
    download_folder
)

def show_help():
    print('''
gcd.py - CLI wrapper for aria2c with Google Drive support

Usage:
    gcd.py [aria2c_options] --gdrive FILE_ID_OR_FOLDER_ID [--debug]

    All standard aria2c options are supported and will be passed through.
    
    Special options:
    --gdrive FILE_ID           Google Drive file or folder ID (required)
    --debug                    Enable debug mode with more verbose output

Example:
    # Download a single file
    gcd.py --gdrive 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT -x16 -s16
    
    # Download an entire folder to a specific directory
    gcd.py --gdrive 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT --dir my_downloads
    
    This will download the Google Drive file/folder with ID 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT
    using aria2c with the options -x16 -s16.
''')

def get_aria2c_path():
    """Get the path to the aria2c executable, preferring system installation"""
    
    # First check if aria2c is in PATH (system installation)
    aria2c_in_path = shutil.which("aria2c")
    if aria2c_in_path:
        return aria2c_in_path
    
    # If not found in PATH, check local directories as fallback
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check for aria2c in several local locations
    possible_locations = [
        # Check in same directory
        os.path.join(script_dir, "aria2c.exe") if platform.system() == "Windows" else os.path.join(script_dir, "aria2c"),
        # Check in aria2 subfolder
        os.path.join(script_dir, "aria2", "aria2c.exe") if platform.system() == "Windows" else os.path.join(script_dir, "aria2", "aria2c"),
        # Check in bin subfolder
        os.path.join(script_dir, "bin", "aria2c.exe") if platform.system() == "Windows" else os.path.join(script_dir, "bin", "aria2c")
    ]
    
    # Try each location
    for aria2c_path in possible_locations:
        if os.path.exists(aria2c_path):
            # Make sure it's executable on Unix-like systems
            if platform.system() != "Windows":
                try:
                    os.chmod(aria2c_path, 0o755)
                except Exception:
                    pass
            
            return aria2c_path
    
    return None

def main():
    # Get the aria2c path
    aria2c_path = get_aria2c_path()
    
    # Check if aria2c is available
    if aria2c_path is None:
        print("Error: aria2c is not installed or not in your PATH")
        print("Please install aria2c and try again")
        print("Visit https://github.com/aria2/aria2/releases to download")
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--gdrive', metavar='FILE_ID', help='Google Drive file or folder ID')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with more verbose output')
    parser.add_argument('--help', '-h', action='store_true', help='Show help message')
    
    # First parse to get our custom arguments, ignore the rest
    args, remaining = parser.parse_known_args()
    
    # Show help and exit if requested
    if args.help or len(sys.argv) == 1:
        show_help()
        sys.exit(0)
    
    # Check if a Google Drive ID was provided
    if not args.gdrive:
        print("Error: No Google Drive file/folder ID specified")
        print("Use --gdrive FILE_ID to specify a Google Drive file or folder ID")
        show_help()
        sys.exit(1)
    
    try:
        drive_id = args.gdrive
        
        # Enable debugging globally if requested
        if args.debug:
            os.environ["GCD_DEBUG"] = "1"
            print("\n=== Debug mode enabled ===")
            print(f"Using aria2c from: {aria2c_path}")
            
            # Check if it's a system installation or local copy
            system_aria2c = shutil.which("aria2c")
            if system_aria2c:
                if system_aria2c == aria2c_path:
                    print("Using system-installed aria2c")
                else:
                    print(f"System aria2c found at {system_aria2c} but using local copy instead")
            else:
                print("Using local aria2c copy (no system installation found)")
        
        # Override the os.system function to use the local aria2c
        original_system = os.system
        
        def custom_system(command):
            # For Windows, use PowerShell to handle URL escaping properly
            if platform.system() == "Windows" and ('aria2c' in command or aria2c_path in command):
                # Extract the URL part for proper escaping
                parts = command.split('"')
                url_part = ""
                for i, part in enumerate(parts):
                    if "&export=download" in part:
                        url_part = part
                        break
                
                # For Windows/PowerShell, we need to handle the command differently
                # Create a simple batch file with the command and execute it
                batch_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aria2c_download.bat")
                with open(batch_file, "w") as f:
                    f.write(f'@echo off\n{command}\n')
                
                if args.debug:
                    print(f"Created batch file: {batch_file}")
                    print(f"With command: {command}")
                
                return original_system(f'"{batch_file}"')
            else:
                # For non-Windows platforms, just execute directly
                if command.startswith('aria2c '):
                    # Replace the command with the path to the local aria2c
                    command = command.replace('aria2c ', f'"{aria2c_path}" ')
                
                if args.debug:
                    print(f"Executing: {command}")
                    
                return original_system(command)
        
        # Replace the os.system function
        os.system = custom_system
        
        # Remove our custom arguments from the remaining arguments list
        filtered_args = []
        skip_next = False
        for i, arg in enumerate(remaining):
            if skip_next:
                skip_next = False
                continue
            
            if arg in ('--gdrive', '--debug'):
                skip_next = (arg != '--debug')
                continue
            
            filtered_args.append(arg)
        
        # Convert the filtered args to a space-separated string
        aria2c_args = " ".join(filtered_args)
        
        # Add some default aria2c parameters if none are provided
        if not aria2c_args:
            aria2c_args = "-x8 -s8 -j5 --retry-wait=3 --max-tries=5 --connect-timeout=60"
            print(f"No aria2c parameters specified, using defaults: {aria2c_args}")
        
        # Debug output
        if args.debug:
            print(f"Drive ID: {drive_id}")
            print(f"Aria2c arguments: {aria2c_args}")
        
        # Check if the ID is for a folder
        print(f"Checking if {drive_id} is a folder or file...")
        if is_folder(drive_id):
            print(f"Detected Google Drive folder: {drive_id}")
            
            # Extract directory parameter if present
            output_dir = None
            
            # Look for --dir or -d in aria2c_args
            parts = aria2c_args.split()
            for i, part in enumerate(parts):
                if (part == "--dir" or part == "-d") and i + 1 < len(parts):
                    output_dir = parts[i + 1].strip('"\'')
                    break
            
            # Download the entire folder
            success = download_folder(drive_id, output_dir, aria2c_args)
            
            if success:
                print("\nFolder download completed successfully")
                if args.debug and output_dir:
                    # Print summary of downloaded files
                    print(f"\nDownloaded files in {output_dir}:")
                    for root, dirs, files in os.walk(output_dir):
                        for file in files:
                            print(f"  - {os.path.join(root, file)}")
            else:
                print("\nFolder download failed")
                sys.exit(1)
        else:
            print(f"Detected Google Drive file: {drive_id}")
            
            # Get download information from Google Drive
            download_url, cookies, filename = get_download_url_and_filename(drive_id)
            
            if args.debug and filename:
                print(f"Detected filename from Google Drive: {filename}")
            
            # Build aria2c options for Google Drive
            cookie_header, output_option = build_aria2c_options(download_url, cookies, filename, drive_id)
            
            # Add reliability options
            reliability_options = "--max-tries=5 --retry-wait=5 --max-file-not-found=5 --connect-timeout=60"
            
            # Use standard quoting, PowerShell will handle special characters
            # Construct the aria2c command
            if platform.system() == "Windows":
                cmd = f'"{aria2c_path}" {aria2c_args} {reliability_options} {output_option} --header="Cookie: {cookie_header}" "{download_url}"'
            else:
                # For Unix systems
                safe_url = f"'{download_url}'"
                cmd = f'aria2c {aria2c_args} {reliability_options} {output_option} --header="Cookie: {cookie_header}" {safe_url}'
            
            print(f"Executing download command...")
            if args.debug:
                print(f"Download URL: {download_url}")
                print(f"Full command: {cmd}")
            else:
                print(f"Downloading file...")
            
            # Execute the aria2c command
            errorcode = os.system(cmd)
            if errorcode != 0:
                print(f"Download failed with error code {errorcode}")
                print("Retrying with alternative URL...")
                
                # Try with alternative URL format
                alt_url = f"https://drive.google.com/uc?id={drive_id}&export=download&confirm=t"
                
                # Construct the command
                if platform.system() == "Windows":
                    cmd = f'"{aria2c_path}" {aria2c_args} {reliability_options} {output_option} --header="Cookie: {cookie_header}" "{alt_url}"'
                else:
                    safe_alt_url = f"'{alt_url}'"
                    cmd = f'aria2c {aria2c_args} {reliability_options} {output_option} --header="Cookie: {cookie_header}" {safe_alt_url}'
                
                errorcode = os.system(cmd)
                if errorcode != 0:
                    print(f"Retry with alternative URL failed. Trying without filename...")
                    
                    # Try again without specifying filename
                    if platform.system() == "Windows":
                        cmd = f'"{aria2c_path}" {aria2c_args} {reliability_options} --header="Cookie: {cookie_header}" "{download_url}"'
                    else:
                        safe_url = f"'{download_url}'"
                        cmd = f'aria2c {aria2c_args} {reliability_options} --header="Cookie: {cookie_header}" {safe_url}'
                    
                    errorcode = os.system(cmd)
                    
                    if errorcode != 0:
                        print(f"All attempts failed with error code {errorcode}")
                        print("Possible reasons:")
                        print("- The file might not exist or is not accessible")
                        print("- Google Drive might be rate limiting your requests")
                        print("- The file might be too large for direct download")
                        sys.exit(1)
                    else:
                        print("Download completed successfully on retry")
                else:
                    print("Download completed successfully with alternative URL")
            else:
                print("Download completed successfully")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if args and args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Restore the original os.system function
        if 'original_system' in locals():
            os.system = original_system

if __name__ == "__main__":
    main()
			