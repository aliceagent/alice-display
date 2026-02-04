#!/usr/bin/env python3
"""
Test script for the gallery integration pipeline.
Tests the selection algorithm with the new database structure.
"""

import os
import sys
import json
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))
from scripts.select_image_new import ImageSelector

def test_selection_algorithm():
    """Test the new selection algorithm with mock data."""
    print("🧪 Testing Selection Algorithm Integration")
    print("=" * 50)
    
    # Change to project root
    os.chdir(Path(__file__).parent)
    
    # Test 1: Check if we can load the current database
    print("\n1️⃣ Testing Database Loading")
    try:
        selector = ImageSelector("data/image-database.json")
        print(f"   ✅ Loaded {len(selector.images)} images from database")
        if selector.images:
            sample_img = selector.images[0]
            print(f"   📄 Sample image keys: {list(sample_img.keys())}")
            print(f"   📄 Sample image: {sample_img.get('name', 'N/A')}")
        else:
            print("   ⚠️ No images in database")
    except Exception as e:
        print(f"   ❌ Error loading database: {e}")
        return False
    
    # Test 2: Run statistics
    print("\n2️⃣ Database Statistics")
    try:
        stats = selector.get_stats()
        print(f"   Total images: {stats['total_images']}")
        print(f"   Verified images: {stats['verified_images']}")
        print(f"   With Cloudinary URL: {stats['with_cloudinary_url']}")
        print(f"   Weather distribution: {stats['by_weather']}")
        print(f"   Time distribution: {stats['by_time']}")
        print(f"   Activity distribution: {stats['by_activity']}")
    except Exception as e:
        print(f"   ❌ Error getting stats: {e}")
        return False
    
    # Test 3: Test selection scenarios
    print("\n3️⃣ Testing Selection Scenarios")
    test_scenarios = [
        ("Sunny", "Morning"),
        ("Rainy", "Evening"),
        ("Snowy", "Dawn"),
        ("Cloudy", "Afternoon"),
        ("Stormy", "Night"),
        ("Foggy", "Midday"),
        ("Overcast", "Morning"),
    ]
    
    selection_results = {}
    
    for weather, time in test_scenarios:
        try:
            print(f"\n   🔬 Testing: {weather} + {time}")
            selected = selector.select(weather, time, save_history=False)
            
            if selected:
                name = selected.get('name', 'Unknown')
                activity = selected.get('activity', 'N/A')
                has_url = bool(selected.get('cloudinary_url'))
                verified = selected.get('verified', False)
                
                print(f"      ✅ Selected: {name}")
                print(f"         Activity: {activity}")
                print(f"         Verified: {verified}")
                print(f"         Has Cloudinary URL: {has_url}")
                
                selection_results[f"{weather}_{time}"] = {
                    "success": True,
                    "name": name,
                    "activity": activity,
                    "verified": verified,
                    "has_cloudinary_url": has_url
                }
            else:
                print(f"      ❌ No selection found")
                selection_results[f"{weather}_{time}"] = {
                    "success": False
                }
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            selection_results[f"{weather}_{time}"] = {
                "success": False,
                "error": str(e)
            }
    
    # Test 4: Check Cloudinary URL mapping
    print("\n4️⃣ Testing Cloudinary URL Integration")
    try:
        cloudinary_urls_path = Path("data/cloudinary-urls.json")
        if cloudinary_urls_path.exists():
            with open(cloudinary_urls_path) as f:
                cloudinary_urls = json.load(f)
            print(f"   ✅ Loaded {len(cloudinary_urls)} Cloudinary URLs")
            
            # Test mapping
            if cloudinary_urls:
                sample_filename = list(cloudinary_urls.keys())[0]
                sample_url = cloudinary_urls[sample_filename]
                print(f"   📄 Sample mapping: {sample_filename} → {sample_url[:50]}...")
        else:
            print(f"   ⚠️ Cloudinary URLs file not found: {cloudinary_urls_path}")
    except Exception as e:
        print(f"   ❌ Error loading Cloudinary URLs: {e}")
    
    # Summary
    print("\n📊 Test Summary")
    successful_selections = sum(1 for result in selection_results.values() if result.get("success"))
    total_tests = len(selection_results)
    success_rate = (successful_selections / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"   Selection Success Rate: {successful_selections}/{total_tests} ({success_rate:.1f}%)")
    
    with_urls = sum(1 for result in selection_results.values() if result.get("has_cloudinary_url"))
    print(f"   Images with Cloudinary URLs: {with_urls}/{successful_selections}")
    
    verified_selections = sum(1 for result in selection_results.values() if result.get("verified"))
    print(f"   Verified images selected: {verified_selections}/{successful_selections}")
    
    # Save test results
    test_results_path = Path("data/test-results.json")
    test_results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(test_results_path, "w") as f:
        json.dump({
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "database_stats": stats,
            "selection_results": selection_results,
            "summary": {
                "success_rate": success_rate,
                "with_cloudinary_urls": with_urls,
                "verified_selections": verified_selections
            }
        }, f, indent=2)
    
    print(f"   📁 Test results saved: {test_results_path}")
    
    return success_rate > 80  # Consider test successful if >80% selections work

def check_upload_progress():
    """Check if the Cloudinary upload has made progress."""
    print("\n🚀 Checking Upload Progress")
    
    # Check if upload log files exist
    log_files = list(Path().glob("gallery_upload_log_*.json"))
    if log_files:
        latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
        print(f"   📝 Found upload log: {latest_log}")
        
        with open(latest_log) as f:
            log_data = json.load(f)
        
        total_entries = len(log_data)
        successful_uploads = sum(1 for entry in log_data if entry.get("success"))
        
        print(f"   📊 Upload Progress: {successful_uploads}/{total_entries} successful")
        return successful_uploads, total_entries
    
    # Check if cloudinary URLs file exists
    cloudinary_urls_path = Path("data/cloudinary-urls.json")
    if cloudinary_urls_path.exists():
        with open(cloudinary_urls_path) as f:
            urls = json.load(f)
        print(f"   📁 Cloudinary URLs file exists with {len(urls)} entries")
        return len(urls), 509  # Expected total
    
    print("   ⚠️ No upload progress files found")
    return 0, 509

def main():
    """Main test function."""
    print("🦜 Alice Gallery Integration Test Suite")
    print("🕒", __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # Check upload progress
    uploaded, total = check_upload_progress()
    
    # Run selection algorithm tests
    selection_success = test_selection_algorithm()
    
    print("\n" + "=" * 60)
    print("🎯 Overall Status:")
    print(f"   📤 Upload Progress: {uploaded}/{total} images ({uploaded/total*100:.1f}%)")
    print(f"   🎲 Selection Algorithm: {'✅ PASS' if selection_success else '❌ FAIL'}")
    
    if uploaded > 50 and selection_success:
        print("   🎉 Integration is looking good!")
    elif uploaded == 0:
        print("   ⏳ Waiting for upload to complete...")
    else:
        print("   🔧 Needs attention")

if __name__ == "__main__":
    main()