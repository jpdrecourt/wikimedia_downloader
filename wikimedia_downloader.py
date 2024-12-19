import requests
import os
from pathlib import Path
import time
import json
from urllib.parse import quote, unquote

def get_file_info(filename):
    """Get direct file information and download URL."""
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "titles": f"File:{filename}"
    }
    
    try:
        response = requests.get(api_url, params=params)
        data = response.json()
        pages = data.get('query', {}).get('pages', {})
        if pages:
            page = next(iter(pages.values()))
            if 'imageinfo' in page:
                return page['imageinfo'][0]
    except Exception as e:
        print(f"Error getting file info: {e}")
    return None

def search_wikimedia(search_term):
    """Search for images using MediaWiki API."""
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",  # File namespace
        "gsrsearch": f"filetype:bitmap {quote(search_term)}",
        "gsrlimit": 50,
        "prop": "imageinfo",
        "iiprop": "url|mime|size"
    }
    
    print(f"\nSearching for '{search_term}'...")
    
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'query' not in data:
            print("No results found.")
            print("Debug info:")
            print(json.dumps(data, indent=2))
            return []
            
        pages = data['query'].get('pages', {})
        if not pages:
            print("No images found.")
            return []
            
        return list(pages.values())
        
    except Exception as e:
        print(f"Error during search: {e}")
        return []

def download_file(url, filepath):
    """Download file with progress indicator."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get file size for progress
        total_size = int(response.headers.get('content-length', 0))
        print(f"File size: {total_size/1024/1024:.1f} MB")
        
        downloaded_size = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    # Show progress
                    if total_size:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\rProgress: {progress:.1f}%", end='', flush=True)
                        
        print("\nDownload complete!")
        return True
        
    except Exception as e:
        print(f"\nError downloading file: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

def process_images(search_term, max_images):
    """Process and download images."""
    # Create download directory
    download_dir = Path.cwd() / "downloads" / search_term.replace(" ", "_")
    download_dir.mkdir(parents=True, exist_ok=True)
    print(f"Download directory: {download_dir}")
    
    # Search for images
    results = search_wikimedia(search_term)
    if not results:
        return 0
        
    print(f"Found {len(results)} potential images")
    
    downloaded = []
    for result in results:
        if len(downloaded) >= max_images:
            break
            
        try:
            title = result.get('title', '').replace('File:', '')
            if not title:
                continue
                
            # Get image info
            image_info = result.get('imageinfo', [{}])[0]
            if not image_info or 'url' not in image_info:
                continue
                
            url = image_info['url']
            
            # Create safe filename
            safe_filename = title.replace(' ', '_')
            filepath = download_dir / safe_filename
            
            print(f"\nDownloading: {title}")
            print(f"URL: {url}")
            
            if download_file(url, filepath):
                file_size = os.path.getsize(filepath)
                if file_size == 0:
                    print("Downloaded file is empty, skipping...")
                    os.remove(filepath)
                    continue
                    
                downloaded.append({
                    'filename': safe_filename,
                    'url': url,
                    'size': f"{file_size/1024/1024:.1f} MB"
                })
                print(f"Successfully saved to: {filepath}")
            
        except Exception as e:
            print(f"Error processing image: {e}")
            continue
            
        time.sleep(1)  # Rate limiting
    
    # Generate report
    if downloaded:
        report_path = download_dir / 'download_report.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Downloaded Images Report\n\n")
            for info in downloaded:
                f.write(f"## {info['filename']}\n")
                f.write(f"- Source: {info['url']}\n")
                f.write(f"- Size: {info['size']}\n\n")
        print(f"\nDownload report saved to: {report_path}")
    
    return len(downloaded)

def main():
    search_term = input("Enter search term: ").strip()
    if not search_term:
        print("Error: Search term cannot be empty")
        return
    
    try:
        max_images = int(input(f"Enter maximum number of images to download (max 500): "))
        max_images = min(max(1, max_images), 500)
    except ValueError:
        print("Invalid input. Using default value of 10 images.")
        max_images = 10
    
    print(f"\nStarting download of up to {max_images} images for '{search_term}'")
    count = process_images(search_term, max_images)
    print(f"\nFinished! Successfully downloaded {count} images.")

if __name__ == "__main__":
    main()