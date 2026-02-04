#!/usr/bin/env python3
"""
Weather API Client for Alice Display System
Fetches real-time weather data from OpenWeatherMap API

Usage:
    python fetch_weather.py                    # Fetch and save weather
    python fetch_weather.py --test             # Test API connection
    python fetch_weather.py --mock sunny       # Use mock weather for testing
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.error

# Hebron, Palestine coordinates
DEFAULT_LAT = 31.5326
DEFAULT_LON = 35.0998
TIMEZONE = "Asia/Hebron"

# Weather code mapping: OpenWeatherMap codes → Our categories
WEATHER_MAPPING = {
    # Thunderstorm (200-232) and Heavy Rain (505-531)
    "Stormy": list(range(200, 233)) + list(range(505, 532)),
    # Drizzle (300-321) and Light Rain (500-504)
    "Rainy": list(range(300, 322)) + list(range(500, 505)),
    # Snow (600-622)
    "Snowy": list(range(600, 623)),
    # Atmosphere - Fog, Mist, Haze (700-749)
    "Foggy": list(range(700, 750)),
    # Atmosphere - Dust, Sand, Tornado (750-781)
    "Windy": list(range(750, 782)),
    # Clear (800)
    "Sunny": [800],
    # Partly Cloudy (801)
    "Partly Cloudy": [801],
    # Cloudy (802)
    "Cloudy": [802],
    # Overcast (803-804)
    "Overcast": [803, 804],
}

# Reverse mapping for lookup
CODE_TO_WEATHER = {}
for weather_type, codes in WEATHER_MAPPING.items():
    for code in codes:
        CODE_TO_WEATHER[code] = weather_type


def normalize_weather(weather_id: int) -> str:
    """Convert OpenWeatherMap weather code to our weather category."""
    return CODE_TO_WEATHER.get(weather_id, "Sunny")


def get_time_period(hour: int, sunrise_hour: int = 6, sunset_hour: int = 18) -> str:
    """
    Determine time period based on current hour.
    Uses fixed boundaries for consistent behavior in Israel timezone.
    
    Maps to gallery DB values: Dawn, Early Morning, Morning, Midday,
    Afternoon, Golden Hour, Evening, Night, Late Night.
    
    The gallery has 31 Sleeping images tagged as Early Morning, Night,
    and Late Night — so late hours map to Late Night to prefer those.
    """
    # Late Night / Sleep: 23:00-4:59 → "Late Night" (maps to sleeping images)
    if hour >= 23 or hour < 5:
        return "Late Night"
    # Dawn: 5:00-5:59 (pre-sunrise)
    elif 5 <= hour < 6:
        return "Dawn"
    # Early Morning: 6:00-7:59
    elif 6 <= hour < 8:
        return "Early Morning"
    # Morning: 8:00-10:59
    elif 8 <= hour < 11:
        return "Morning"
    # Midday: 11:00-13:59
    elif 11 <= hour < 14:
        return "Midday"
    # Afternoon: 14:00-16:59
    elif 14 <= hour < 17:
        return "Afternoon"
    # Golden Hour: 17:00-17:59 (sunset hour in Israel winter)
    elif 17 <= hour < 18:
        return "Golden Hour"
    # Evening: 18:00-19:59
    elif 18 <= hour < 20:
        return "Evening"
    # Night: 20:00-22:59
    else:
        return "Night"


class WeatherClient:
    """Client for fetching weather data from OpenWeatherMap API."""
    
    def __init__(self, api_key: str = None, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
        self.api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")
        self.lat = lat
        self.lon = lon
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.cache_file = Path(__file__).parent.parent / "data" / "weather-cache.json"
        
    def fetch(self) -> dict:
        """Fetch current weather from API."""
        if not self.api_key:
            raise ValueError("API key required. Set OPENWEATHER_API_KEY environment variable.")
        
        url = f"{self.base_url}?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                return self._parse_response(data)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise ValueError("Invalid API key")
            elif e.code == 429:
                raise ValueError("Rate limit exceeded")
            else:
                raise ValueError(f"API error: {e.code}")
        except urllib.error.URLError as e:
            raise ValueError(f"Network error: {e.reason}")
    
    def _parse_response(self, data: dict) -> dict:
        """Parse OpenWeatherMap response into our format."""
        weather_id = data["weather"][0]["id"]
        
        # Extract sunrise/sunset for time period calculation
        sunrise_ts = data["sys"]["sunrise"]
        sunset_ts = data["sys"]["sunset"]
        sunrise_hour = datetime.fromtimestamp(sunrise_ts).hour
        sunset_hour = datetime.fromtimestamp(sunset_ts).hour
        
        # Get current hour
        current_hour = datetime.now().hour
        
        return {
            "temperature": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"],
            "wind_speed": round(data["wind"]["speed"] * 3.6),  # m/s to km/h
            "weather_id": weather_id,
            "condition": normalize_weather(weather_id),
            "description": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
            "sunrise_hour": sunrise_hour,
            "sunset_hour": sunset_hour,
            "time_period": get_time_period(current_hour, sunrise_hour, sunset_hour),
            "current_hour": current_hour,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "OpenWeatherMap"
        }
    
    def fetch_with_fallback(self) -> dict:
        """Fetch weather with cache fallback on failure."""
        try:
            weather = self.fetch()
            self._save_cache(weather)
            return weather
        except Exception as e:
            print(f"⚠️ Weather API error: {e}", file=sys.stderr)
            
            # Try to load from cache
            cached = self._load_cache()
            if cached:
                print("📦 Using cached weather data", file=sys.stderr)
                cached["source"] = "cache"
                return cached
            
            # Ultimate fallback
            print("🔄 Using fallback weather defaults", file=sys.stderr)
            return self._get_fallback()
    
    def _save_cache(self, weather: dict) -> None:
        """Save weather data to cache file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(weather, f, indent=2)
    
    def _load_cache(self):
        """Load weather data from cache file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return None
        return None
    
    def _get_fallback(self) -> dict:
        """Return fallback weather for when all else fails."""
        current_hour = datetime.now().hour
        return {
            "temperature": 20,
            "feels_like": 20,
            "humidity": 50,
            "wind_speed": 10,
            "weather_id": 800,
            "condition": "Sunny",
            "description": "clear sky (fallback)",
            "icon": "01d" if 6 <= current_hour <= 18 else "01n",
            "sunrise_hour": 6,
            "sunset_hour": 18,
            "time_period": get_time_period(current_hour, 6, 18),
            "current_hour": current_hour,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "fallback"
        }


def get_mock_weather(condition: str = "Sunny") -> dict:
    """Generate mock weather for testing."""
    current_hour = datetime.now().hour
    
    condition_map = {
        "sunny": ("Sunny", 800, "clear sky"),
        "cloudy": ("Cloudy", 802, "scattered clouds"),
        "rainy": ("Rainy", 500, "light rain"),
        "stormy": ("Stormy", 211, "thunderstorm"),
        "snowy": ("Snowy", 601, "snow"),
        "foggy": ("Foggy", 741, "fog"),
    }
    
    cond, code, desc = condition_map.get(condition.lower(), ("Sunny", 800, "clear sky"))
    
    return {
        "temperature": 18,
        "feels_like": 17,
        "humidity": 65,
        "wind_speed": 12,
        "weather_id": code,
        "condition": cond,
        "description": desc,
        "icon": "01d",
        "sunrise_hour": 6,
        "sunset_hour": 18,
        "time_period": get_time_period(current_hour, 6, 18),
        "current_hour": current_hour,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mock"
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch weather for Alice Display")
    parser.add_argument("--test", action="store_true", help="Test API connection")
    parser.add_argument("--mock", type=str, help="Use mock weather (sunny/cloudy/rainy/stormy/snowy/foggy)")
    parser.add_argument("--output", type=str, default="data/current-weather.json", help="Output file path")
    args = parser.parse_args()
    
    # Change to script's parent directory (project root)
    os.chdir(Path(__file__).parent.parent)
    
    if args.mock:
        weather = get_mock_weather(args.mock)
        print(f"🎭 Mock weather: {args.mock}")
    else:
        client = WeatherClient()
        
        if args.test:
            print("🧪 Testing API connection...")
            try:
                weather = client.fetch()
                print("✅ API connection successful!")
            except ValueError as e:
                print(f"❌ API test failed: {e}")
                sys.exit(1)
        else:
            weather = client.fetch_with_fallback()
    
    # Save to output file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(weather, f, indent=2)
    
    # Print summary
    print(f"🌤️  Weather: {weather['condition']} ({weather['description']})")
    print(f"🌡️  Temperature: {weather['temperature']}°C (feels like {weather['feels_like']}°C)")
    print(f"💧 Humidity: {weather['humidity']}%")
    print(f"💨 Wind: {weather['wind_speed']} km/h")
    print(f"🕐 Time period: {weather['time_period']}")
    print(f"📁 Saved to: {output_path}")
    
    return weather


if __name__ == "__main__":
    main()
