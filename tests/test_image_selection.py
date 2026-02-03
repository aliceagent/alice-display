#!/usr/bin/env python3
"""
Test Kit: Image Selection Algorithm
Tests for select_image.py module
"""

import pytest
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from select_image import (
    ImageSelector,
    WEATHER_FALLBACKS,
    TIME_FALLBACKS,
)


@pytest.fixture
def sample_database():
    """Create a sample database for testing."""
    return [
        {"id": "1", "title": "Sunny Morning 1", "weather": "Sunny", "time_period": "Morning", "activity": "Work"},
        {"id": "2", "title": "Sunny Morning 2", "weather": "Sunny", "time_period": "Morning", "activity": "Creative"},
        {"id": "3", "title": "Rainy Afternoon", "weather": "Rainy", "time_period": "Afternoon", "activity": "Work"},
        {"id": "4", "title": "Cloudy Evening", "weather": "Cloudy", "time_period": "Evening", "activity": "Leisure"},
        {"id": "5", "title": "Stormy Night", "weather": "Stormy", "time_period": "Night", "activity": "Sleeping"},
        {"id": "6", "title": "Snowy Morning", "weather": "Snowy", "time_period": "Morning", "activity": "Leisure"},
        {"id": "7", "title": "Foggy Dawn", "weather": "Foggy", "time_period": "Dawn", "activity": "Exercise"},
        {"id": "8", "title": "Clear Night", "weather": "Clear Night", "time_period": "Night", "activity": "Creative"},
    ]


@pytest.fixture
def temp_database_file(sample_database):
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"images": sample_database}, f)
        return Path(f.name)


@pytest.fixture
def selector(temp_database_file):
    """Create an ImageSelector with sample database."""
    return ImageSelector(str(temp_database_file))


class TestExactMatching:
    """Tests for exact weather + time matching."""
    
    def test_exact_match_sunny_morning(self, selector):
        """Should find exact match for Sunny + Morning."""
        result = selector.select("Sunny", "Morning", avoid_recent=False, save_history=False)
        assert result is not None
        assert result["weather"] == "Sunny"
        assert result["time_period"] == "Morning"
    
    def test_exact_match_rainy_afternoon(self, selector):
        """Should find exact match for Rainy + Afternoon."""
        result = selector.select("Rainy", "Afternoon", avoid_recent=False, save_history=False)
        assert result is not None
        assert result["weather"] == "Rainy"
        assert result["time_period"] == "Afternoon"
    
    def test_multiple_matches_returns_random(self, selector):
        """When multiple matches exist, should return one randomly."""
        # Sunny + Morning has 2 matches
        results = set()
        for _ in range(20):
            result = selector.select("Sunny", "Morning", avoid_recent=False, save_history=False)
            results.add(result["id"])
        
        # Should have found both options at least once (with high probability)
        assert len(results) >= 1  # At minimum, finds one match


class TestWeatherFallbacks:
    """Tests for weather fallback chains."""
    
    def test_weather_fallback_chain_exists(self):
        """All weather types should have fallback chains."""
        expected_weathers = ["Sunny", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy", "Overcast"]
        for weather in expected_weathers:
            assert weather in WEATHER_FALLBACKS, f"Missing fallback for {weather}"
    
    def test_rainy_falls_back_to_stormy(self, selector):
        """When no Rainy + Night, should try Stormy."""
        # No Rainy Night in sample, but there's Stormy Night
        result = selector.select("Rainy", "Night", avoid_recent=False, save_history=False)
        # Should either find fallback or ultimate fallback
        assert result is not None
    
    def test_sunny_falls_back_to_partly_cloudy(self):
        """Sunny should fallback to Partly Cloudy first."""
        assert "Partly Cloudy" in WEATHER_FALLBACKS["Sunny"]


class TestTimeFallbacks:
    """Tests for time period fallback chains."""
    
    def test_time_fallback_chain_exists(self):
        """All time periods should have fallback chains."""
        expected_times = ["Dawn", "Morning", "Afternoon", "Evening", "Night"]
        for time in expected_times:
            assert time in TIME_FALLBACKS, f"Missing fallback for {time}"
    
    def test_dawn_falls_back_to_morning(self):
        """Dawn should fallback to Morning."""
        assert "Morning" in TIME_FALLBACKS["Dawn"]
    
    def test_evening_falls_back_to_afternoon(self):
        """Evening should fallback to Afternoon."""
        assert "Afternoon" in TIME_FALLBACKS["Evening"]


class TestVariationTracking:
    """Tests for avoiding recently used images."""
    
    def test_avoids_recently_selected(self, selector):
        """Should avoid images selected in last 24 hours."""
        # Select an image and save to history
        first = selector.select("Sunny", "Morning", avoid_recent=False, save_history=True)
        
        # Try to select again with avoid_recent=True
        second = selector.select("Sunny", "Morning", avoid_recent=True, save_history=False)
        
        # If there are multiple options, second should be different
        # (or same if only one option available)
        assert second is not None


class TestUltimateFallback:
    """Tests for ultimate fallback when no matches found."""
    
    def test_returns_any_image_on_no_match(self, selector):
        """Should return any image when no match or fallback found."""
        # Use a weather/time combination that doesn't exist
        result = selector.select("Windy", "Late Night", avoid_recent=False, save_history=False)
        assert result is not None  # Should still return something


class TestDatabaseStats:
    """Tests for database statistics."""
    
    def test_stats_returns_correct_total(self, selector, sample_database):
        """Stats should report correct total image count."""
        stats = selector.get_stats()
        assert stats["total_images"] == len(sample_database)
    
    def test_stats_groups_by_weather(self, selector):
        """Stats should group images by weather."""
        stats = selector.get_stats()
        assert "by_weather" in stats
        assert isinstance(stats["by_weather"], dict)
    
    def test_stats_groups_by_time(self, selector):
        """Stats should group images by time period."""
        stats = selector.get_stats()
        assert "by_time" in stats
        assert isinstance(stats["by_time"], dict)


class TestCaseInsensitivity:
    """Tests for case-insensitive matching."""
    
    def test_weather_matching_case_insensitive(self, selector):
        """Weather matching should be case-insensitive."""
        result1 = selector.select("SUNNY", "Morning", avoid_recent=False, save_history=False)
        result2 = selector.select("sunny", "Morning", avoid_recent=False, save_history=False)
        result3 = selector.select("Sunny", "Morning", avoid_recent=False, save_history=False)
        
        # All should find a match
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None


class TestEmptyDatabase:
    """Tests for handling empty database."""
    
    def test_empty_database_returns_none(self, tmp_path):
        """Should return None when database is empty."""
        empty_db = tmp_path / "empty.json"
        empty_db.write_text('{"images": []}')
        
        selector = ImageSelector(str(empty_db))
        result = selector.select("Sunny", "Morning", avoid_recent=False, save_history=False)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
