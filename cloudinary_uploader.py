#!/usr/bin/env python3
"""
Cloudinary Upload System for Alice Gallery
Uploads images with systematic folder structure:
- alice-gallery/anime/001-anime.png
- alice-gallery/comic-90s/002-comic-90s.png
- etc.
"""

import requests
import hashlib
import hmac
import time
import json
import os
from datetime import datetime

# Cloudinary Configuration  
CLOUD_NAME = "dfzowmhfp"
API_KEY = "965349664584469"
API_SECRET = "iKIDovK2zXK_7KeOVsqN0tinmpY"

def create_signature(params, api_secret):
    """Create Cloudinary API signature"""
    # Sort parameters and create string
    sorted_params = sorted(params.items())
    params_string = '&'.join([f'{k}={v}' for k, v in sorted_params])
    
    # Create signature
    signature = hmac.new(
        api_secret.encode('utf-8'),
        params_string.encode('utf-8'),
        hashlib.sha1
    ).hexdigest()
    
    return signature

def upload_image(image_path, public_id, folder="alice-gallery"):
    """Upload image to Cloudinary with proper folder structure"""
    if not os.path.exists(image_path):
        return False, f"Image file not found: {image_path}"
        
    timestamp = int(time.time())
    
    # Parameters for signature (don't include file or api_key)
    params = {
        'folder': folder,
        'public_id': public_id,
        'timestamp': timestamp
    }
    
    # Create signature
    signature = create_signature(params, API_SECRET)
    
    # Upload data (includes api_key and signature)
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

def upload_alice_image(row, style, local_image_path):
    """Upload Alice image with systematic naming"""
    padded_row = f"{row:03d}"
    public_id = f"{style}/{padded_row}-{style}"
    
    print(f"📤 Uploading Row {padded_row} - {style.title()} Style...")
    print(f"   Local: {local_image_path}")
    print(f"   Public ID: alice-gallery/{public_id}")
    
    success, result = upload_image(local_image_path, public_id)
    
    if success:
        cloudinary_url = result
        print(f"   ✅ Success: {cloudinary_url}")
        return True, cloudinary_url
    else:
        print(f"   ❌ Failed: {result}")
        return False, result

def batch_upload_style(style, image_directory, max_images=383):
    """Upload all images for a specific style"""
    print(f"\n🎨 Starting batch upload for {style.upper()} style...")
    print(f"📁 Looking for images in: {image_directory}")
    
    success_count = 0
    failed_count = 0
    upload_log = []
    
    for row in range(1, max_images + 1):
        padded_row = f"{row:03d}"
        local_filename = f"{padded_row}-{style}.png"
        local_path = os.path.join(image_directory, local_filename)
        
        if not os.path.exists(local_path):
            print(f"⚠️  Row {padded_row}: Image not found, skipping")
            continue
            
        success, result = upload_alice_image(row, style, local_path)
        
        upload_log.append({
            "row": row,
            "style": style, 
            "local_path": local_path,
            "success": success,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if success:
            success_count += 1
        else:
            failed_count += 1
            
        # Rate limiting - be gentle with Cloudinary
        time.sleep(0.5)
        
        # Progress updates
        if row % 50 == 0:
            print(f"\n📊 Progress: {row}/{max_images} images")
            print(f"✅ Success: {success_count}, ❌ Failed: {failed_count}")
            print("-" * 50)
    
    # Save upload log
    log_filename = f"upload_log_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_filename, 'w') as f:
        json.dump(upload_log, f, indent=2)
    
    print(f"\n🎉 {style.upper()} BATCH COMPLETE!")
    print(f"✅ Successful uploads: {success_count}")
    print(f"❌ Failed uploads: {failed_count}")  
    print(f"📝 Log saved: {log_filename}")
    
    return success_count, failed_count

def main():
    print("🚀 Alice Gallery Cloudinary Upload System")
    print(f"☁️  Target: {CLOUD_NAME}")
    print(f"📁 Folder: alice-gallery/")
    print(f"🎨 Styles: anime, comic-90s, realistic, renaissance, disney")
    print("=" * 60)
    
    # Example usage - modify paths as needed
    styles = ["anime", "comic-90s", "realistic", "renaissance", "disney"]
    
    print("📋 UPLOAD PLAN:")
    for style in styles:
        image_dir = f"generated_images/{style}/"  # Adjust path as needed
        print(f"   {style}: {image_dir}")
    
    print("\n⚠️  READY TO UPLOAD - This will upload up to 1,915 images!")
    print("    Make sure your generated_images/ folder structure matches above")
    print("    Each style should have 001-{style}.png through 383-{style}.png")
    print("\n🔧 Modify the paths in this script and run when ready!")

if __name__ == "__main__":
    main()