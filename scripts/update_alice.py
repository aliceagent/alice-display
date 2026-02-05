#!/usr/bin/env python3
"""
Alice Display Update Orchestrator
Main script that coordinates weather fetching, image selection, and display updates.

This is the script called by GitHub Actions every hour.

Usage:
    python update_alice.py              # Full update cycle
    python update_alice.py --dry-run    # Preview without committing changes
    python update_alice.py --force      # Force update even if same conditions
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Import our modules
from fetch_weather import WeatherClient, get_mock_weather
from select_image import ImageSelector


class AliceUpdater:
    """Orchestrates the Alice display update process."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.weather_file = self.project_root / "data" / "current-weather.json"
        self.control_file = self.project_root / "display-control.json"
        self.history_file = self.project_root / "data" / "update-history.json"
        
    def run(self, dry_run: bool = False, force: bool = False, mock_weather: str = None) -> bool:
        """
        Execute the full update cycle.
        
        Args:
            dry_run: If True, don't write any files
            force: If True, update even if conditions haven't changed
            mock_weather: Use mock weather instead of API
            
        Returns:
            True if update was made, False otherwise
        """
        print("=" * 50)
        print("🦜 Alice Display Update")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Step 1: Fetch weather
        print("\n📡 Step 1: Fetching weather...")
        weather = self._fetch_weather(mock_weather)
        if not weather:
            print("❌ Failed to get weather data")
            return False
        
        print(f"   Condition: {weather['condition']}")
        print(f"   Temperature: {weather['temperature']}°C")
        print(f"   Time period: {weather['time_period']}")
        print(f"   Source: {weather['source']}")
        
        # Step 2: Always proceed - we want a new image every hour regardless of conditions
        # (The old logic skipped updates when weather was unchanged - removed per J's request)
        
        # Step 3: Select image
        print("\n🎨 Step 2: Selecting image...")
        selector = ImageSelector(self.project_root / "data" / "image-database.json")
        
        selected = selector.select(
            weather=weather["condition"],
            time_period=weather["time_period"],
            save_history=not dry_run
        )
        
        if not selected:
            print("❌ No suitable image found")
            return False
        
        print(f"   Selected: {selected.get('title', selected.get('id', 'Unknown'))}")
        
        # Step 4: Update display control
        print("\n📝 Step 3: Updating display control...")
        control = self._build_control(weather, selected)
        
        if dry_run:
            print("   [DRY RUN] Would update display-control.json:")
            print(f"   Image: {control['currentImage']['title']}")
            print(f"   URL: {control['currentImage']['url']}")
        else:
            self._save_control(control)
            self._save_history(weather, selected)
            print(f"   ✅ Saved to {self.control_file}")
        
        print("\n" + "=" * 50)
        print("✅ Update complete!")
        print("=" * 50)
        
        return True
    
    def _fetch_weather(self, mock: str = None) -> dict:
        """Fetch weather data from API or use mock."""
        if mock:
            return get_mock_weather(mock)
        
        client = WeatherClient()
        weather = client.fetch_with_fallback()
        
        # Save weather data
        self.weather_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.weather_file, "w") as f:
            json.dump(weather, f, indent=2)
        
        return weather
    
    def _load_current_control(self) -> dict:
        """Load current display control file."""
        if self.control_file.exists():
            try:
                with open(self.control_file) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return None
        return None
    
    def _conditions_match(self, current: dict, weather: dict) -> bool:
        """Check if conditions match current display."""
        try:
            current_weather = current.get("weather", {}).get("condition")
            current_time = current.get("time", {}).get("period")
            
            return (
                current_weather == weather["condition"] and
                current_time == weather["time_period"]
            )
        except (KeyError, TypeError):
            return False
    
    def _build_control(self, weather: dict, image: dict) -> dict:
        """Build the display control JSON."""
        # Get image URL
        url = (
            image.get("cloudinary_url") or 
            image.get("url") or 
            f"images/{image.get('filename', 'fallback.png')}"
        )
        
        return {
            "currentImage": {
                "id": image.get("id"),
                "url": url,
                "title": image.get("title", image.get("name", "Alice")),
                "description": image.get("description", ""),
                "activity": image.get("activity", ""),
                "mood": image.get("mood", ""),
                "imageWeather": image.get("weather", "Unknown"),
                "imageTimePeriod": image.get("time_period", image.get("time", "Unknown")),
                "imageHoliday": image.get("holiday", ""),
            },
            "weather": {
                "condition": weather["condition"],
                "temperature": weather["temperature"],
                "humidity": weather["humidity"],
                "description": weather["description"],
                "icon": weather["icon"],
            },
            "time": {
                "period": weather["time_period"],
                "hour": weather["current_hour"],
                "timezone": "Asia/Hebron",
            },
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "nextUpdate": self._get_next_update_time(),
        }
    
    def _get_next_update_time(self) -> str:
        """Calculate next update time (top of next hour)."""
        now = datetime.now(timezone.utc)
        next_hour = now.replace(minute=0, second=0, microsecond=0)
        if now.minute > 0 or now.second > 0:
            next_hour = next_hour.replace(hour=now.hour + 1)
        return next_hour.isoformat()
    
    def _save_control(self, control: dict) -> None:
        """Save display control file."""
        with open(self.control_file, "w") as f:
            json.dump(control, f, indent=2)
    
    def _save_history(self, weather: dict, image: dict) -> None:
        """Save update to history log."""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                history = []
        
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weather": weather["condition"],
            "time_period": weather["time_period"],
            "temperature": weather["temperature"],
            "image_id": image.get("id"),
            "image_title": image.get("title", image.get("name")),
        })
        
        # Keep last 168 entries (7 days of hourly updates)
        history = history[-168:]
        
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Update Alice Display")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--force", action="store_true", help="Force update even if conditions unchanged")
    parser.add_argument("--mock", type=str, help="Use mock weather (sunny/cloudy/rainy/etc)")
    args = parser.parse_args()
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent)
    
    updater = AliceUpdater()
    success = updater.run(
        dry_run=args.dry_run,
        force=args.force,
        mock_weather=args.mock
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
