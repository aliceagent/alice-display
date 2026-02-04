#!/usr/bin/env python3
"""
Export Notion database to JSON for Alice Display System.

Usage:
    python export_notion.py                    # Export all rows
    python export_notion.py --limit 50         # Export first 50 rows
    python export_notion.py --validate         # Validate export completeness
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# Alice image database ID (from Notion)
DATABASE_ID = "2fc41906-4d30-8189-a748-c6b715faf485"
NOTION_VERSION = "2022-06-28"  # Using correct version, NOT 2025-09-03


class NotionExporter:
    """Exports Alice image database from Notion."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        if not self.api_key:
            # Try reading from config file
            config_path = Path.home() / ".config" / "notion" / "api_key"
            if config_path.exists():
                self.api_key = config_path.read_text().strip()
        
        if not self.api_key:
            raise ValueError("Notion API key required. Set NOTION_API_KEY or ~/.config/notion/api_key")
        
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
    
    def export_database(self, limit: int = None) -> list:
        """Export all rows from the Alice image database."""
        images = []
        start_cursor = None
        page_count = 0
        
        print(f"📥 Exporting from Notion database: {DATABASE_ID}")
        
        while True:
            page_count += 1
            print(f"   Fetching page {page_count}...", end=" ")
            
            # Build request body
            body = {"page_size": 100}
            if start_cursor:
                body["start_cursor"] = start_cursor
            
            # Make request
            url = f"{self.base_url}/databases/{DATABASE_ID}/query"
            data = json.dumps(body).encode("utf-8")
            
            request = urllib.request.Request(url, data=data, headers=self.headers, method="POST")
            
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    result = json.loads(response.read().decode())
            except urllib.error.HTTPError as e:
                print(f"\n❌ API Error: {e.code}")
                error_body = e.read().decode()
                print(f"   {error_body}")
                break
            except urllib.error.URLError as e:
                print(f"\n❌ Network Error: {e.reason}")
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
            
            # Check limit
            if limit and len(images) >= limit:
                images = images[:limit]
                break
        
        print(f"✅ Exported {len(images)} images")
        return images
    
    def _parse_row(self, row: dict) -> Optional[dict]:
        """Parse a Notion database row into our image format."""
        try:
            props = row.get("properties", {})
            
            # Extract title
            title = self._get_title(props)
            if not title:
                return None
            
            # Extract other properties
            image = {
                "id": row.get("id", "").replace("-", ""),
                "notion_id": row.get("id"),
                "title": title,
                "description": self._get_rich_text(props, "Description") or self._get_rich_text(props, "Detailed Image Description"),
                "weather": self._get_select(props, "Weather"),
                "time_period": self._get_select(props, "Time") or self._get_select(props, "Time of Day"),
                "activity": self._get_select(props, "Activity") or self._get_select(props, "Activity Type"),
                "sub_activity": self._get_rich_text(props, "Sub-Activity") or self._get_select(props, "Sub-Activity"),
                "location": self._get_rich_text(props, "Location") or self._get_select(props, "Location"),
                "mood": self._get_select(props, "Mood") or self._get_rich_text(props, "Mood"),
                "season": self._get_select(props, "Season"),
                "row_number": self._get_number(props, "Row") or self._get_number(props, "#"),
                "cloudinary_url": self._get_url(props, "Image URL") or self._get_url(props, "Cloudinary URL"),
                "generated": self._get_checkbox(props, "Generated"),
                "approved": self._get_checkbox(props, "Approved"),
                "style": self._get_select(props, "Style") or "Anime",
            }
            
            # Clean up None values
            image = {k: v for k, v in image.items() if v is not None}
            
            return image
            
        except Exception as e:
            print(f"⚠️ Error parsing row: {e}")
            return None
    
    def _get_title(self, props: dict) -> Optional[str]:
        """Extract title property."""
        for key in ["Name", "Title", "name", "title"]:
            if key in props:
                title_data = props[key].get("title", [])
                if title_data:
                    return "".join(t.get("plain_text", "") for t in title_data)
        return None
    
    def _get_rich_text(self, props: dict, key: str) -> Optional[str]:
        """Extract rich text property."""
        if key in props:
            text_data = props[key].get("rich_text", [])
            if text_data:
                return "".join(t.get("plain_text", "") for t in text_data)
        return None
    
    def _get_select(self, props: dict, key: str) -> Optional[str]:
        """Extract select property."""
        if key in props:
            select_data = props[key].get("select")
            if select_data:
                return select_data.get("name")
        return None
    
    def _get_number(self, props: dict, key: str) -> Optional[int]:
        """Extract number property."""
        if key in props:
            return props[key].get("number")
        return None
    
    def _get_checkbox(self, props: dict, key: str) -> Optional[bool]:
        """Extract checkbox property."""
        if key in props:
            return props[key].get("checkbox")
        return None
    
    def _get_url(self, props: dict, key: str) -> Optional[str]:
        """Extract URL property."""
        if key in props:
            return props[key].get("url")
        return None


def validate_export(images: list) -> dict:
    """Validate the exported data for completeness."""
    weather_types = set()
    time_periods = set()
    activities = set()
    
    missing_weather = []
    missing_time = []
    missing_description = []
    
    for img in images:
        weather = img.get("weather")
        time = img.get("time_period")
        
        if weather:
            weather_types.add(weather)
        else:
            missing_weather.append(img.get("title", img.get("id")))
        
        if time:
            time_periods.add(time)
        else:
            missing_time.append(img.get("title", img.get("id")))
        
        if img.get("activity"):
            activities.add(img["activity"])
        
        if not img.get("description"):
            missing_description.append(img.get("title", img.get("id")))
    
    return {
        "total_images": len(images),
        "weather_types": sorted(weather_types),
        "time_periods": sorted(time_periods),
        "activities": sorted(activities),
        "missing_weather": missing_weather[:10],  # First 10
        "missing_time": missing_time[:10],
        "missing_description": missing_description[:10],
        "coverage": {
            "has_weather": len(images) - len(missing_weather),
            "has_time": len(images) - len(missing_time),
            "has_description": len(images) - len(missing_description),
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Export Notion database for Alice Display")
    parser.add_argument("--limit", type=int, help="Limit number of rows to export")
    parser.add_argument("--output", type=str, default="data/image-database.json", help="Output file path")
    parser.add_argument("--validate", action="store_true", help="Validate export and show stats")
    args = parser.parse_args()
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent)
    
    try:
        exporter = NotionExporter()
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Export database
    images = exporter.export_database(limit=args.limit)
    
    if not images:
        print("❌ No images exported")
        sys.exit(1)
    
    # Validate if requested
    if args.validate:
        validation = validate_export(images)
        print(f"\n📊 Validation Results:")
        print(f"   Total images: {validation['total_images']}")
        print(f"   Weather types: {validation['weather_types']}")
        print(f"   Time periods: {validation['time_periods']}")
        print(f"   Activities: {validation['activities']}")
        print(f"   Coverage:")
        print(f"     - Has weather: {validation['coverage']['has_weather']}")
        print(f"     - Has time: {validation['coverage']['has_time']}")
        print(f"     - Has description: {validation['coverage']['has_description']}")
        
        if validation['missing_weather']:
            print(f"   ⚠️ Missing weather (first 10): {validation['missing_weather']}")
        if validation['missing_time']:
            print(f"   ⚠️ Missing time (first 10): {validation['missing_time']}")
    
    # Save to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump({"images": images, "exported_at": __import__("datetime").datetime.now().isoformat()}, f, indent=2)
    
    print(f"\n📁 Saved to: {output_path}")


if __name__ == "__main__":
    main()
