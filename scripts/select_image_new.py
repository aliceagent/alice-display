#!/usr/bin/env python3
"""
Enhanced Image Selection Algorithm for Alice Display System
Selects the optimal Alice image based on weather and time conditions from the gallery database.

Usage:
    python select_image_new.py                           # Select based on current weather
    python select_image_new.py --weather Rainy --time Morning  # Manual override
    python select_image_new.py --dry-run                 # Preview selection without saving
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict


# Weather fallback chains from gallery database values
WEATHER_FALLBACKS = {
    "Sunny": ["Cloudy", "Overcast"],
    "Cloudy": ["Overcast", "Sunny", "Foggy"],
    "Overcast": ["Cloudy", "Foggy", "Rainy"],
    "Rainy": ["Stormy", "Overcast", "Cloudy"],
    "Stormy": ["Rainy", "Overcast"],
    "Snowy": ["Cloudy", "Overcast", "Foggy"],
    "Foggy": ["Cloudy", "Overcast"],
}

# Time of Day fallback chains from gallery database values
TIME_FALLBACKS = {
    "Dawn": ["Morning", "Evening"],
    "Morning": ["Dawn", "Midday"],
    "Midday": ["Morning", "Afternoon"],
    "Afternoon": ["Midday", "Evening"],
    "Evening": ["Afternoon", "Night"],
    "Night": ["Evening", "Dawn"],
}


class ImageSelector:
    """Selects images from the gallery database based on weather and time conditions."""
    
    def __init__(self, database_path: str = "data/image-database.json"):
        self.database_path = Path(database_path)
        self.history_path = Path("data/selection-history.json")
        self.cloudinary_urls_path = Path("data/cloudinary-urls.json")
        
        self.images = self._load_database()
        self.history = self._load_history()
        self.cloudinary_urls = self._load_cloudinary_urls()
    
    def _load_database(self) -> List[Dict]:
        """Load image database from JSON file."""
        if not self.database_path.exists():
            print(f"⚠️ Database not found: {self.database_path}", file=sys.stderr)
            return []
        
        try:
            with open(self.database_path) as f:
                data = json.load(f)
                # Handle both list format and dict with 'images' key
                if isinstance(data, list):
                    return data
                return data.get("images", [])
        except Exception as e:
            print(f"❌ Error loading database: {e}", file=sys.stderr)
            return []
    
    def _load_history(self) -> Dict:
        """Load selection history for variety tracking."""
        if self.history_path.exists():
            try:
                with open(self.history_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"selections": []}
        return {"selections": []}
    
    def _load_cloudinary_urls(self) -> Dict:
        """Load Cloudinary URL mapping."""
        if self.cloudinary_urls_path.exists():
            try:
                with open(self.cloudinary_urls_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def _save_history(self, selected_image: Dict) -> None:
        """Save selection to history for variety tracking."""
        selection_record = {
            "id": selected_image.get("id") or selected_image.get("notion_id"),
            "name": selected_image.get("name") or selected_image.get("title"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weather": selected_image.get("weather"),
            "time_of_day": selected_image.get("time_of_day") or selected_image.get("time_period"),
            "activity": selected_image.get("activity"),
        }
        
        self.history["selections"].append(selection_record)
        
        # Keep only last 100 selections
        self.history["selections"] = self.history["selections"][-100:]
        
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_path, "w") as f:
            json.dump(self.history, f, indent=2)
    
    def _get_recent_ids(self, hours: int = 24) -> set:
        """Get image IDs selected in the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_ids = set()
        
        for selection in self.history.get("selections", []):
            try:
                ts_str = selection["timestamp"]
                # Handle both Z suffix and +00:00 timezone formats
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                ts = datetime.fromisoformat(ts_str)
                
                if ts > cutoff:
                    recent_ids.add(selection.get("id"))
                    recent_ids.add(selection.get("name"))  # Also track by name
            except (KeyError, ValueError):
                continue
        
        return recent_ids
    
    def select(
        self,
        weather: str,
        time_of_day: str,
        avoid_recent: bool = True,
        save_history: bool = True
    ) -> Optional[Dict]:
        """
        Select an image matching the given weather and time of day.
        
        Args:
            weather: Weather condition (Sunny, Rainy, Snowy, Cloudy, Stormy, Foggy, Overcast)
            time_of_day: Time period (Dawn, Morning, Midday, Afternoon, Evening, Night)
            avoid_recent: Avoid images selected in last 24 hours
            save_history: Save selection to history
            
        Returns:
            Selected image dict or None if no match found
        """
        if not self.images:
            print("❌ No images in database", file=sys.stderr)
            return None
        
        # Get recent IDs to avoid
        recent_ids = self._get_recent_ids(24) if avoid_recent else set()
        
        print(f"🔍 Searching for: {weather} + {time_of_day}")
        if recent_ids:
            print(f"📝 Avoiding {len(recent_ids)} recently used images")
        
        # Try exact match first
        candidates = self._find_matches(weather, time_of_day, recent_ids)
        match_type = "exact"
        
        # Try weather fallbacks
        if not candidates:
            for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                candidates = self._find_matches(fallback_weather, time_of_day, recent_ids)
                if candidates:
                    match_type = f"weather fallback: {weather} → {fallback_weather}"
                    print(f"📎 Using {match_type}")
                    break
        
        # Try time fallbacks
        if not candidates:
            for fallback_time in TIME_FALLBACKS.get(time_of_day, []):
                candidates = self._find_matches(weather, fallback_time, recent_ids)
                if candidates:
                    match_type = f"time fallback: {time_of_day} → {fallback_time}"
                    print(f"📎 Using {match_type}")
                    break
        
        # Try both fallbacks combined
        if not candidates:
            for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                for fallback_time in TIME_FALLBACKS.get(time_of_day, []):
                    candidates = self._find_matches(fallback_weather, fallback_time, recent_ids)
                    if candidates:
                        match_type = f"combined fallback: {weather}/{time_of_day} → {fallback_weather}/{fallback_time}"
                        print(f"📎 Using {match_type}")
                        break
                if candidates:
                    break
        
        # If still no candidates, ignore recent restriction
        if not candidates and avoid_recent:
            print("📎 Relaxing recent restriction to find match")
            return self.select(weather, time_of_day, avoid_recent=False, save_history=save_history)
        
        # Ultimate fallback: any verified image
        if not candidates:
            print("📎 Using random verified image as ultimate fallback")
            candidates = [img for img in self.images if img.get("verified", False)]
            if not candidates:
                candidates = self.images  # If no verified, use any
            match_type = "random fallback"
        
        if not candidates:
            print("❌ No images available", file=sys.stderr)
            return None
        
        # Select randomly from candidates
        selected = random.choice(candidates)
        
        # Enhance the selected image with Cloudinary URL if available
        filename = None
        # Try to extract filename from path or name
        if selected.get("path"):
            filename = Path(selected["path"]).stem
        elif selected.get("name"):
            # Try to construct filename from name and row number
            if selected.get("row_number"):
                row_num = selected["row_number"]
                filename = f"{row_num:03d}_{selected['name'].replace(' ', '_').replace('-', '_')}"
        
        # Look up Cloudinary URL
        if filename and filename in self.cloudinary_urls:
            selected["cloudinary_url"] = self.cloudinary_urls[filename]
        
        print(f"✅ Selected image ({match_type}): {selected.get('name', 'Unknown')}")
        print(f"   Found {len(candidates)} matching candidates")
        
        if save_history:
            self._save_history(selected)
        
        return selected
    
    def _find_matches(self, weather: str, time_of_day: str, exclude_ids: set) -> List[Dict]:
        """Find all images matching weather and time, excluding recent IDs."""
        matches = []
        
        for img in self.images:
            # Skip if not verified (unless no verified images exist)
            # We'll handle this at the candidate level
            
            # Check weather match (exact match for gallery database)
            img_weather = img.get("weather", "").strip()
            if not img_weather or img_weather.lower() != weather.lower():
                continue
            
            # Check time match (exact match for gallery database)
            img_time = img.get("time_of_day", "").strip()
            if not img_time or img_time.lower() != time_of_day.lower():
                continue
            
            # Check if recently used (check both ID and name)
            img_id = img.get("id") or img.get("notion_id")
            img_name = img.get("name") or img.get("title")
            if img_id in exclude_ids or img_name in exclude_ids:
                continue
            
            matches.append(img)
        
        # Prefer verified images if available
        verified_matches = [m for m in matches if m.get("verified", False)]
        if verified_matches:
            return verified_matches
        
        return matches
    
    def get_stats(self) -> Dict:
        """Get statistics about the image database."""
        weather_counts = {}
        time_counts = {}
        activity_counts = {}
        verified_count = 0
        with_cloudinary = 0
        
        for img in self.images:
            weather = img.get("weather", "Unknown")
            time = img.get("time_of_day", "Unknown")
            activity = img.get("activity", "Unknown")
            
            weather_counts[weather] = weather_counts.get(weather, 0) + 1
            time_counts[time] = time_counts.get(time, 0) + 1
            activity_counts[activity] = activity_counts.get(activity, 0) + 1
            
            if img.get("verified"):
                verified_count += 1
            
            if img.get("cloudinary_url"):
                with_cloudinary += 1
        
        return {
            "total_images": len(self.images),
            "verified_images": verified_count,
            "with_cloudinary_url": with_cloudinary,
            "by_weather": weather_counts,
            "by_time": time_counts,
            "by_activity": activity_counts,
            "recent_selections_24h": len(self._get_recent_ids(24)),
        }


