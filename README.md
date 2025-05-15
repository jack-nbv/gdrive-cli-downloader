# GCD - GoogleDrive CLI Downloader using aria2c
Download large files from Google Drive with aria2c at max speed

## Why do this?
With small files, you can easily download them using ```aria2c -x16 -s16 -j5 "https://drive.google.com/uc?id=YOURFILEID&export=download"```. But you can't do that with large files because Google will show a warning about virus scanning. This tool automatically handles that warning to download large files from Google Drive without manual confirmation.

## How this works?
This works the same as <a href="https://gist.github.com/iamtekeste/3cdfd0366ebfd2c0d805#gistcomment-2316906">this</a> wget method: Get the auth cookies from Google Drive, pass it to aria2c (see <a href="https://github.com/aria2/aria2/issues/545">this</a>).

## Usage
```
gcd.py [aria2c_options] --gdrive FILE_ID
```

### Parameters:
- `--gdrive FILE_ID`: The Google Drive file ID (required)
- All other aria2c options are supported and forwarded directly to aria2c

### Example:
If your link is https://drive.google.com/file/d/1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT/view
```
gcd.py --gdrive 1nVOL_4NMw8hfszfYYo2bwUSgFtQtulAT -x16 -s16
```

## Requirements
- Python 3
- `requests` library: ```pip install requests``` 
- <a href="https://github.com/aria2/aria2">aria2</a>

## Features
- Automatically handles Google Drive's virus scan warning for large files
- Forwards all aria2c options, acting as a transparent wrapper
- Tries to extract and preserve the original filename

## Credits
Special thanks to aria2, requests and other libs.
