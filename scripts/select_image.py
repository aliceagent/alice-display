#!/usr/bin/env python3
"""
Image Selection Algorithm for Alice Display System
Selects the optimal Alice image based on weather and time conditions.

Usage:
    python select_image.py                           # Select based on current weather
    python select_image.py --weather Rainy --time Morning  # Manual override
    python select_image.py --dry-run                 # Preview selection without saving
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# Weather fallback chains - if no exact match, try these in order
WEATHER_FALLBACKS = {
    "Sunny": ["Partly Cloudy", "Cloudy"],
    "Partly Cloudy": ["Sunny", "Cloudy"],
    "Cloudy": ["Overcast", "Partly Cloudy"],
    "Overcast": ["Cloudy", "Rainy"],
    "Rainy": ["Stormy", "Cloudy", "Overcast"],
    "Stormy": ["Rainy", "Overcast"],
    "Snowy": ["Cloudy", "Overcast", "Foggy"],
    "Foggy": ["Cloudy", "Overcast"],
    "Windy": ["Cloudy", "Partly Cloudy"],
}

# Time period fallback chains (matching gallery DB values:
# Dawn, Morning, Midday, Afternoon, Evening, Night, Early Morning, Late Night, Golden Hour)
TIME_FALLBACKS = {
    "Dawn": ["Early Morning", "Morning", "Golden Hour"],
    "Early Morning": ["Dawn", "Morning"],
    "Morning": ["Dawn", "Midday", "Early Morning"],
    "Midday": ["Afternoon", "Morning"],
    "Afternoon": ["Midday", "Evening", "Golden Hour"],
    "Golden Hour": ["Afternoon", "Evening"],
    "Evening": ["Golden Hour", "Afternoon", "Night"],
    "Night": ["Late Night", "Evening", "Dawn"],
    "Late Night": ["Night", "Dawn"],
    "Clear Night": ["Night", "Late Night", "Evening"],
}


class ImageSelector:
    """Selects images from the database based on weather and time conditions."""
    
    def __init__(self, database_path: str = "data/image-database.json"):
        self.database_path = Path(database_path)
        self.history_path = Path("data/selection-history.json")
        self.images = self._load_database()
        self.history = self._load_history()
    
    def _load_database(self) -> list:
        """Load image database from JSON file."""
        if not self.database_path.exists():
            print(f"⚠️ Database not found: {self.database_path}", file=sys.stderr)
            return []
        
        with open(self.database_path) as f:
            data = json.load(f)
            # Handle both list format and dict with 'images' key
            if isinstance(data, list):
                return data
            return data.get("images", [])
    
    def _load_history(self) -> dict:
        """Load selection history for variety tracking."""
        if self.history_path.exists():
            try:
                with open(self.history_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"selections": []}
        return {"selections": []}
    
    def _save_history(self, selected_image: dict) -> None:
        """Save selection to history for variety tracking."""
        self.history["selections"].append({
            "id": selected_image.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weather": selected_image.get("weather"),
            "time_period": selected_image.get("time_period"),
        })
        
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
                ts = datetime.fromisoformat(selection["timestamp"].replace("Z", "+00:00"))
                if ts > cutoff:
                    recent_ids.add(selection["id"])
            except (KeyError, ValueError):
                continue
        
        return recent_ids
    
    def select(
        self,
        weather: str,
        time_period: str,
        avoid_recent: bool = True,
        save_history: bool = True
    ) -> Optional[dict]:
        """
        Select an image matching the given weather and time period.
        
        Args:
            weather: Weather condition (Sunny, Rainy, etc.)
            time_period: Time of day (Morning, Afternoon, etc.)
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
        
        # Try exact match first
        candidates = self._find_matches(weather, time_period, recent_ids)
        
        # Try weather fallbacks
        if not candidates:
            for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                candidates = self._find_matches(fallback_weather, time_period, recent_ids)
                if candidates:
                    print(f"📎 Using weather fallback: {weather} → {fallback_weather}")
                    break
        
        # Try time fallbacks
        if not candidates:
            for fallback_time in TIME_FALLBACKS.get(time_period, []):
                candidates = self._find_matches(weather, fallback_time, recent_ids)
                if candidates:
                    print(f"📎 Using time fallback: {time_period} → {fallback_time}")
                    break
        
        # Try both fallbacks combined
        if not candidates:
            for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                for fallback_time in TIME_FALLBACKS.get(time_period, []):
                    candidates = self._find_matches(fallback_weather, fallback_time, recent_ids)
                    if candidates:
                        print(f"📎 Using combined fallback: {weather}/{time_period} → {fallback_weather}/{fallback_time}")
                        break
                if candidates:
                    break
        
        # If still no candidates, ignore recent restriction
        if not candidates and avoid_recent:
            print("📎 Relaxing recent restriction to find match")
            return self.select(weather, time_period, avoid_recent=False, save_history=save_history)
        
        # Ultimate fallback: any image
        if not candidates:
            print("📎 Using random image as ultimate fallback")
            candidates = self.images
        
        # Select randomly from candidates (could add weighting here)
        selected = random.choice(candidates)
        
        if save_history:
            self._save_history(selected)
        
        return selected
    
    def _find_matches(self, weather: str, time_period: str, exclude_ids: set) -> list:
        """Find all images matching weather and time, excluding recent IDs and non-current holidays."""
        matches = []
        for img in self.images:
            # CRITICAL: Skip holiday images unless today is that holiday
            # Holiday images should only show on their specific days
            img_holiday = img.get("holiday", "").strip()
            if img_holiday:
                # This is a holiday image - skip it for now
                # TODO: Add proper Hebrew calendar integration to show holiday images on correct days
                continue
            
            # Check weather match (case-insensitive)
            img_weather = img.get("weather", "").lower()
            if weather.lower() not in img_weather and img_weather not in weather.lower():
                continue
            
            # Check time match (case-insensitive)
            img_time = img.get("time_period", img.get("time", "")).lower()
            if time_period.lower() not in img_time and img_time not in time_period.lower():
                continue
            
            # Check if recently used
            if img.get("id") in exclude_ids:
                continue
            
            matches.append(img)
        
        # REQUIRE Cloudinary URLs — local paths don't exist on GitHub Pages.
        # Once all images are uploaded to Cloudinary, this filter can be relaxed.
        images_with_cdn = [m for m in matches if m.get("cloudinary_url")]
        if images_with_cdn:
            return images_with_cdn
        
        # Fallback: any image with a URL (only useful for local development)
        images_with_urls = [m for m in matches if m.get("url")]
        if images_with_urls:
            return images_with_urls
        
        return matches
    
    def get_stats(self) -> dict:
        """Get statistics about the image database."""
        weather_counts = {}
        time_counts = {}
        
        for img in self.images:
            weather = img.get("weather", "Unknown")
            time = img.get("time_period", img.get("time", "Unknown"))
            
            weather_counts[weather] = weather_counts.get(weather, 0) + 1
            time_counts[time] = time_counts.get(time, 0) + 1
        
        return {
            "total_images": len(self.images),
            "by_weather": weather_counts,
            "by_time": time_counts,
            "recent_selections": len(self._get_recent_ids(24)),
        }


