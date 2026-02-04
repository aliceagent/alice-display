#!/usr/bin/env python3
"""
Gallery Uploader for Alice Display Integration
Uploads 509 verified base images from ~/alice-gallery-images/ to Cloudinary.

Excludes Purim orphan files and 2026- prefixed files.
Organizes by style (anime vs pixel-art) based on Notion metadata.
"""

import os
import sys
import json
import time
import hashlib
import hmac
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
NOTION_VERSION = "2022-06-28"  # Explicitly using 2022-06-28, NOT 2025-09-03

# File patterns to exclude
EXCLUDE_PATTERNS = [
    "Alice_Attending_Lively_Purim",
    "Alice_Reading_Megillah",
    "2026-"
]


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
                print(f"   {e.read().decode()}")
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

            path_prop = props.get("Path", {})
            path = ""
            if path_prop.get("rich_text"):
                path = "".join(t.get("plain_text", "") for t in path_prop["rich_text"])

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
                "path": path,
                "row_number": row_number,
                "verified": verified
            }
        except Exception as e:
            print(f"⚠️ Error parsing row: {e}")
            return None


class CloudinaryUploader:
    """Handles uploading images to Cloudinary with proper organization."""

    def create_signature(self, params: Dict, api_secret: str) -> str:
        """Create Cloudinary API signature."""
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

    def upload_image(self, image_path: str, public_id: str, folder: str) -> Tuple[bool, str]:
        """Upload single image to Cloudinary."""
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
        signature = self.create_signature(params, API_SECRET)

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


class GalleryUploader:
    """Main uploader class that coordinates the upload process."""

    def __init__(self):
        self.notion_client = NotionClient()
        self.cloudinary_uploader = CloudinaryUploader()
        self.upload_log = []
        self.cloudinary_urls = {}

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
        filename = Path(image_path).stem  # Get filename without extension

        # Try to extract row number from filename
        parts = filename.split("_")
        if parts and parts[0].isdigit():
            row_number = int(parts[0])

            # Find matching row in Notion data
            for item in notion_data:
                if item.get("row_number") == row_number:
                    return item

        # Fallback: try to match by activity/weather/time patterns in filename
        # This is more complex matching for files without clear row numbers
        filename_lower = filename.lower()

        for item in notion_data:
            # Check if key components match
            name_parts = item.get("name", "").lower().split()
            if len(name_parts) >= 2:
                activity = name_parts[1] if len(name_parts) > 1 else ""
                if activity and activity in filename_lower:
                    return item

        return None

    def upload_gallery(self) -> Dict:
        """Upload all valid gallery images to Cloudinary."""
        print("🚀 Starting Gallery Upload to Cloudinary")
        print(f"☁️  Target: {CLOUD_NAME}")
        print("=" * 60)

        # Get valid images and Notion metadata
        valid_images = self.get_valid_images()
        notion_data = self.notion_client.query_database()

        if not notion_data:
            raise Exception("Failed to fetch Notion metadata")

        success_count = 0
        failed_count = 0

        print(f"\n📤 Starting upload of {len(valid_images)} images...")

        for i, image_path in enumerate(valid_images, 1):
            filename = Path(image_path).stem

            # Find metadata for this image
            metadata = self.find_image_metadata(image_path, notion_data)
            if not metadata:
                print(f"⚠️  {i:3d}: {filename} - No metadata found, skipping")
                failed_count += 1
                continue

            # Determine folder and public_id
            folder = self.determine_folder(metadata.get("style_notes", ""))
            public_id = filename  # Use filename as public_id

            print(f"📤 {i:3d}: Uploading {filename}...")
            print(f"     Folder: {folder}")
            print(f"     Activity: {metadata.get('activity', 'N/A')}")
            print(f"     Weather: {metadata.get('weather', 'N/A')} / {metadata.get('time_of_day', 'N/A')}")

            # Upload to Cloudinary
            success, result = self.cloudinary_uploader.upload_image(image_path, public_id, folder)

            # Log result
            log_entry = {
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

            # Rate limiting - be gentle with Cloudinary free tier
            time.sleep(7.5)  # ~480 uploads per hour (under 500 limit)

            # Progress updates every 50 images
            if i % 50 == 0:
                print(f"\n📊 Progress: {i}/{len(valid_images)} images")
                print(f"✅ Success: {success_count}, ❌ Failed: {failed_count}")
                print(f"⏱️  Estimated remaining: {(len(valid_images) - i) * 7.5 / 60:.1f} minutes")
                print("-" * 60)

        # Save upload log
        log_filename = f"gallery_upload_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_filename, 'w') as f:
            json.dump(self.upload_log, f, indent=2)

        # Save cloudinary URLs mapping
        os.makedirs("data", exist_ok=True)
        with open("data/cloudinary-urls.json", 'w') as f:
            json.dump(self.cloudinary_urls, f, indent=2)

        print(f"\n🎉 GALLERY UPLOAD COMPLETE!")
        print(f"✅ Successful uploads: {success_count}")
        print(f"❌ Failed uploads: {failed_count}")
        print(f"📝 Upload log: {log_filename}")
        print(f"📁 URL mapping: data/cloudinary-urls.json")

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total_attempted": len(valid_images),
            "cloudinary_urls": self.cloudinary_urls,
            "log_file": log_filename
        }


def main():
    """Main entry point."""
    try:
        uploader = GalleryUploader()
        result = uploader.upload_gallery()

        print(f"\n📈 Final Stats:")
        print(f"   Attempted: {result['total_attempted']}")
        print(f"   Successful: {result['success_count']}")
        print(f"   Failed: {result['failed_count']}")
        print(f"   Success Rate: {result['success_count']/result['total_attempted']*100:.1f}%")

        if result['success_count'] > 0:
            print(f"\n✅ Upload completed successfully!")
            print(f"📁 {result['success_count']} images now available on Cloudinary")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()