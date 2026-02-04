#!/usr/bin/env python3
"""
Fixed Cloudinary uploader with correct signature generation.
"""

import hashlib
import hmac
import json
import os
import requests
import time
from pathlib import Path

# Cloudinary Configuration
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dfzowmhfp")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "965349664584469")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "YOUR_API_SECRET_HERE")

def create_cloudinary_signature(params, api_secret):
    """Create Cloudinary signature in the correct format."""
    # Remove api_key and file from params for signature
    sign_params = {k: v for k, v in params.items() if k not in ['api_key', 'file']}
    
    # Sort parameters alphabetically and create signature string
    sorted_items = sorted(sign_params.items())
    params_string = '&'.join([f'{k}={v}' for k, v in sorted_items])
    
    # Add API secret at the end
    string_to_sign = f"{params_string}{api_secret}"
    
    # Create SHA-1 hash
    return hashlib.sha1(string_to_sign.encode('utf-8')).hexdigest()

def upload_to_cloudinary(image_path, folder="alice-gallery", public_id=None):
    """Upload image to Cloudinary with proper authentication."""
    
    if not os.path.exists(image_path):
        return False, f"File not found: {image_path}"
    
    # Use filename as public_id if not provided
    if not public_id:
        public_id = Path(image_path).stem
    
    # Current timestamp
    timestamp = int(time.time())
    
    # Parameters for upload (including those for signature)
    params = {
        'timestamp': timestamp,
        'folder': folder,
        'public_id': public_id,
        'api_key': API_KEY,
    }
    
    # Create signature
    signature = create_cloudinary_signature(params, API_SECRET)
    params['signature'] = signature
    
    print(f"📤 Uploading {Path(image_path).name}")
    print(f"   Folder: {folder}")
    print(f"   Public ID: {public_id}")
    print(f"   Timestamp: {timestamp}")
    
    try:
        # Prepare the request
        url = f'https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload'
        
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {k: v for k, v in params.items() if k != 'file'}
            
            response = requests.post(url, data=data, files=files, timeout=30)
        
        print(f"   Response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            secure_url = result.get('secure_url')
            print(f"   ✅ Success: {secure_url}")
            return True, secure_url
        else:
            error_text = response.text[:200]
            print(f"   ❌ Error: {error_text}")
            return False, f"HTTP {response.status_code}: {error_text}"
    
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Exception: {error_msg}")
        return False, error_msg

def test_signature_creation():
    """Test the signature creation separately."""
    print("🧪 Testing Signature Creation")
    
    # Test parameters
    test_params = {
        'timestamp': 1234567890,
        'folder': 'test',
        'public_id': 'test_image',
        'api_key': API_KEY,
    }
    
    signature = create_cloudinary_signature(test_params, API_SECRET)
    print(f"Test signature: {signature}")
    
    # Manual verification
    # Expected string to sign: "folder=test&public_id=test_image&timestamp=1234567890{API_SECRET}"
    expected_string = f"folder=test&public_id=test_image&timestamp=1234567890{API_SECRET}"
    expected_signature = hashlib.sha1(expected_string.encode('utf-8')).hexdigest()
    
    print(f"String to sign: {expected_string}")
    print(f"Expected signature: {expected_signature}")
    print(f"Generated signature: {signature}")
    print(f"Signatures match: {signature == expected_signature}")

def main():
    """Test the fixed uploader."""
    print("🚀 Fixed Cloudinary Uploader Test")
    print("=" * 40)
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    # Test signature creation first
    test_signature_creation()
    
    print("\n📤 Testing Upload")
    
    # Get a test image
    gallery_path = Path.home() / "alice-gallery-images"
    test_images = list(gallery_path.glob("*.png"))[:1]
    
    if not test_images:
        print("❌ No test images found")
        return
    
    test_image = test_images[0]
    
    # Test upload
    success, result = upload_to_cloudinary(
        str(test_image), 
        folder="alice-gallery/test",
        public_id="test_upload"
    )
    
    if success:
        print(f"\n✅ Upload successful!")
        print(f"   URL: {result}")
        
        # Save result
        with open("test_cloudinary_result.json", "w") as f:
            json.dump({
                "success": True,
                "url": result,
                "timestamp": time.time()
            }, f, indent=2)
        
    else:
        print(f"\n❌ Upload failed: {result}")

if __name__ == "__main__":
    main()