def main():
    parser = argparse.ArgumentParser(description="Select Alice image based on conditions")
    parser.add_argument("--weather", type=str, help="Weather condition override")
    parser.add_argument("--time", type=str, help="Time period override")
    parser.add_argument("--database", type=str, default="data/image-database.json", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--test", action="store_true", help="Run test scenarios")
    args = parser.parse_args()
    
    # Change to script's parent directory (project root)
    os.chdir(Path(__file__).parent.parent)
    
    selector = ImageSelector(args.database)
    
    if args.stats:
        stats = selector.get_stats()
        print(f"📊 Database Statistics:")
        print(f"   Total images: {stats['total_images']}")
        print(f"   Verified: {stats['verified_images']}")
        print(f"   With Cloudinary URL: {stats['with_cloudinary_url']}")
        print(f"   By weather: {json.dumps(stats['by_weather'], indent=6)}")
        print(f"   By time: {json.dumps(stats['by_time'], indent=6)}")
        print(f"   By activity: {json.dumps(stats['by_activity'], indent=6)}")
        print(f"   Recent selections (24h): {stats['recent_selections_24h']}")
        return
    
    if args.test:
        # Test various weather/time combinations
        test_cases = [
            ("Sunny", "Morning"),
            ("Rainy", "Evening"),
            ("Snowy", "Dawn"),
            ("Cloudy", "Afternoon"),
            ("Stormy", "Night"),
            ("Foggy", "Midday"),
        ]
        
        print("🧪 Testing Selection Algorithm:")
        print("=" * 50)
        
        for weather, time in test_cases:
            print(f"\n🔬 Test: {weather} + {time}")
            selected = selector.select(weather, time, save_history=False)
            if selected:
                print(f"   Result: {selected.get('name', 'Unknown')}")
                print(f"   Activity: {selected.get('activity', 'N/A')}")
                print(f"   Location: {selected.get('location', 'N/A')}")
                has_url = bool(selected.get('cloudinary_url'))
                print(f"   Has Cloudinary URL: {has_url}")
            else:
                print(f"   Result: ❌ No match found")
        
        return
    
    # Load weather data if no override provided
    if not args.weather or not args.time:
        weather_file = Path("data/current-weather.json")
        if weather_file.exists():
            with open(weather_file) as f:
                weather_data = json.load(f)
            weather = args.weather or weather_data.get("condition", "Sunny")
            time_period = args.time or weather_data.get("time_period", "Afternoon")
        else:
            weather = args.weather or "Sunny"
            time_period = args.time or "Afternoon"
            print("⚠️ No weather data found, using defaults", file=sys.stderr)
    else:
        weather = args.weather
        time_period = args.time
    
    # Select image
    selected = selector.select(
        weather=weather,
        time_of_day=time_period,
        save_history=not args.dry_run
    )
    
    if selected:
        print(f"\n📸 Selected Image Details:")
        print(f"   ID: {selected.get('id') or selected.get('notion_id', 'N/A')}")
        print(f"   Name: {selected.get('name') or selected.get('title', 'N/A')}")
        print(f"   Weather: {selected.get('weather', 'N/A')}")
        print(f"   Time: {selected.get('time_of_day', 'N/A')}")
        print(f"   Activity: {selected.get('activity', 'N/A')}")
        print(f"   Location: {selected.get('location', 'N/A')}")
        print(f"   Verified: {selected.get('verified', False)}")
        print(f"   Row Number: {selected.get('row_number', 'N/A')}")
        
        url = selected.get('cloudinary_url')
        if url:
            print(f"   Cloudinary URL: {url}")
        else:
            print(f"   Cloudinary URL: ❌ Not available")
        
        # Save selected image info
        if not args.dry_run:
            output_path = Path("data/selected-image.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(selected, f, indent=2)
            print(f"📁 Saved to: {output_path}")
        
        return selected
    else:
        print("❌ No matching image found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()