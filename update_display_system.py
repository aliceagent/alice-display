#!/usr/bin/env python3
"""
Update Alice Display System to use Gallery Integration
Updates the display control system to use the new selection algorithm and gallery database.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def update_display_control():
    """Update the display control system to use the new gallery selection."""
    print("🔄 Updating Display Control System")
    print("=" * 40)
    
    # Change to project root
    os.chdir(Path(__file__).parent)
    
    try:
        # Run the new selection algorithm
        print("🎲 Running enhanced selection algorithm...")
        
        # Use the new selection script
        result = subprocess.run([
            sys.executable, 
            "scripts/select_image_new.py"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ Selection script failed: {result.stderr}")
            return False
        
        print("✅ Selection completed successfully")
        
        # Load the selected image
        selected_file = Path("data/selected-image.json")
        if not selected_file.exists():
            print(f"❌ Selected image file not found: {selected_file}")
            return False
        
        with open(selected_file) as f:
            selected_image = json.load(f)
        
        print(f"📸 Selected: {selected_image.get('name', 'Unknown')}")
        print(f"   Activity: {selected_image.get('activity', 'N/A')}")
        print(f"   Weather: {selected_image.get('weather', 'N/A')}")
        print(f"   Time: {selected_image.get('time_of_day', 'N/A')}")
        
        # Get image URL - prioritize Cloudinary, fallback to local
        image_url = selected_image.get('cloudinary_url')
        if not image_url:
            # Fallback to local generated images
            weather = selected_image.get('weather', 'sunny').lower()
            time = selected_image.get('time_of_day', 'afternoon').lower()
            image_url = f"images/generated/{time}-{weather}.png"
            print(f"⚠️ Using fallback image: {image_url}")
        else:
            print(f"☁️ Using Cloudinary image: {image_url}")
        
        # Load current weather data
        weather_file = Path("data/current-weather.json")
        weather_data = {"condition": "Sunny", "temperature": 20}
        
        if weather_file.exists():
            with open(weather_file) as f:
                weather_data = json.load(f)
        
        # Update display control file with enhanced info
        display_control = {
            "currentImage": {
                "id": selected_image.get('id') or selected_image.get('notion_id', 'unknown'),
                "url": image_url,
                "title": selected_image.get('name', 'Alice'),
                "description": selected_image.get('full_description', ''),
                "activity": selected_image.get('activity', 'Unknown'),
                "location": selected_image.get('location', ''),
                "mood": selected_image.get('mood', ''),
                "weather_context": selected_image.get('weather', ''),
                "time_context": selected_image.get('time_of_day', ''),
                "verified": selected_image.get('verified', False),
                "style_notes": selected_image.get('style_notes', '')
            },
            "weather": {
                "condition": weather_data.get("condition", "Sunny"),
                "temperature": weather_data.get("temperature", 20),
                "humidity": weather_data.get("humidity", 60),
                "description": weather_data.get("description", "clear sky"),
                "icon": weather_data.get("icon", "01d")
            },
            "time": {
                "period": selected_image.get('time_of_day', 'Afternoon'),
                "hour": datetime.now().hour,
                "timezone": "Asia/Hebron"
            },
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "nextUpdate": datetime.now(timezone.utc).replace(
                minute=0, second=0, microsecond=0
            ).isoformat(),
            "gallery_integration": {
                "enabled": True,
                "cloudinary_url": bool(selected_image.get('cloudinary_url')),
                "database_version": "enhanced",
                "selection_algorithm": "gallery-integrated"
            }
        }
        
        # Save updated display control
        with open("display-control.json", "w") as f:
            json.dump(display_control, f, indent=2)
        
        print(f"✅ Updated display-control.json")
        print(f"   Image: {image_url}")
        print(f"   Activity: {display_control['currentImage']['activity']}")
        print(f"   Weather Match: {display_control['currentImage']['weather_context']}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Selection script timed out")
        return False
    except Exception as e:
        print(f"❌ Error updating display: {e}")
        return False

def test_display_update():
    """Test the display update with various weather scenarios."""
    print("\n🧪 Testing Display Update Scenarios")
    print("=" * 40)
    
    test_scenarios = [
        {"condition": "Sunny", "time_period": "Morning"},
        {"condition": "Rainy", "time_period": "Evening"},
        {"condition": "Cloudy", "time_period": "Afternoon"},
    ]
    
    for scenario in test_scenarios:
        print(f"\n🌤️ Testing: {scenario['condition']} + {scenario['time_period']}")
        
        # Create mock weather data
        os.makedirs("data", exist_ok=True)
        with open("data/current-weather.json", "w") as f:
            json.dump({
                "condition": scenario["condition"],
                "time_period": scenario["time_period"],
                "temperature": 22,
                "humidity": 65
            }, f)
        
        # Run selection
        try:
            result = subprocess.run([
                sys.executable,
                "scripts/select_image_new.py",
                "--weather", scenario["condition"],
                "--time", scenario["time_period"],
                "--dry-run"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"   ✅ Selection successful")
                # Parse the output to extract selected image info
                lines = result.stdout.split('\n')
                for line in lines:
                    if "Selected image" in line or "Name:" in line or "Activity:" in line:
                        print(f"      {line.strip()}")
            else:
                print(f"   ❌ Selection failed: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"   ⏱️ Selection timed out")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    """Main function."""
    print("🦜 Alice Display System Update")
    print("🕒", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)
    
    # Test scenarios first
    test_display_update()
    
    # Update the actual display
    print("\n📱 Updating Live Display")
    success = update_display_control()
    
    if success:
        print("\n✅ Display system updated successfully!")
        print("   The display will now use the gallery-integrated selection algorithm")
        print("   Cloudinary URLs will be used when available")
        print("   Enhanced metadata is included in the display control")
    else:
        print("\n❌ Display update failed!")
        print("   Check the logs above for details")

if __name__ == "__main__":
    main()