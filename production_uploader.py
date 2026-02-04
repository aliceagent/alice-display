#!/usr/bin/env python3
"""
Production Gallery Uploader for Alice Display Integration
Uploads all 509 verified base images from ~/alice-gallery-images/ to Cloudinary.
Uses correct signature generation and integrates with Notion metadata.
"""

import os
import sys
import json
import time
import hashlib
import requests
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Cloudinary Configuration
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dfzowmhfp")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "965349664584469")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "YOUR_API_SECRET_HERE")

# Notion Configuration  
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "2fc41906-4d30-8189-a748-c6b715faf485")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "YOUR_NOTION_KEY_HERE")
NOTION_VERSION = "2022-06-28"

# File patterns to exclude
EXCLUDE_PATTERNS = [
    "Alice_Attending_Lively_Purim",
    "Alice_Reading_Megillah",
    "2026-"
]

def create_cloudinary_signature(params, api_secret):
    """Create Cloudinary signature with correct format."""
    # Remove api_key and file from params for signature
    sign_params = {k: v for k, v in params.items() if k not in ['api_key', 'file']}
    
    # Sort parameters alphabetically and create signature string
    sorted_items = sorted(sign_params.items())
    params_string = '&'.join([f'{k}={v}' for k, v in sorted_items])
    
    # Add API secret at the end
    string_to_sign = f"{params_string}{api_secret}"
    
    # Create SHA-1 hash
    return hashlib.sha1(string_to_sign.encode('utf-8')).hexdigest()

