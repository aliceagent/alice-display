#!/usr/bin/env python3
"""
Bulk Cloudinary Uploader for Alice Gallery.
Uploads all verified base images to Cloudinary CDN.

Uses the CORRECT Cloudinary signature method:
  hashlib.sha1( "param1=val1&param2=val2" + api_secret )

Tracks progress in data/cloudinary-urls.json so it can resume
if interrupted. Only uploads images not already in the URL map.

Usage:
    python bulk_upload.py                  # Upload all missing images
    python bulk_upload.py --dry-run        # Preview what would be uploaded
    python bulk_upload.py --limit 10       # Upload max 10 images
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ─── Cloudinary Configuration ───────────────────────────────────────
# These are read from environment variables with fallbacks.
# The API secret is required for signature generation.
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "dfzowmhfp")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "965349664584469")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "iKIDovK2zXK_7KeOVsqN0tinmpY")

# ─── Paths ──────────────────────────────────────────────────────────
GALLERY_DIR = Path.home() / "alice-gallery-images"
PROJECT_ROOT = Path(__file__).parent
URLS_FILE = PROJECT_ROOT / "data" / "cloudinary-urls.json"
DB_FILE = PROJECT_ROOT / "data" / "image-database.json"


def create_signature(params: dict, api_secret: str) -> str:
    """
    Create Cloudinary upload signature.
    
    Cloudinary's required format:
      1. Take all params EXCEPT api_key and file
      2. Sort alphabetically by key
      3. Join as "key1=val1&key2=val2"
      4. Append the API secret (no separator)
      5. SHA-1 hash the result
    """
    # Filter out api_key and file — they're not part of the signature
    sign_params = {k: v for k, v in params.items() if k not in ("api_key", "file")}
    
    # Sort alphabetically and join
    sorted_items = sorted(sign_params.items())
    params_string = "&".join(f"{k}={v}" for k, v in sorted_items)
    
    # Append secret and hash
    string_to_sign = f"{params_string}{api_secret}"
    return hashlib.sha1(string_to_sign.encode("utf-8")).hexdigest()


def upload_one(image_path: str, folder: str, public_id: str) -> tuple:
    """
    Upload a single image to Cloudinary.
    
    Returns:
        (success: bool, result: str)  — result is URL on success, error on failure
    """
    timestamp = int(time.time())
    
    # Build params (api_key included for the POST but excluded from signature)
    params = {
        "timestamp": timestamp,
        "folder": folder,
        "public_id": public_id,
        "api_key": API_KEY,
    }
    
    # Generate correct signature
    signature = create_signature(params, API_SECRET)
    
    # Build multipart form data manually (no requests dependency)
    boundary = f"----CloudinaryBoundary{timestamp}"
    
    # All form fields
    fields = {
        "timestamp": str(timestamp),
        "folder": folder,
        "public_id": public_id,
        "api_key": API_KEY,
        "signature": signature,
    }
    
    # Build multipart body
    body_parts = []
    for key, value in fields.items():
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body_parts.append(f"{value}\r\n".encode())
    
    # Add file
    filename = Path(image_path).name
    with open(image_path, "rb") as f:
        file_data = f.read()
    
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body_parts.append(b"Content-Type: image/png\r\n\r\n")
    body_parts.append(file_data)
    body_parts.append(b"\r\n")
    body_parts.append(f"--{boundary}--\r\n".encode())
    
    body = b"".join(body_parts)
    
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/image/upload"
    
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            secure_url = result.get("secure_url", "")
            return True, secure_url
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")[:200]
        return False, f"HTTP {e.code}: {error_body}"
    except Exception as e:
        return False, str(e)


def load_url_map() -> dict:
    """Load existing Cloudinary URL mapping."""
    if URLS_FILE.exists():
        with open(URLS_FILE) as f:
            return json.load(f)
    return {}


def save_url_map(url_map: dict) -> None:
    """Save Cloudinary URL mapping (atomic write)."""
    URLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = URLS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(url_map, f, indent=2)
    tmp.rename(URLS_FILE)


def get_upload_list(url_map: dict) -> list:
    """
    Build list of images that need uploading.
    Scans the gallery directory for all .png files,
    skips any already in the URL map.
    """
    if not GALLERY_DIR.exists():
        print(f"❌ Gallery directory not found: {GALLERY_DIR}")
        return []
    
    all_pngs = sorted(GALLERY_DIR.glob("*.png"))
    
    # Skip rejected/ subdirectory images
    to_upload = []
    for png in all_pngs:
        stem = png.stem
        if stem in url_map:
            continue  # Already uploaded
        to_upload.append(png)
    
    return to_upload


def determine_folder(filename: str) -> str:
    """
    Determine Cloudinary folder based on image type.
    Holiday images go to alice-gallery/holiday/
    Pixel art images go to alice-gallery/pixel-art/
    Everything else goes to alice-gallery/anime/
    """
    lower = filename.lower()
    
    # Holiday images have holiday names in them
    holiday_keywords = [
        "purim", "shushan", "pesach", "passover",
        "shoah", "zikaron", "atzmaut", "omer",
        "sukkot", "shavuot", "rosh_hashana", "kippur",
        "chanukah", "hanukkah", "tu_bishvat",
    ]
    for kw in holiday_keywords:
        if kw in lower:
            return "alice-gallery/holiday"
    
    # Pixel art images
    pixel_keywords = [
        "pixel", "catching_snowflakes", "hot_cocoa_outside",
        "baking_-_", "playing_piano_-_", "flower_picking_-_",
        "park_walk_-_", "snowman_building_-_", "yoga_-_",
        "gaming_-_cloudy", "gaming_-_sunny", "gaming_-_rainy",
    ]
    for kw in pixel_keywords:
        if kw in lower:
            return "alice-gallery/pixel-art"
    
    return "alice-gallery/anime"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bulk upload Alice Gallery to Cloudinary")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--limit", type=int, default=0, help="Max images to upload (0=all)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between uploads")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🦜 Alice Gallery — Bulk Cloudinary Upload")
    print("=" * 60)
    
    # Load existing URL map
    url_map = load_url_map()
    print(f"📦 Existing Cloudinary URLs: {len(url_map)}")
    
    # Get list of images needing upload
    to_upload = get_upload_list(url_map)
    print(f"📤 Images to upload: {len(to_upload)}")
    
    if not to_upload:
        print("✅ All images already uploaded!")
        return
    
    if args.limit:
        to_upload = to_upload[:args.limit]
        print(f"📤 Limited to: {args.limit}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN — would upload:")
        for i, png in enumerate(to_upload[:20], 1):
            folder = determine_folder(png.stem)
            print(f"  {i}. {png.stem} → {folder}")
        if len(to_upload) > 20:
            print(f"  ... and {len(to_upload) - 20} more")
        return
    
    # Upload loop
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    for i, png in enumerate(to_upload, 1):
        folder = determine_folder(png.stem)
        public_id = png.stem
        
        elapsed = time.time() - start_time
        rate = success_count / max(elapsed, 1) * 60  # per minute
        
        print(f"\n📤 [{i}/{len(to_upload)}] {png.stem}")
        print(f"   Folder: {folder} | Elapsed: {elapsed:.0f}s | Rate: {rate:.1f}/min")
        
        ok, result = upload_one(str(png), folder, public_id)
        
        if ok:
            success_count += 1
            url_map[png.stem] = result
            print(f"   ✅ {result[:80]}...")
            
            # Save progress every 10 uploads (atomic write)
            if success_count % 10 == 0:
                save_url_map(url_map)
                print(f"   💾 Saved progress ({len(url_map)} URLs)")
        else:
            fail_count += 1
            print(f"   ❌ {result}")
            
            # If we get 3 consecutive failures, something is wrong — abort
            if fail_count >= 3 and success_count == 0:
                print("\n🚨 3 consecutive failures with 0 successes — aborting!")
                print("   Check API credentials and signature method.")
                break
        
        # Rate limiting
        if i < len(to_upload):
            time.sleep(args.delay)
    
    # Final save
    save_url_map(url_map)
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"📊 Upload Complete")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   📦 Total Cloudinary URLs: {len(url_map)}")
    print(f"   ⏱️  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print("=" * 60)


if __name__ == "__main__":
    main()