def main():
    parser = argparse.ArgumentParser(description="Select Alice image based on conditions")
    parser.add_argument("--weather", type=str, help="Weather condition override")
    parser.add_argument("--time", type=str, help="Time period override")
    parser.add_argument("--database", type=str, default="data/image-database.json", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    args = parser.parse_args()
    
    # Change to script's parent directory (project root)
    os.chdir(Path(__file__).parent.parent)
    
    selector = ImageSelector(args.database)
    
    if args.stats:
        stats = selector.get_stats()
        print(f"📊 Database Statistics:")
        print(f"   Total images: {stats['total_images']}")
        print(f"   By weather: {json.dumps(stats['by_weather'], indent=6)}")
        print(f"   By time: {json.dumps(stats['by_time'], indent=6)}")
        print(f"   Recent selections (24h): {stats['recent_selections']}")
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
    
    print(f"🔍 Searching for: {weather} + {time_period}")
    
    # Select image
    selected = selector.select(
        weather=weather,
        time_period=time_period,
        save_history=not args.dry_run
    )
    
    if selected:
        print(f"✅ Selected image:")
        print(f"   ID: {selected.get('id', 'N/A')}")
        print(f"   Title: {selected.get('title', selected.get('name', 'N/A'))}")
        print(f"   Weather: {selected.get('weather', 'N/A')}")
        print(f"   Time: {selected.get('time_period', selected.get('time', 'N/A'))}")
        print(f"   Activity: {selected.get('activity', 'N/A')}")
        
        url = selected.get('cloudinary_url') or selected.get('url') or selected.get('filename')
        if url:
            print(f"   URL: {url}")
        
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