def upload_to_cloudinary(image_path, folder, public_id):
    """Upload image to Cloudinary with proper authentication."""
    
    if not os.path.exists(image_path):
        return False, f"File not found: {image_path}"
    
    # Current timestamp
    timestamp = int(time.time())
    
    # Parameters for upload
    params = {
        'timestamp': timestamp,
        'folder': folder,
        'public_id': public_id,
        'api_key': API_KEY,
    }
    
    # Create signature
    signature = create_cloudinary_signature(params, API_SECRET)
    params['signature'] = signature
    
    try:
        url = f'https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload'
        
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {k: v for k, v in params.items() if k != 'file'}
            
            response = requests.post(url, data=data, files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return True, result.get('secure_url')
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    
    except Exception as e:
        return False, str(e)

class NotionClient:
    """Simple Notion API client for fetching image metadata."""
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self.base_url = "https://api.notion.com/v1"
    
    def query_database(self) -> List[Dict]:
        """Query all base (non-holiday) rows from the gallery database."""
        results = []
        start_cursor = None
        page_count = 0
        
        print("📥 Fetching metadata from Notion database...")
        
        while True:
            page_count += 1
            print(f"   Fetching page {page_count}...", end=" ", flush=True)
            
            # Build request body  
            body = {
                "page_size": 100,
                "filter": {
                    "property": "Holiday",
                    "select": {
                        "is_empty": True  # Only base (non-holiday) images
                    }
                }
            }
            if start_cursor:
                body["start_cursor"] = start_cursor
            
            # Make request
            url = f"{self.base_url}/databases/{DATABASE_ID}/query"
            data = json.dumps(body).encode("utf-8")
            
            try:
                request = urllib.request.Request(url, data=data, headers=self.headers, method="POST")
                with urllib.request.urlopen(request, timeout=30) as response:
                    result = json.loads(response.read().decode())
            except urllib.error.HTTPError as e:
                print(f"\n❌ Notion API Error: {e.code}")
                print(f"   {e.read().decode()[:200]}")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                break
            
            # Parse results
            rows = result.get("results", [])
            print(f"got {len(rows)} rows")
            
            for row in rows:
                parsed = self._parse_row(row)
                if parsed:
                    results.append(parsed)
            
            # Check for more pages
            if not result.get("has_more"):
                break
            start_cursor = result.get("next_cursor")
        
        print(f"✅ Fetched metadata for {len(results)} images")
        return results
    
    def _parse_row(self, row: Dict) -> Optional[Dict]:
        """Parse Notion row into image metadata."""
        try:
            props = row.get("properties", {})
            
            # Get name/title
            name_prop = props.get("Name", {})
            title = ""
            if name_prop.get("title"):
                title = "".join(t.get("plain_text", "") for t in name_prop["title"])
            
            # Get style notes to determine folder
            style_notes_prop = props.get("Style Notes", {})
            style_notes = ""
            if style_notes_prop.get("rich_text"):
                style_notes = "".join(t.get("plain_text", "") for t in style_notes_prop["rich_text"])
            
            # Get other properties
            weather_prop = props.get("Weather", {})
            weather = weather_prop.get("select", {}).get("name", "")
            
            time_prop = props.get("Time of Day", {})
            time_of_day = time_prop.get("select", {}).get("name", "")
            
            activity_prop = props.get("Activity", {})
            activity = activity_prop.get("select", {}).get("name", "")
            
            location_prop = props.get("Location", {})
            location = ""
            if location_prop.get("rich_text"):
                location = "".join(t.get("plain_text", "") for t in location_prop["rich_text"])
            
            row_number_prop = props.get("Row Number", {})
            row_number = row_number_prop.get("number")
            
            verified_prop = props.get("Verified", {})
            verified = verified_prop.get("checkbox", False)
            
            return {
                "notion_id": row.get("id"),
                "name": title,
                "style_notes": style_notes,
                "weather": weather,
                "time_of_day": time_of_day,
                "activity": activity,
                "location": location,
                "row_number": row_number,
                "verified": verified
            }
        except Exception as e:
            print(f"⚠️ Error parsing row: {e}")
            return None

class ProductionUploader:
    """Production uploader for the complete gallery."""
    
    def __init__(self):
        self.notion_client = NotionClient()
        self.upload_log = []
        self.cloudinary_urls = {}
        self.start_time = datetime.now()
        
        # Change to project root
        os.chdir(Path(__file__).parent)
    
    def get_valid_images(self) -> List[str]:
        """Get list of valid image files, excluding Purim orphans."""
        gallery_path = Path.home() / "alice-gallery-images"
        if not gallery_path.exists():
            raise FileNotFoundError(f"Gallery directory not found: {gallery_path}")
        
        all_images = list(gallery_path.glob("*.png"))
        valid_images = []
        
        for img_path in all_images:
            filename = img_path.name
            
            # Skip if matches exclude patterns
            if any(pattern in filename for pattern in EXCLUDE_PATTERNS):
                continue
            
            valid_images.append(str(img_path))
        
        print(f"📁 Found {len(valid_images)} valid images (excluded {len(all_images) - len(valid_images)} Purim/orphan files)")
        return valid_images
    
    def determine_folder(self, style_notes: str) -> str:
        """Determine Cloudinary folder based on style notes."""
        if "pixel art" in style_notes.lower() or "pixel-art" in style_notes.lower():
            return "alice-gallery/pixel-art"
        else:
            return "alice-gallery/anime"  # Default to anime
    
    def find_image_metadata(self, image_path: str, notion_data: List[Dict]) -> Optional[Dict]:
        """Find metadata for an image by matching filename patterns."""
        filename = Path(image_path).stem
        
        # Try to extract row number from filename
        parts = filename.split("_")
        if parts and parts[0].isdigit():
            row_number = int(parts[0])
            
            # Find matching row in Notion data
            for item in notion_data:
                if item.get("row_number") == row_number:
                    return item
        
        # Secondary matching by name patterns
        filename_lower = filename.lower()
        for item in notion_data:
            name_parts = item.get("name", "").lower().split()
            if len(name_parts) >= 2:
                activity = name_parts[1] if len(name_parts) > 1 else ""
                if activity and activity in filename_lower:
                    return item
        
        return None
    
    def upload_batch(self, start_index=0, batch_size=50):
        """Upload a batch of images."""
        print(f"🚀 Starting Batch Upload (Starting at index {start_index})")
        print(f"☁️  Target: {CLOUD_NAME}")
        print("=" * 60)
        
        # Get valid images and Notion metadata
        valid_images = self.get_valid_images()
        if start_index >= len(valid_images):
            print("❌ Start index beyond available images")
            return
        
        # Slice for this batch
        batch_images = valid_images[start_index:start_index + batch_size]
        
        notion_data = self.notion_client.query_database()
        if not notion_data:
            raise Exception("Failed to fetch Notion metadata")
        
        success_count = 0
        failed_count = 0
        
        print(f"\n📤 Uploading batch: {len(batch_images)} images (indices {start_index}-{start_index + len(batch_images) - 1})")
        
        for i, image_path in enumerate(batch_images):
            global_index = start_index + i + 1
            filename = Path(image_path).stem
            
            # Find metadata for this image
            metadata = self.find_image_metadata(image_path, notion_data)
            if not metadata:
                print(f"⚠️  {global_index:3d}: {filename} - No metadata found, skipping")
                failed_count += 1
                continue
            
            # Determine folder and public_id
            folder = self.determine_folder(metadata.get("style_notes", ""))
            public_id = filename
            
            print(f"📤 {global_index:3d}: {filename}")
            print(f"     Activity: {metadata.get('activity', 'N/A')} | Weather: {metadata.get('weather', 'N/A')} | Time: {metadata.get('time_of_day', 'N/A')}")
            
            # Upload to Cloudinary
            success, result = upload_to_cloudinary(image_path, folder, public_id)
            
            # Log result
            log_entry = {
                "global_index": global_index,
                "filename": filename,
                "image_path": image_path,
                "notion_id": metadata.get("notion_id"),
                "folder": folder,
                "public_id": public_id,
                "success": success,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata
            }
            self.upload_log.append(log_entry)
            
            if success:
                print(f"     ✅ Success: {result}")
                self.cloudinary_urls[filename] = result
                success_count += 1
            else:
                print(f"     ❌ Failed: {result}")
                failed_count += 1
            
            # Rate limiting - ~7.2 seconds per upload = 500/hour
            time.sleep(7.2)
            
            # Progress updates every 10 images
            if (i + 1) % 10 == 0:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                print(f"\n📊 Batch Progress: {i + 1}/{len(batch_images)} images")
                print(f"✅ Success: {success_count}, ❌ Failed: {failed_count}")
                print(f"⏱️  Elapsed: {elapsed/60:.1f} minutes")
                print("-" * 50)
        
        # Save results
        self.save_results(start_index, batch_size, success_count, failed_count)
        
        return {
            "batch_start": start_index,
            "batch_size": len(batch_images),
            "success_count": success_count,
            "failed_count": failed_count,
            "cloudinary_urls": self.cloudinary_urls
        }
    
    def save_results(self, start_index, batch_size, success_count, failed_count):
        """Save upload results."""
        # Save upload log
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"upload_log_batch_{start_index}_{timestamp}.json"
        
        with open(log_filename, 'w') as f:
            json.dump(self.upload_log, f, indent=2)
        
        # Save/update cloudinary URLs mapping
        os.makedirs("data", exist_ok=True)
        urls_file = Path("data/cloudinary-urls.json")
        
        # Load existing URLs if they exist
        existing_urls = {}
        if urls_file.exists():
            with open(urls_file) as f:
                existing_urls = json.load(f)
        
        # Merge with new URLs
        existing_urls.update(self.cloudinary_urls)
        
        with open(urls_file, 'w') as f:
            json.dump(existing_urls, f, indent=2)
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n🎉 BATCH COMPLETE!")
        print(f"✅ Successful uploads: {success_count}")
        print(f"❌ Failed uploads: {failed_count}")
        print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
        print(f"📝 Batch log: {log_filename}")
        print(f"📁 URL mapping: {urls_file} ({len(existing_urls)} total URLs)")

def main():
    """Main entry point for production upload."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload Alice Gallery to Cloudinary")
    parser.add_argument("--start", type=int, default=0, help="Start index for upload")
    parser.add_argument("--batch", type=int, default=50, help="Batch size")
    parser.add_argument("--test", action="store_true", help="Test mode (upload first 5 images)")
    args = parser.parse_args()
    
    try:
        uploader = ProductionUploader()
        
        if args.test:
            print("🧪 TEST MODE - Uploading first 5 images")
            result = uploader.upload_batch(start_index=0, batch_size=5)
        else:
            result = uploader.upload_batch(start_index=args.start, batch_size=args.batch)
        
        print(f"\n📈 Final Results:")
        print(f"   Batch: {result['batch_start']}-{result['batch_start'] + result['batch_size'] - 1}")
        print(f"   Successful: {result['success_count']}")
        print(f"   Failed: {result['failed_count']}")
        print(f"   Total URLs: {len(result['cloudinary_urls'])}")
        
        if result['success_count'] > 0:
            print(f"\n✅ Batch uploaded successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()