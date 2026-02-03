#!/usr/bin/env python3
"""
Update Image Database with Cloudinary URLs

Scans the generated images directory and updates the image database
with Cloudinary URLs for each generated image.

Usage:
    python update_database_urls.py                    # Upload and update
    python update_database_urls.py --local            # Use local paths only
    python update_database_urls.py --dry-run          # Preview changes
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_local_images(images_dir: Path) -> dict:
    """Scan local images directory and return mapping."""
    images = {}
    
    for img_file in images_dir.glob("*.png"):
        # Extract weather-time from filename
        name = img_file.stem.lower()
        images[name] = {
            "path": str(img_file),
            "filename": img_file.name,
            "size": img_file.stat().st_size,
        }
    
    return images


def match_image_to_database(img_name: str, db_entries: list) -> dict:
    """Try to match an image filename to a database entry."""
    
    # Parse the image name for weather/time info
    parts = img_name.lower().replace("-", " ").split()
    
    for entry in db_entries:
        entry_weather = entry.get("weather", "").lower()
        entry_time = entry.get("time_period", "").lower()
        
        # Check if weather and time are in the filename
        weather_match = entry_weather in img_name.lower() or any(
            w in img_name.lower() for w in entry_weather.split()
        )
        time_match = entry_time in img_name.lower() or any(
            t in img_name.lower() for t in entry_time.split()
        )
        
        if weather_match and time_match:
            return entry
    
    return None


def update_database_with_urls(
    database_path: Path,
    images_dir: Path,
    cloudinary_base_url: str = None,
    dry_run: bool = False
) -> dict:
    """Update database entries with image URLs."""
    
    # Load database
    with open(database_path) as f:
        data = json.load(f)
    
    images_list = data.get("images", data) if isinstance(data, dict) else data
    
    # Get local images
    local_images = get_local_images(images_dir)
    print(f"📁 Found {len(local_images)} local images")
    
    # Track updates
    updates = []
    
    for img_name, img_info in local_images.items():
        matched = match_image_to_database(img_name, images_list)
        
        if matched:
            # Generate URL
            if cloudinary_base_url:
                url = f"{cloudinary_base_url}/{img_info['filename']}"
            else:
                url = f"images/generated/{img_info['filename']}"
            
            updates.append({
                "image_name": img_name,
                "matched_title": matched.get("title"),
                "matched_id": matched.get("id"),
                "url": url,
            })
            
            if not dry_run:
                matched["cloudinary_url"] = url
                matched["generated"] = True
    
    if dry_run:
        print("\n🔍 DRY RUN - Would update:")
        for u in updates:
            print(f"  - {u['matched_title']}: {u['url']}")
    else:
        # Save updated database
        if isinstance(data, dict):
            data["images"] = images_list
            data["last_updated"] = datetime.now().isoformat()
        
        with open(database_path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✅ Updated {len(updates)} database entries")
    
    return {
        "total_images": len(local_images),
        "matched": len(updates),
        "updates": updates,
    }


def main():
    parser = argparse.ArgumentParser(description="Update database with image URLs")
    parser.add_argument("--database", type=str, default="data/image-database.json")
    parser.add_argument("--images-dir", type=str, default="images/generated")
    parser.add_argument("--cloudinary-base", type=str, help="Cloudinary base URL")
    parser.add_argument("--local", action="store_true", help="Use local paths only")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    args = parser.parse_args()
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent)
    
    database_path = Path(args.database)
    images_dir = Path(args.images_dir)
    
    if not database_path.exists():
        print(f"❌ Database not found: {database_path}")
        sys.exit(1)
    
    if not images_dir.exists():
        print(f"❌ Images directory not found: {images_dir}")
        sys.exit(1)
    
    cloudinary_base = None if args.local else args.cloudinary_base
    
    result = update_database_with_urls(
        database_path=database_path,
        images_dir=images_dir,
        cloudinary_base_url=cloudinary_base,
        dry_run=args.dry_run,
    )
    
    print(f"\n📊 Summary:")
    print(f"   Local images: {result['total_images']}")
    print(f"   Matched to DB: {result['matched']}")


if __name__ == "__main__":
    main()
