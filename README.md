# GCD - GoogleDrive CLI Downloader using aria2c
Download large files from Google Drive with aria2c at max speed

## Why do this?
With small files, you can easily download them using ```aria2c -x16 -s16 -j5 "https://drive.google.com/uc?id=YOURFILEID&export=download"```. But you can't do that with large files because Google will show a warning about virus scanning. This tool automatically handles that warning to download large files from Google Drive without manual confirmation.

## How this works?
This works the same as <a href="https://gist.github.com/iamtekeste/3cdfd0366ebfd2c0d805#gistcomment-2316906">this</a> wget method: Get the auth cookies from Google Drive, pass it to aria2c (see <a href="https://github.com/aria2/aria2/issues/545">this</a>).

## Usage
```
gcd.py [aria2c_options] --gdrive FILE_ID_OR_FOLDER_ID [--debug]
```

### Parameters:
- `--gdrive FILE_ID_OR_FOLDER_ID`: The Google Drive file or folder ID (required)
- `--debug`: Enable debug mode with more verbose output
- All other aria2c options are supported and forwarded directly to aria2c

### Examples:
#### Downloading a single file
If your link is https://drive.google.com/file/d/1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT/view
```
gcd.py --gdrive 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT -x16 -s16
```

#### Downloading an entire folder
If your link is https://drive.google.com/drive/folders/1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT
```
gcd.py --gdrive 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT --dir my_downloads
```

#### Troubleshooting download issues
If you're having problems with downloads, enable debug mode:
```
gcd.py --gdrive 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT --debug
```

## Requirements
- Python 3
- `requests` library: ```pip install requests```
- aria2c (included in the package, no separate installation required)

## Features
- Automatically handles Google Drive's virus scan warning for large files
- Forwards all aria2c options, acting as a transparent wrapper
- Tries to extract and preserve the original filename
- Supports downloading entire folders, including nested subfolders
- Multiple download retry attempts with different URL formats
- Enhanced error handling and diagnostics
- aria2c executable included in the package

## Credits
Special thanks to aria2, requests and other libs.
