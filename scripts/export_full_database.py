#!/usr/bin/env python3
"""
Enhanced Export Notion Database Script
Exports the complete gallery database with Cloudinary URLs integration.

Usage:
    python export_full_database.py                    # Export all verified base rows
    python export_full_database.py --include-unverified # Include unverified rows too
    python export_full_database.py --validate         # Validate export completeness
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict

# Notion Configuration
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "2fc41906-4d30-8189-a748-c6b715faf485")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "YOUR_NOTION_KEY_HERE")
NOTION_VERSION = "2022-06-28"


class EnhancedNotionExporter:
    """Enhanced exporter with Cloudinary URL integration."""
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self.base_url = "https://api.notion.com/v1"
    
    def export_database(self, include_unverified=False) -> List[Dict]:
        """Export base (non-holiday) rows from the gallery database."""
        images = []
        start_cursor = None
        page_count = 0
        
        print(f"📥 Exporting from Notion database: {DATABASE_ID}")
        print(f"🎯 Mode: {'All rows' if include_unverified else 'Verified only'}")
        
        while True:
            page_count += 1
            print(f"   Fetching page {page_count}...", end=" ", flush=True)
            
            # Build request body with filter
            body = {
                "page_size": 100,
                "filter": {
                    "and": [
                        {
                            "property": "Holiday",
                            "select": {
                                "is_empty": True  # Only base (non-holiday) images
                            }
                        }
                    ]
                }
            }
            
            # Add verified filter if needed
            if not include_unverified:
                body["filter"]["and"].append({
                    "property": "Verified",
                    "checkbox": {
                        "equals": True
                    }
                })
            
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
                error_body = e.read().decode()
                print(f"   {error_body}")
                break
            except Exception as e:
                print(f"\n❌ Network Error: {e}")
                break
            
            # Parse results
            rows = result.get("results", [])
            print(f"got {len(rows)} rows")
            
            for row in rows:
                image = self._parse_row(row)
                if image:
                    images.append(image)
            
            # Check for more pages
            if not result.get("has_more"):
                break
            start_cursor = result.get("next_cursor")
        
        print(f"✅ Exported {len(images)} images")
        return images
    
    def _parse_row(self, row: Dict) -> Optional[Dict]:
        """Parse Notion database row into enhanced image format."""
        try:
            props = row.get("properties", {})
            
            # Extract title/name
            name_prop = props.get("Name", {})
            name = ""
            if name_prop.get("title"):
                name = "".join(t.get("plain_text", "") for t in name_prop["title"])
            
            # Extract all properties for the enhanced database
            full_description_prop = props.get("Full Description", {})
            full_description = ""
            if full_description_prop.get("rich_text"):
                full_description = "".join(t.get("plain_text", "") for t in full_description_prop["rich_text"])
            
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
            
            style_notes_prop = props.get("Style Notes", {})
            style_notes = ""
            if style_notes_prop.get("rich_text"):
                style_notes = "".join(t.get("plain_text", "") for t in style_notes_prop["rich_text"])
            
            props_prop = props.get("Props", {})
            props_text = ""
            if props_prop.get("rich_text"):
                props_text = "".join(t.get("plain_text", "") for t in props_prop["rich_text"])
            
            path_prop = props.get("Path", {})
            path = ""
            if path_prop.get("rich_text"):
                path = "".join(t.get("plain_text", "") for t in path_prop["rich_text"])
            
            row_number_prop = props.get("Row Number", {})
            row_number = row_number_prop.get("number")
            
            verified_prop = props.get("Verified", {})
            verified = verified_prop.get("checkbox", False)
            
            generated_prop = props.get("Generated", {})
            generated = generated_prop.get("checkbox", False)
            
            holiday_prop = props.get("Holiday", {})
            holiday = holiday_prop.get("select", {}).get("name", "") if holiday_prop.get("select") else ""
            
            # Build the enhanced image record
            image = {
                "id": row.get("id", "").replace("-", ""),  # Clean ID for compatibility
                "notion_id": row.get("id"),
                "name": name,
                "full_description": full_description,
                "weather": weather,
                "time_of_day": time_of_day,
                "activity": activity,
                "location": location,
                "style_notes": style_notes,
                "props": props_text,
                "path": path,
                "row_number": row_number,
                "verified": verified,
                "generated": generated,
                "holiday": holiday,
                # These will be added by the integration process
                "cloudinary_url": None,
                "filename": None,
            }
            
            # Clean up None values except for cloudinary_url and filename
            image = {k: v for k, v in image.items() if v is not None or k in ['cloudinary_url', 'filename']}
            
            return image
            
        except Exception as e:
            print(f"⚠️ Error parsing row: {e}")
            return None
    
    def integrate_cloudinary_urls(self, images: List[Dict]) -> List[Dict]:
        """Integrate Cloudinary URLs from the mapping file."""
        print("\n🔗 Integrating Cloudinary URLs...")
        
        urls_file = Path("data/cloudinary-urls.json")
        if not urls_file.exists():
            print(f"   ⚠️ Cloudinary URLs file not found: {urls_file}")
            return images
        
        try:
            with open(urls_file) as f:
                cloudinary_urls = json.load(f)
            print(f"   📁 Loaded {len(cloudinary_urls)} Cloudinary URLs")
        except Exception as e:
            print(f"   ❌ Error loading Cloudinary URLs: {e}")
            return images
        
        integrated_count = 0
        
        for image in images:
            # Try multiple methods to find the matching cloudinary URL
            
            # Method 1: Direct row number match
            if image.get("row_number"):
                row_num = image["row_number"]
                # Try various filename patterns
                potential_filenames = [
                    f"{row_num:03d}_{image.get('name', '').replace(' ', '_')}",
                    f"{row_num:03d}",
                    f"Alice_{image.get('activity', '')}_Row_{row_num:03d}",
                ]
                
                for filename in potential_filenames:
                    if filename in cloudinary_urls:
                        image["cloudinary_url"] = cloudinary_urls[filename]
                        image["filename"] = filename
                        integrated_count += 1
                        break
            
            # Method 2: Match by name pattern
            if not image.get("cloudinary_url"):
                name = image.get("name", "")
                activity = image.get("activity", "")
                weather = image.get("weather", "")
                time_of_day = image.get("time_of_day", "")
                
                for filename, url in cloudinary_urls.items():
                    # Check if filename contains key components
                    filename_lower = filename.lower()
                    if (activity.lower() in filename_lower and 
                        weather.lower() in filename_lower and
                        any(word.lower() in filename_lower for word in name.split()[:2])):
                        image["cloudinary_url"] = url
                        image["filename"] = filename
                        integrated_count += 1
                        break
        
        print(f"   ✅ Integrated {integrated_count}/{len(images)} Cloudinary URLs")
        return images

def validate_export(images: List[Dict]) -> Dict:
    """Validate the exported data for completeness."""
    print("\n📊 Validating Export...")
    
    weather_types = set()
    time_periods = set()
    activities = set()
    style_notes = set()
    
    missing_weather = []
    missing_time = []
    missing_activity = []
    with_cloudinary = 0
    verified_count = 0
    
    for img in images:
        weather = img.get("weather")
        time = img.get("time_of_day")
        activity = img.get("activity")
        style = img.get("style_notes")
        
        if weather:
            weather_types.add(weather)
        else:
            missing_weather.append(img.get("name", img.get("id")))
        
        if time:
            time_periods.add(time)
        else:
            missing_time.append(img.get("name", img.get("id")))
        
        if activity:
            activities.add(activity)
        else:
            missing_activity.append(img.get("name", img.get("id")))
        
        if style:
            style_notes.add(style)
        
        if img.get("cloudinary_url"):
            with_cloudinary += 1
        
        if img.get("verified"):
            verified_count += 1
    
    validation = {
        "total_images": len(images),
        "verified_images": verified_count,
        "with_cloudinary_url": with_cloudinary,
        "weather_types": sorted(weather_types),
        "time_periods": sorted(time_periods),
        "activities": sorted(activities),
        "style_notes": sorted(style_notes),
        "missing_weather": missing_weather[:5],  # First 5
        "missing_time": missing_time[:5],
        "missing_activity": missing_activity[:5],
        "coverage": {
            "has_weather": len(images) - len(missing_weather),
            "has_time": len(images) - len(missing_time),
            "has_activity": len(images) - len(missing_activity),
            "has_cloudinary": with_cloudinary,
        }
    }
    
    print(f"   Total images: {validation['total_images']}")
    print(f"   Verified: {verified_count}")
    print(f"   With Cloudinary URLs: {with_cloudinary}")
    print(f"   Weather types: {validation['weather_types']}")
    print(f"   Time periods: {validation['time_periods']}")
    print(f"   Activities: {validation['activities']}")
    
    if validation['missing_weather']:
        print(f"   ⚠️ Missing weather (first 5): {validation['missing_weather']}")
    if validation['missing_time']:
        print(f"   ⚠️ Missing time (first 5): {validation['missing_time']}")
    
    return validation

def main():
    parser = argparse.ArgumentParser(description="Export enhanced Alice gallery database")
    parser.add_argument("--output", type=str, default="data/image-database.json", 
                       help="Output file path")
    parser.add_argument("--include-unverified", action="store_true", 
                       help="Include unverified rows")
    parser.add_argument("--validate", action="store_true", 
                       help="Validate export and show detailed stats")
    args = parser.parse_args()
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent)
    
    try:
        exporter = EnhancedNotionExporter()
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        sys.exit(1)
    
    # Export database
    images = exporter.export_database(include_unverified=args.include_unverified)
    
    if not images:
        print("❌ No images exported")
        sys.exit(1)
    
    # Integrate Cloudinary URLs
    images = exporter.integrate_cloudinary_urls(images)
    
    # Validate if requested
    if args.validate:
        validation = validate_export(images)
        
        # Save validation results
        validation_path = Path("data/validation-results.json")
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validation_path, "w") as f:
            json.dump(validation, f, indent=2)
        print(f"   📁 Validation saved: {validation_path}")
    
    # Save database
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    database = {
        "images": images,
        "exported_at": __import__("datetime").datetime.now().isoformat(),
        "total_images": len(images),
        "cloudinary_integration": sum(1 for img in images if img.get("cloudinary_url")),
        "export_config": {
            "include_unverified": args.include_unverified,
            "database_id": DATABASE_ID,
            "api_version": NOTION_VERSION
        }
    }
    
    with open(output_path, "w") as f:
        json.dump(database, f, indent=2)
    
    print(f"\n📁 Enhanced database saved: {output_path}")
    print(f"   Total images: {len(images)}")
    print(f"   With Cloudinary URLs: {sum(1 for img in images if img.get('cloudinary_url'))}")
    print(f"   Export size: {output_path.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()