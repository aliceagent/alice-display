#!/usr/bin/env python3
"""
Simple script to update Alice Display System
Usage: python3 update-display.py alice-03
"""

import json
import sys
from datetime import datetime
import subprocess

IMAGES = {
    'alice-01': 'Alice - Coding at Golden Hour',
    'alice-02': 'Alice - Anime Style',  
    'alice-03': 'Alice - Mature Anime',
    'alice-04': 'Alice - Japanese Anime',
    'alice-05': 'Alice - Ghibli Style'
}

def update_display(image_key):
    if image_key not in IMAGES:
        print(f"❌ Unknown image key: {image_key}")
        print(f"Available options: {', '.join(IMAGES.keys())}")
        return False
    
    # Create new control data
    control_data = {
        "currentImage": image_key,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "message": f"Now displaying: {IMAGES[image_key]}"
    }
    
    # Write to file
    try:
        with open('display-control.json', 'w') as f:
            json.dump(control_data, f, indent=4)
        
        print(f"✅ Updated display to: {IMAGES[image_key]}")
        
        # Git commit and push
        try:
            subprocess.run(['git', 'add', 'display-control.json'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', f'Update display to {image_key}: {IMAGES[image_key]}'], 
                          check=True, capture_output=True)
            subprocess.run(['git', 'push'], check=True, capture_output=True)
            
            print("🚀 Changes pushed to GitHub - display will update in ~2 seconds")
            print("🌐 View at: https://aliceagent.github.io/alice-display/")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  File updated locally, but git push failed: {e}")
            print("You may need to manually commit and push the changes")
            
        return True
        
    except Exception as e:
        print(f"❌ Error updating display: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 update-display.py <image-key>")
        print(f"Available images: {', '.join(IMAGES.keys())}")
        for key, title in IMAGES.items():
            print(f"  {key}: {title}")
        sys.exit(1)
    
    image_key = sys.argv[1]
    success = update_display(image_key)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()