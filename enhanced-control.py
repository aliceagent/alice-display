#!/usr/bin/env python3
"""
Enhanced Alice Gallery Control System
Supports 420 concepts × 5 styles = 2,100 total images

Usage: 
python3 enhanced-control.py --row 42 --style anime
python3 enhanced-control.py --random
python3 enhanced-control.py --style realistic  # keeps current row
python3 enhanced-control.py --row 100  # keeps current style
"""

import json
import sys
import argparse
import random
import subprocess
from datetime import datetime

STYLES = {
    'anime': 'Anime Style',
    'comic-90s': '90s Comic Book',
    'realistic': 'Realistic',
    'renaissance': 'Renaissance',
    'disney': 'Disney Animation'
}

TOTAL_ROWS = 420

def get_current_config():
    """Get current display configuration"""
    try:
        with open('enhanced-display-control.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default if file doesn't exist
        return {
            "currentRow": 1,
            "currentStyle": "anime",
            "totalRows": TOTAL_ROWS
        }

def update_display(row=None, style=None):
    """Update the display configuration"""
    config = get_current_config()
    
    # Use current values if not specified
    new_row = row if row is not None else config.get("currentRow", 1)
    new_style = style if style is not None else config.get("currentStyle", "anime")
    
    # Validate inputs
    if new_row < 1 or new_row > TOTAL_ROWS:
        print(f"❌ Row must be between 1 and {TOTAL_ROWS}")
        return False
        
    if new_style not in STYLES:
        print(f"❌ Invalid style. Choose from: {', '.join(STYLES.keys())}")
        return False
    
    # Create new config
    new_config = {
        "currentRow": new_row,
        "currentStyle": new_style,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "message": f"Row {new_row:03d} - {STYLES[new_style]}",
        "styles": [
            {
                "id": "anime",
                "name": "Anime Style", 
                "description": "Hand-painted watercolor animation with soft textures"
            },
            {
                "id": "comic-90s",
                "name": "90s Comic Book",
                "description": "Bold comic book style with vibrant colors"  
            },
            {
                "id": "realistic", 
                "name": "Realistic",
                "description": "Photorealistic photography style"
            },
            {
                "id": "renaissance",
                "name": "Renaissance", 
                "description": "Classical oil painting, old master techniques"
            },
            {
                "id": "disney",
                "name": "Disney Animation",
                "description": "Classic Disney animation style"
            }
        ],
        "totalRows": TOTAL_ROWS,
        "availableStyles": len(STYLES),
        "totalImages": TOTAL_ROWS * len(STYLES)
    }
    
    # Write config
    try:
        with open('enhanced-display-control.json', 'w') as f:
            json.dump(new_config, f, indent=4)
            
        print(f"✅ Updated display:")
        print(f"   Row: {new_row:03d}/{TOTAL_ROWS}")
        print(f"   Style: {STYLES[new_style]}")
        print(f"   File: https://res.cloudinary.com/dfzowmhfp/image/upload/alice-gallery/{new_style}/{new_row:03d}-{new_style}.png")
        
        # Git commit and push
        try:
            subprocess.run(['git', 'add', 'enhanced-display-control.json'], 
                          check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 
                           f'Update display: Row {new_row:03d} - {STYLES[new_style]}'], 
                          check=True, capture_output=True)
            subprocess.run(['git', 'push'], check=True, capture_output=True)
            
            print("🚀 Changes pushed to GitHub - display will update in ~2 seconds")
            print("🌐 View at: https://aliceagent.github.io/alice-display/")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Config updated locally, but git push failed: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error updating display: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Enhanced Alice Gallery Control System')
    parser.add_argument('--row', type=int, help=f'Row number (1-{TOTAL_ROWS})')
    parser.add_argument('--style', choices=list(STYLES.keys()), 
                       help='Art style')
    parser.add_argument('--random', action='store_true', 
                       help='Select random row and style')
    parser.add_argument('--list-styles', action='store_true',
                       help='List all available styles')
    parser.add_argument('--status', action='store_true',
                       help='Show current configuration')
    
    args = parser.parse_args()
    
    if args.list_styles:
        print("Available styles:")
        for style_id, style_name in STYLES.items():
            print(f"  {style_id}: {style_name}")
        return
        
    if args.status:
        config = get_current_config()
        print(f"Current display:")
        print(f"  Row: {config['currentRow']:03d}/{TOTAL_ROWS}")
        print(f"  Style: {STYLES.get(config['currentStyle'], 'unknown')}")
        print(f"  File: https://res.cloudinary.com/dfzowmhfp/image/upload/alice-gallery/{config['currentStyle']}/{config['currentRow']:03d}-{config['currentStyle']}.png")
        return
    
    if args.random:
        random_row = random.randint(1, TOTAL_ROWS)
        random_style = random.choice(list(STYLES.keys()))
        print(f"🎲 Random selection: Row {random_row}, Style {STYLES[random_style]}")
        success = update_display(random_row, random_style)
    else:
        success = update_display(args.row, args.style)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()