#!/usr/bin/env python3
"""
Test Kit: Weather API
Tests for fetch_weather.py module
"""

import pytest
import json
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_weather import (
    normalize_weather,
    get_time_period,
    WeatherClient,
    get_mock_weather,
    DEFAULT_LAT,
    DEFAULT_LON,
)


class TestWeatherCodeMapping:
    """Tests for OpenWeatherMap code normalization."""
    
    def test_thunderstorm_codes_return_stormy(self):
        """Weather codes 200-232 should return Stormy."""
        for code in [200, 201, 211, 221, 232]:
            assert normalize_weather(code) == "Stormy", f"Code {code} should be Stormy"
    
    def test_rain_codes_return_rainy(self):
        """Light rain codes should return Rainy."""
        for code in [300, 310, 500, 501, 502]:
            assert normalize_weather(code) == "Rainy", f"Code {code} should be Rainy"
    
    def test_snow_codes_return_snowy(self):
        """Snow codes 600-622 should return Snowy."""
        for code in [600, 601, 611, 620]:
            assert normalize_weather(code) == "Snowy", f"Code {code} should be Snowy"
    
    def test_fog_codes_return_foggy(self):
        """Fog/mist codes should return Foggy."""
        for code in [701, 711, 721, 741]:
            assert normalize_weather(code) == "Foggy", f"Code {code} should be Foggy"
    
    def test_clear_returns_sunny(self):
        """Clear sky code 800 should return Sunny."""
        assert normalize_weather(800) == "Sunny"
    
    def test_partly_cloudy(self):
        """Code 801 should return Partly Cloudy."""
        assert normalize_weather(801) == "Partly Cloudy"
    
    def test_cloudy(self):
        """Code 802 should return Cloudy."""
        assert normalize_weather(802) == "Cloudy"
    
    def test_overcast(self):
        """Codes 803-804 should return Overcast."""
        assert normalize_weather(803) == "Overcast"
        assert normalize_weather(804) == "Overcast"
    
    def test_unknown_code_defaults_to_sunny(self):
        """Unknown weather codes should default to Sunny."""
        assert normalize_weather(999) == "Sunny"
        assert normalize_weather(0) == "Sunny"


class TestTimePeriodCalculation:
    """Tests for time period determination."""
    
    def test_dawn_near_sunrise(self):
        """Hours around sunrise should return Dawn."""
        # Assuming sunrise at 6
        assert get_time_period(5, 6, 18) == "Dawn"
        assert get_time_period(6, 6, 18) == "Dawn"
    
    def test_morning_after_dawn(self):
        """Morning hours should return Morning."""
        assert get_time_period(7, 6, 18) == "Morning"
        assert get_time_period(9, 6, 18) == "Morning"
        assert get_time_period(11, 6, 18) == "Morning"
    
    def test_afternoon(self):
        """Afternoon hours should return Afternoon."""
        assert get_time_period(12, 6, 18) == "Afternoon"
        assert get_time_period(14, 6, 18) == "Afternoon"
        assert get_time_period(15, 6, 18) == "Afternoon"
    
    def test_evening_near_sunset(self):
        """Hours around sunset should return Evening."""
        assert get_time_period(16, 6, 18) == "Evening"
        assert get_time_period(17, 6, 18) == "Evening"
        assert get_time_period(18, 6, 18) == "Evening"
    
    def test_night_after_evening(self):
        """Late night hours should return Night."""
        assert get_time_period(21, 6, 18) == "Night"
        assert get_time_period(23, 6, 18) == "Night"
        assert get_time_period(2, 6, 18) == "Night"


class TestMockWeather:
    """Tests for mock weather generation."""
    
    def test_sunny_mock(self):
        """Mock sunny weather should have correct values."""
        weather = get_mock_weather("sunny")
        assert weather["condition"] == "Sunny"
        assert weather["weather_id"] == 800
        assert weather["source"] == "mock"
    
    def test_rainy_mock(self):
        """Mock rainy weather should have correct values."""
        weather = get_mock_weather("rainy")
        assert weather["condition"] == "Rainy"
        assert weather["source"] == "mock"
    
    def test_mock_includes_required_fields(self):
        """All mock weather should include required fields."""
        weather = get_mock_weather("cloudy")
        required_fields = [
            "temperature", "humidity", "condition", "description",
            "time_period", "current_hour", "timestamp", "source"
        ]
        for field in required_fields:
            assert field in weather, f"Missing field: {field}"


class TestWeatherClientFallback:
    """Tests for weather client error handling and fallback."""
    
    def test_fallback_on_missing_api_key(self):
        """Should use fallback when no API key is provided."""
        with patch.dict('os.environ', {}, clear=True):
            client = WeatherClient(api_key=None)
            weather = client._get_fallback()
            assert weather["source"] == "fallback"
            assert weather["condition"] == "Sunny"
    
    def test_fallback_weather_has_required_fields(self):
        """Fallback weather should have all required fields."""
        client = WeatherClient(api_key="test")
        fallback = client._get_fallback()
        
        required_fields = [
            "temperature", "humidity", "condition", "description",
            "time_period", "timestamp", "source"
        ]
        for field in required_fields:
            assert field in fallback, f"Missing field: {field}"


class TestCoordinates:
    """Tests for location coordinates."""
    
    def test_default_coordinates_are_hebron(self):
        """Default coordinates should be Hebron, Palestine."""
        # Hebron approximate coordinates
        assert 31.0 < DEFAULT_LAT < 32.0, "Latitude should be around 31.5"
        assert 35.0 < DEFAULT_LON < 36.0, "Longitude should be around 35.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
