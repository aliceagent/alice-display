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
import requests
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

# Activity preferences by hour - what Alice should be doing at different times
# Format: hour -> list of preferred activities (in order of preference)
ACTIVITY_BY_HOUR = {
    # Late night / sleeping (22:00 - 05:59)
    22: ["Sleeping"],
    23: ["Sleeping"],
    0: ["Sleeping"],
    1: ["Sleeping"],
    2: ["Sleeping"],
    3: ["Sleeping"],
    4: ["Sleeping"],
    5: ["Sleeping"],
    # Early morning (06:00 - 07:59)
    6: ["Sleeping", "Waking Up", "Morning Routine"],
    7: ["Waking Up", "Morning Routine", "Breakfast", "Exercise"],
    # Morning (08:00 - 11:59)
    8: ["Breakfast", "Exercise", "Work", "Outdoor"],
    9: ["Work", "Exercise", "Outdoor", "Creative"],
    10: ["Work", "Outdoor", "Creative", "Exercise"],
    11: ["Work", "Outdoor", "Creative"],
    # Midday (12:00 - 13:59)
    12: ["Lunch", "Work", "Outdoor"],
    13: ["Lunch", "Work", "Leisure", "Outdoor"],
    # Afternoon (14:00 - 17:59)
    14: ["Work", "Leisure", "Creative", "Outdoor"],
    15: ["Work", "Leisure", "Creative", "Outdoor"],
    16: ["Leisure", "Creative", "Outdoor", "Exercise"],
    17: ["Leisure", "Creative", "Outdoor"],
    # Evening (18:00 - 21:59)
    18: ["Dinner", "Leisure", "Creative"],
    19: ["Dinner", "Leisure", "Reading", "Gaming"],
    20: ["Leisure", "Reading", "Gaming", "Movie"],
    21: ["Wind Down", "Reading", "Skincare", "Preparing for Bed"],
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
        hour: int = None,
        avoid_recent: bool = True,
        save_history: bool = True
    ) -> Optional[dict]:
        """
        Select an image matching the given weather and time period.
        
        Args:
            weather: Weather condition (Sunny, Rainy, etc.)
            time_period: Time of day (Morning, Afternoon, etc.)
            hour: Current hour (0-23) for activity preference
            avoid_recent: Avoid images selected in last 24 hours
            save_history: Save selection to history
            
        Returns:
            Selected image dict or None if no match found
        """
        if not self.images:
            print("❌ No images in database", file=sys.stderr)
            return None
        
        # Default hour to current time if not provided
        if hour is None:
            from datetime import datetime
            # Use UTC+2 as approximation for Asia/Hebron
            hour = (datetime.utcnow().hour + 2) % 24
        
        # Get recent IDs to avoid
        recent_ids = self._get_recent_ids(24) if avoid_recent else set()
        
        # Get preferred activities for this hour
        preferred_activities = ACTIVITY_BY_HOUR.get(hour, [])
        
        # Try exact match first (with activity preference)
        candidates = self._find_matches(weather, time_period, recent_ids, preferred_activities)
        
        # Try weather fallbacks
        if not candidates:
            for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                candidates = self._find_matches(fallback_weather, time_period, recent_ids, preferred_activities)
                if candidates:
                    print(f"📎 Using weather fallback: {weather} → {fallback_weather}")
                    break
        
        # Try time fallbacks
        if not candidates:
            for fallback_time in TIME_FALLBACKS.get(time_period, []):
                candidates = self._find_matches(weather, fallback_time, recent_ids, preferred_activities)
                if candidates:
                    print(f"📎 Using time fallback: {time_period} → {fallback_time}")
                    break
        
        # Try both fallbacks combined
        if not candidates:
            for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                for fallback_time in TIME_FALLBACKS.get(time_period, []):
                    candidates = self._find_matches(fallback_weather, fallback_time, recent_ids, preferred_activities)
                    if candidates:
                        print(f"📎 Using combined fallback: {weather}/{time_period} → {fallback_weather}/{fallback_time}")
                        break
                if candidates:
                    break
        
        # For sleeping hours (22-05), prioritize activity match over recency
        # Better to repeat a sleeping image than show Alice partying at 2 AM
        is_sleeping_hour = hour in [22, 23, 0, 1, 2, 3, 4, 5]
        
        # Check if current candidates actually match preferred activity
        def has_activity_match(cands, prefs):
            if not prefs:
                return True
            for c in cands:
                act = c.get('activity', '').lower()
                for p in prefs:
                    if p.lower() in act:
                        return True
            return False
        
        candidates_have_activity = has_activity_match(candidates, preferred_activities)
        
        if avoid_recent and is_sleeping_hour and preferred_activities and not candidates_have_activity:
            print("💤 Sleeping hour: relaxing recency to prioritize Sleeping images")
            
            # Helper to check if candidates have valid CDN URLs
            def has_cdn(cands):
                return any(c.get('cloudinary_url') and c.get('cloudinary_url').strip() for c in cands)
            
            sleeping_candidates = self._find_matches(weather, time_period, set(), preferred_activities)
            # Only accept if we have CDN images
            if not sleeping_candidates or not has_cdn(sleeping_candidates):
                for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                    sleeping_candidates = self._find_matches(fallback_weather, time_period, set(), preferred_activities)
                    if sleeping_candidates and has_cdn(sleeping_candidates):
                        print(f"📎 Using weather fallback: {weather} → {fallback_weather}")
                        break
            if sleeping_candidates and has_cdn(sleeping_candidates):
                # Filter to only CDN images
                sleeping_candidates = [c for c in sleeping_candidates if c.get('cloudinary_url') and c.get('cloudinary_url').strip()]
                candidates = sleeping_candidates
        
        # Try relaxing activity restriction if we still have no candidates with CDN
        if not candidates and preferred_activities:
            print("📎 Relaxing activity restriction to find CDN match")
            candidates = self._find_matches(weather, time_period, recent_ids, [])
            
            # Try weather fallbacks with relaxed activity
            if not candidates:
                for fallback_weather in WEATHER_FALLBACKS.get(weather, []):
                    candidates = self._find_matches(fallback_weather, time_period, recent_ids, [])
                    if candidates:
                        print(f"📎 Using weather fallback: {weather} → {fallback_weather}")
                        break
        
        # If still no candidates, ignore recent restriction
        if not candidates and avoid_recent:
            print("📎 Relaxing recent restriction to find match")
            return self.select(weather, time_period, hour=hour, avoid_recent=False, save_history=save_history)
        
        # Ultimate fallback: any image WITH CDN URL, but respect activity restrictions
        if not candidates:
            print("📎 Using CDN image fallback with activity filter")
            cdn_images = [img for img in self.images if img.get("cloudinary_url") and img.get("cloudinary_url").strip()]
            
            # During sleeping hours (22-07), only allow sleeping/waking activities in fallback
            if hour is not None and (hour >= 22 or hour <= 7):
                sleeping_activities = ["sleeping", "waking up", "morning routine"]
                filtered = []
                for img in cdn_images:
                    img_activity = img.get("activity", "").lower()
                    img_title = img.get("title", "").lower()
                    for act in sleeping_activities:
                        if act in img_activity or act in img_title:
                            filtered.append(img)
                            break
                if filtered:
                    print(f"   🛏️ Filtered to {len(filtered)} sleeping/waking images for hour {hour}")
                    cdn_images = filtered
            
            if cdn_images:
                candidates = cdn_images
            else:
                print("⚠️ No CDN images available!")
                candidates = self.images  # Last resort - shouldn't happen
        
        # Select using weighted random choice based on rating scores
        selected = self._weighted_random_choice(candidates)
        
        if save_history:
            self._save_history(selected)
        
        return selected
    
    def _weighted_random_choice(self, candidates: list) -> Optional[dict]:
        """
        Select an image using weighted random selection based on rating score.
        Higher rated images are more likely to be selected.
        
        Weight formula:
        - Base weight: 1.0
        - Rating modifier: rating_score / 10 (capped at ±1.0)
        - Final weight: max(0.1, min(3.0, base + modifier))
        
        Images with < 5 total ratings get neutral weight (1.0) to avoid
        extreme bias from few votes.
        """
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Calculate weights for each candidate
        weights = []
        for img in candidates:
            rating_score = img.get('rating_score', 0)
            total_ratings = img.get('total_ratings', 0)
            
            # Only apply rating weight if we have enough data
            if total_ratings >= 5:
                # Calculate weight modifier from rating score
                # Score of +10 → weight 2.0 (2x more likely)
                # Score of 0 → weight 1.0 (neutral)
                # Score of -10 → weight 0.1 (10x less likely)
                modifier = rating_score / 10.0
                weight = max(0.1, min(3.0, 1.0 + modifier))
            else:
                # Not enough ratings - use neutral weight
                weight = 1.0
            
            weights.append(weight)
        
        # Normalize weights to probabilities
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(candidates)
        
        probabilities = [w / total_weight for w in weights]
        
        # Weighted random selection
        r = random.random()
        cumulative = 0
        for i, prob in enumerate(probabilities):
            cumulative += prob
            if r <= cumulative:
                selected = candidates[i]
                # Log if rating influenced selection
                if selected.get('total_ratings', 0) >= 5:
                    print(f"   ⭐ Rating influence: score={selected.get('rating_score', 0)}, "
                          f"weight={weights[i]:.2f}")
                return selected
        
        # Fallback (shouldn't reach here)
        return random.choice(candidates)
    
    def _find_matches(self, weather: str, time_period: str, exclude_ids: set, preferred_activities: list = None) -> list:
        """Find all images matching weather, time, and activity preferences."""
        matches = []
        activity_matches = []  # Images that also match preferred activity
        
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
            
            # Check if activity matches preferred activities for this hour
            if preferred_activities:
                img_activity = img.get("activity", "").lower()
                img_title = img.get("title", "").lower()
                for pref_activity in preferred_activities:
                    pref_lower = pref_activity.lower()
                    if pref_lower in img_activity or pref_lower in img_title:
                        activity_matches.append(img)
                        break
        
        # Return activity-matched images if we have them, otherwise fall back to all matches
        if activity_matches:
            print(f"   🎯 Activity filter: {len(activity_matches)}/{len(matches)} images match preferred activities")
            matches = activity_matches
        
        # REQUIRE Cloudinary URLs — local paths don't exist on GitHub Pages.
        # STRICT: Only return images with CDN URLs. Return empty if none found.
        # The caller will handle fallbacks while keeping the CDN requirement.
        images_with_cdn = [m for m in matches if m.get("cloudinary_url") and m.get("cloudinary_url").strip()]
        return images_with_cdn  # May be empty - caller handles fallback
    
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


