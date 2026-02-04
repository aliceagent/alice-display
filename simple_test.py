#!/usr/bin/env python3
"""
Simple Cloudinary upload test to verify credentials.
"""

import requests
from pathlib import Path

# Cloudinary Configuration  
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dfzowmhfp")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "965349664584469")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "YOUR_API_SECRET_HERE")

def test_basic_upload():
    """Test basic unsigned upload first."""
    
    # Get a test image
    gallery_path = Path.home() / "alice-gallery-images"
    test_images = list(gallery_path.glob("*.png"))[:1]
    
    if not test_images:
        print("❌ No test images found")
        return
    
    test_image = test_images[0]
    print(f"📤 Testing upload of: {test_image.name}")
    
    try:
        # Try basic upload without signature first
        upload_data = {
            'api_key': API_KEY,
            'upload_preset': 'ml_default',  # Use default preset for testing
        }
        
        with open(test_image, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f'https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload',
                data=upload_data,
                files=files,
                timeout=60
            )
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! URL: {result.get('secure_url', 'No URL')}")
            return True
        else:
            print(f"❌ Upload failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_cloudinary_api():
    """Test if we can reach Cloudinary API."""
    try:
        response = requests.get(f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/list", 
                               params={'api_key': API_KEY}, timeout=10)
        print(f"API reachability test: {response.status_code}")
        if response.status_code == 401:
            print("🔐 API credentials work but need proper auth for this endpoint")
        elif response.status_code == 200:
            print("✅ API credentials work!")
        else:
            print(f"❓ Unexpected response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ API unreachable: {e}")

def main():
    print("🧪 Simple Cloudinary Test")
    print("=" * 30)
    
    print("\n1️⃣ Testing API Reachability")
    test_cloudinary_api()
    
    print("\n2️⃣ Testing Basic Upload")
    test_basic_upload()

if __name__ == "__main__":
    main()