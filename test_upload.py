#!/usr/bin/env python3
"""
Test uploader for debugging issues with the full gallery upload.
Uploads just a few images to test the pipeline.
"""

import os
import sys
import json
import time
import hashlib
import hmac
import requests
from datetime import datetime
from pathlib import Path

# Cloudinary Configuration
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dfzowmhfp")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "965349664584469")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "YOUR_API_SECRET_HERE")

def create_signature(params, api_secret):
    """Create Cloudinary API signature"""
    sorted_params = sorted(params.items())
    params_string = '&'.join([f'{k}={v}' for k, v in sorted_params])
    signature = hmac.new(
        api_secret.encode('utf-8'),
        params_string.encode('utf-8'),
        hashlib.sha1
    ).hexdigest()
    return signature

def upload_image(image_path, public_id, folder):
    """Upload single image to Cloudinary."""
    if not os.path.exists(image_path):
        return False, f"Image file not found: {image_path}"
    
    timestamp = int(time.time())
    
    params = {
        'folder': folder,
        'public_id': public_id,
        'timestamp': timestamp
    }
    
    signature = create_signature(params, API_SECRET)
    
    upload_data = {
        'api_key': API_KEY,
        'timestamp': timestamp,
        'folder': folder,
        'public_id': public_id,
        'signature': signature
    }
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f'https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload',
                data=upload_data,
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            return True, result['secure_url']
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, str(e)

def test_upload():
    """Test upload with a few images."""
    print("🧪 Testing Cloudinary Upload")
    print("=" * 40)
    
    # Get first 5 valid images
    gallery_path = Path.home() / "alice-gallery-images"
    if not gallery_path.exists():
        print(f"❌ Gallery directory not found: {gallery_path}")
        return
    
    exclude_patterns = [
        "Alice_Attending_Lively_Purim",
        "Alice_Reading_Megillah", 
        "2026-"
    ]
    
    all_images = list(gallery_path.glob("*.png"))
    valid_images = []
    
    for img_path in all_images:
        if any(pattern in img_path.name for pattern in exclude_patterns):
            continue
        valid_images.append(img_path)
        if len(valid_images) >= 5:  # Test with just 5 images
            break
    
    print(f"📁 Testing with {len(valid_images)} images")
    
    upload_log = []
    cloudinary_urls = {}
    
    for i, image_path in enumerate(valid_images, 1):
        filename = image_path.stem
        folder = "alice-gallery/anime"  # Default for testing
        public_id = filename
        
        print(f"📤 {i}: Uploading {filename}")
        print(f"     Path: {image_path}")
        print(f"     Folder: {folder}")
        
        success, result = upload_image(str(image_path), public_id, folder)
        
        log_entry = {
            "filename": filename,
            "image_path": str(image_path),
            "folder": folder,
            "public_id": public_id,
            "success": success,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        upload_log.append(log_entry)
        
        if success:
            print(f"     ✅ Success: {result}")
            cloudinary_urls[filename] = result
        else:
            print(f"     ❌ Failed: {result}")
        
        # Small delay
        time.sleep(2)
    
    # Save results
    os.makedirs("data", exist_ok=True)
    
    with open("test_upload_log.json", 'w') as f:
        json.dump(upload_log, f, indent=2)
    
    with open("data/cloudinary-urls-test.json", 'w') as f:
        json.dump(cloudinary_urls, f, indent=2)
    
    success_count = sum(1 for entry in upload_log if entry["success"])
    print(f"\n🎉 Test Upload Complete!")
    print(f"   Successful: {success_count}/{len(upload_log)}")
    print(f"   📝 Log: test_upload_log.json")
    print(f"   📁 URLs: data/cloudinary-urls-test.json")
    
    return success_count, len(upload_log)

def main():
    os.chdir(Path(__file__).parent)
    test_upload()

if __name__ == "__main__":
    main()