def increment_display_count(selected_image: dict) -> None:
    """
    Increment the Display Count for the selected image in Notion.
    Non-blocking: logs warning if fails but doesn't affect image selection.
    """
    page_id = selected_image.get("id") or selected_image.get("page_id")
    if not page_id:
        print("⚠️ Display Count: No page ID found, skipping counter increment", file=sys.stderr)
        return
    
    # Notion API configuration - uses environment variable only (no hardcoded fallback)
    notion_token = os.getenv("NOTION_API_KEY")
    if not notion_token:
        print("Warning: NOTION_API_KEY not set, Display Count will not be updated", file=sys.stderr)
        return  # Exit early if no token
    api_version = "2022-06-28"
    
    try:
        # First, get current Display Count value
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": api_version
        }
        
        response = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"⚠️ Display Count: Failed to read current count (HTTP {response.status_code})", file=sys.stderr)
            return
        
        data = response.json()
        current_count = data.get("properties", {}).get("Display Count", {}).get("number", 0) or 0
        new_count = current_count + 1
        
        # Update with incremented count
        headers["Content-Type"] = "application/json"
        update_data = {
            "properties": {
                "Display Count": {"number": new_count}
            }
        }
        
        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            json=update_data,
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"📊 Display Count: {current_count} → {new_count}")
        else:
            print(f"⚠️ Display Count: Failed to update count (HTTP {response.status_code})", file=sys.stderr)
            
    except Exception as e:
        print(f"⚠️ Display Count: Update failed - {str(e)}", file=sys.stderr)


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
            
            # Increment Display Count in Notion (non-blocking)
            increment_display_count(selected)
        
        return selected
    else:
        print("❌ No matching image found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
