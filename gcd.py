'''
gcd.py - CLI wrapper for aria2c with Google Drive support
'''

import sys
import os
import shutil
import argparse
from gdrive_handler import get_download_url_and_filename, build_aria2c_options

def show_help():
    print('''
gcd.py - CLI wrapper for aria2c with Google Drive support

Usage:
    gcd.py [aria2c_options] --gdrive FILE_ID

    All standard aria2c options are supported and will be passed through.
    The --gdrive option is specific to this tool and must be followed by a Google Drive file ID.

Example:
    gcd.py --gdrive 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT -x16 -s16
    
    This will download the Google Drive file with ID 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT
    using aria2c with the options -x16 -s16.
''')

def main():
    # Check if aria2c is installed
    if shutil.which("aria2c") is None:
        print("Error: aria2c is not installed or not in your PATH")
        print("Please install aria2c and try again")
        print("Visit https://github.com/aria2/aria2/releases to download")
        sys.exit(1)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--gdrive', metavar='FILE_ID', help='Google Drive file ID')
    parser.add_argument('--help', '-h', action='store_true', help='Show help message')
    
    # First parse to get the gdrive argument and help flag, ignore the rest
    args, remaining = parser.parse_known_args()
    
    # Show help and exit if requested
    if args.help or len(sys.argv) == 1:
        show_help()
        sys.exit(0)
    
    # Check if a Google Drive file ID was provided
    if not args.gdrive:
        print("Error: No Google Drive file ID specified")
        print("Use --gdrive FILE_ID to specify a Google Drive file ID")
        show_help()
        sys.exit(1)
    
    try:
        file_id = args.gdrive
        
        # Get download information from Google Drive
        download_url, cookies, filename = get_download_url_and_filename(file_id)
        
        # Build aria2c options for Google Drive
        cookie_header, output_option = build_aria2c_options(download_url, cookies, filename, file_id)
        
        # Remove our custom argument from the remaining arguments list
        filtered_args = [arg for i, arg in enumerate(remaining) 
                        if arg != '--gdrive' and 
                        (i == 0 or remaining[i-1] != '--gdrive')]
        
        # Construct the aria2c command
        aria2c_args = " ".join(filtered_args)
        cmd = f'aria2c {aria2c_args} {output_option} --header="Cookie: {cookie_header}" "{download_url}"'
        
        print(f"Executing download command...")
        print(f"Download URL: {download_url}")
        
        # Execute the aria2c command
        errorcode = os.system(cmd)
        if errorcode != 0:
            print(f"Download failed with error code {errorcode}")
            print("Retrying download without specifying filename...")
            
            # Try again without specifying filename
            cmd = f'aria2c {aria2c_args} --header="Cookie: {cookie_header}" "{download_url}"'
            errorcode = os.system(cmd)
            
            if errorcode != 0:
                print(f"Retry failed with error code {errorcode}")
            else:
                print("Download completed successfully on retry")
        else:
            print("Download completed successfully")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
			