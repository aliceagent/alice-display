#!/usr/bin/env python3
"""
Export Alice Gallery Notion DB to image-database.json for the display system.
Merges Notion metadata with Cloudinary URLs from data/cloudinary-urls.json.

Usage:
    python scripts/export_gallery.py                    # Full export
    python scripts/export_gallery.py --cloudinary-only  # Only images with Cloudinary URLs
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Notion Configuration
DATABASE_ID = "2fc41906-4d30-8189-a748-c6b715faf485"
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_VERSION = "2022-06-28"  # NEVER use 2025-09-03

def query_notion_pages(filter_body=None):
    """Paginate through all matching Notion DB rows."""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    
    all_results = []
    cursor = None
    page = 0
    
    while True:
        page += 1
        body = {"page_size": 100}
        if filter_body:
            body["filter"] = filter_body
        if cursor:
            body["start_cursor"] = cursor
        
        print(f"  Fetching page {page}...", end=" ", flush=True)
        
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f"ERROR: {e}")
            break
        
        rows = data.get("results", [])
        print(f"got {len(rows)} rows")
        all_results.extend(rows)
        
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    
    return all_results


def parse_row(row):
    """Parse a Notion row into a clean image metadata dict."""
    props = row.get("properties", {})
    
    # Title / Name
    name = ""
    name_prop = props.get("Name", {}).get("title", [])
    if name_prop:
        name = "".join(t.get("plain_text", "") for t in name_prop)
    
    # Row Number
    row_number = props.get("Row Number", {}).get("number")
    
    # Skip row 999 (tech spec)
    if row_number == 999:
        return None
    
    # Weather (select)
    weather = ""
    weather_sel = props.get("Weather", {}).get("select")
    if weather_sel:
        weather = weather_sel.get("name", "")
    
    # Time of Day (select)
    time_of_day = ""
    tod_sel = props.get("Time of Day", {}).get("select")
    if tod_sel:
        time_of_day = tod_sel.get("name", "")
    
    # Activity (select)
    activity = ""
    act_sel = props.get("Activity", {}).get("select")
    if act_sel:
        activity = act_sel.get("name", "")
    
    # Location (rich_text)
    location = ""
    loc_rt = props.get("Location", {}).get("rich_text", [])
    if loc_rt:
        location = "".join(t.get("plain_text", "") for t in loc_rt)
    
    # Style Notes (rich_text)
    style_notes = ""
    sn_rt = props.get("Style Notes", {}).get("rich_text", [])
    if sn_rt:
        style_notes = "".join(t.get("plain_text", "") for t in sn_rt)
    
    # Holiday (select)
    holiday = ""
    hol_sel = props.get("Holiday", {}).get("select")
    if hol_sel:
        holiday = hol_sel.get("name", "")
    
    # Verified (checkbox)
    verified = props.get("Verified", {}).get("checkbox", False)
    
    # Generated (checkbox)
    generated = props.get("Generated", {}).get("checkbox", False)
    
    # Build filename (matching generator's naming convention)
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    if row_number is not None:
        filename = f"{int(row_number):03d}_{safe_name}"
    else:
        filename = safe_name
    
    return {
        "id": row.get("id"),
        "name": name,
        "filename": filename,
        "row_number": row_number,
        "weather": weather,
        "time_period": time_of_day,
        "activity": activity,
        "location": location[:200],  # Truncate long locations
        "style_notes": style_notes[:200],
        "holiday": holiday,
        "verified": verified,
        "generated": generated,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Export Alice Gallery to image-database.json")
    parser.add_argument("--cloudinary-only", action="store_true",
                        help="Only include images that have Cloudinary URLs")
    parser.add_argument("--output", default="data/image-database.json",
                        help="Output file path")
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("📥 Exporting Alice Gallery from Notion...")
    
    # Query all base (non-holiday) verified rows
    print("  Fetching base (non-holiday) images...")
    base_rows = query_notion_pages({
        "and": [
            {"property": "Holiday", "select": {"is_empty": True}},
            {"property": "Verified", "checkbox": {"equals": True}},
        ]
    })
    
    # Also fetch verified holiday images
    print("  Fetching verified holiday images...")
    holiday_rows = query_notion_pages({
        "and": [
            {"property": "Holiday", "select": {"is_not_empty": True}},
            {"property": "Verified", "checkbox": {"equals": True}},
        ]
    })
    
    all_rows = base_rows + holiday_rows
    print(f"✅ Total verified rows: {len(all_rows)}")
    
    # Parse all rows
    images = []
    for row in all_rows:
        parsed = parse_row(row)
        if parsed:
            images.append(parsed)
    
    print(f"📊 Parsed {len(images)} image records")
    
    # Load Cloudinary URL mapping
    urls_file = Path("data/cloudinary-urls.json")
    cloudinary_urls = {}
    if urls_file.exists():
        with open(urls_file) as f:
            cloudinary_urls = json.load(f)
        print(f"☁️  Loaded {len(cloudinary_urls)} Cloudinary URLs")
    
    # Merge Cloudinary URLs into image records
    matched = 0
    for img in images:
        filename = img["filename"]
        if filename in cloudinary_urls:
            img["cloudinary_url"] = cloudinary_urls[filename]
            matched += 1
        # Also try without row number prefix
        bare_name = re.sub(r'^\d{3}_', '', filename)
        if bare_name in cloudinary_urls and "cloudinary_url" not in img:
            img["cloudinary_url"] = cloudinary_urls[bare_name]
            matched += 1
    
    print(f"🔗 Matched {matched} images with Cloudinary URLs")
    
    # Filter to cloudinary-only if requested
    if args.cloudinary_only:
        images = [img for img in images if img.get("cloudinary_url")]
        print(f"☁️  Filtered to {len(images)} images with Cloudinary URLs")
    
    # Add local fallback URLs for images without Cloudinary
    for img in images:
        if "cloudinary_url" not in img:
            img["url"] = f"images/generated/{img['filename']}.png"
    
    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(images, f, indent=2)
    
    print(f"💾 Saved {len(images)} images to {output_path}")
    
    # Stats
    weather_counts = {}
    time_counts = {}
    for img in images:
        w = img.get("weather", "Unknown")
        t = img.get("time_period", "Unknown")
        weather_counts[w] = weather_counts.get(w, 0) + 1
        time_counts[t] = time_counts.get(t, 0) + 1
    
    print(f"\n📊 Weather distribution: {json.dumps(weather_counts)}")
    print(f"📊 Time distribution: {json.dumps(time_counts)}")
    
    with_urls = sum(1 for img in images if img.get("cloudinary_url"))
    print(f"☁️  {with_urls}/{len(images)} have Cloudinary URLs")


if __name__ == "__main__":
    main()
