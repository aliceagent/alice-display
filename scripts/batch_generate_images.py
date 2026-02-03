#!/usr/bin/env python3
"""
Batch Generate Alice MVP Images

Generates the 24 MVP images (3 times × 8 weather) using DALL-E 3.
Run this script to populate the images directory.

Usage:
    python batch_generate_images.py              # Generate all MVP images
    python batch_generate_images.py --dry-run    # Preview prompts only
    python batch_generate_images.py --start 5    # Start from image #5
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path


# MVP combinations: 3 times × 8 weather = 24 images
MVP_IMAGES = [
    # Morning images
    {"id": "morning-sunny", "time": "Morning", "weather": "Sunny", 
     "prompt": "Anime style: young blonde woman with green eyes doing yoga on balcony with green parrot companion, bright morning sunlight, energetic atmosphere, Studio Ghibli style"},
    {"id": "morning-cloudy", "time": "Morning", "weather": "Cloudy",
     "prompt": "Anime style: young blonde woman with green eyes having breakfast at kitchen table, green parrot on shoulder, soft cloudy morning light through window, cozy atmosphere, Studio Ghibli style"},
    {"id": "morning-rainy", "time": "Morning", "weather": "Rainy",
     "prompt": "Anime style: young blonde woman with green eyes writing in journal by window, rain streaking down glass, green parrot nearby, peaceful rainy morning, warm interior lighting, Studio Ghibli style"},
    {"id": "morning-snowy", "time": "Morning", "weather": "Snowy",
     "prompt": "Anime style: young blonde woman with green eyes enjoying hot cocoa by frosted window, snow falling outside, green parrot companion, cozy winter morning, Studio Ghibli style"},
    {"id": "morning-overcast", "time": "Morning", "weather": "Overcast",
     "prompt": "Anime style: young blonde woman with green eyes reading newspaper with coffee, green parrot on table, gray overcast morning through window, comfortable atmosphere, Studio Ghibli style"},
    {"id": "morning-foggy", "time": "Morning", "weather": "Foggy",
     "prompt": "Anime style: young blonde woman with green eyes doing meditation, misty fog visible through window, green parrot resting nearby, serene foggy morning atmosphere, Studio Ghibli style"},
    {"id": "morning-stormy", "time": "Morning", "weather": "Stormy",
     "prompt": "Anime style: young blonde woman with green eyes watching lightning storm through window, green parrot huddled close, dramatic stormy morning, cozy indoor contrast, Studio Ghibli style"},
    {"id": "morning-clear-night", "time": "Morning", "weather": "Clear Night",
     "prompt": "Anime style: young blonde woman with green eyes at dawn watching last stars fade, green parrot companion, magical transition from night to day, Studio Ghibli style"},
    
    # Afternoon images  
    {"id": "afternoon-sunny", "time": "Afternoon", "weather": "Sunny",
     "prompt": "Anime style: young blonde woman with green eyes at outdoor cafe with laptop, green parrot on table, bright sunny afternoon, cheerful atmosphere, Studio Ghibli style"},
    {"id": "afternoon-cloudy", "time": "Afternoon", "weather": "Cloudy",
     "prompt": "Anime style: young blonde woman with green eyes painting at easel, green parrot watching, soft cloudy afternoon light, creative atmosphere, Studio Ghibli style"},
    {"id": "afternoon-rainy", "time": "Afternoon", "weather": "Rainy",
     "prompt": "Anime style: young blonde woman with green eyes in cozy library reading, rain against windows, green parrot perched nearby, warm lamp light, rainy afternoon, Studio Ghibli style"},
    {"id": "afternoon-snowy", "time": "Afternoon", "weather": "Snowy",
     "prompt": "Anime style: young blonde woman with green eyes baking cookies in warm kitchen, snow falling outside window, green parrot companion, cozy winter afternoon, Studio Ghibli style"},
    {"id": "afternoon-overcast", "time": "Afternoon", "weather": "Overcast",
     "prompt": "Anime style: young blonde woman with green eyes doing crafts at desk, green parrot companion, gray overcast afternoon, focused creative work, Studio Ghibli style"},
    {"id": "afternoon-foggy", "time": "Afternoon", "weather": "Foggy",
     "prompt": "Anime style: young blonde woman with green eyes having tea by window, mysterious fog outside, green parrot nearby, contemplative foggy afternoon, Studio Ghibli style"},
    {"id": "afternoon-stormy", "time": "Afternoon", "weather": "Stormy",
     "prompt": "Anime style: young blonde woman with green eyes playing piano during thunderstorm, green parrot on piano, dramatic lighting from lightning, Studio Ghibli style"},
    {"id": "afternoon-clear-night", "time": "Afternoon", "weather": "Clear Night",
     "prompt": "Anime style: young blonde woman with green eyes at sunset transitioning to dusk, green parrot companion, golden hour light, magical atmosphere, Studio Ghibli style"},
    
    # Night images
    {"id": "night-sunny", "time": "Night", "weather": "Sunny",
     "prompt": "Anime style: young blonde woman with green eyes under moonlight in garden, green parrot companion, clear night sky with stars, peaceful night atmosphere, Studio Ghibli style"},
    {"id": "night-cloudy", "time": "Night", "weather": "Cloudy",
     "prompt": "Anime style: young blonde woman with green eyes reading by lamp light, cloudy night outside window, green parrot sleeping nearby, cozy night scene, Studio Ghibli style"},
    {"id": "night-rainy", "time": "Night", "weather": "Rainy",
     "prompt": "Anime style: young blonde woman with green eyes listening to music with headphones, rain on window at night, green parrot companion, warm lamp glow, Studio Ghibli style"},
    {"id": "night-snowy", "time": "Night", "weather": "Snowy",
     "prompt": "Anime style: young blonde woman with green eyes by fireplace, snow falling outside dark window, green parrot dozing, warm cozy winter night, Studio Ghibli style"},
    {"id": "night-overcast", "time": "Night", "weather": "Overcast",
     "prompt": "Anime style: young blonde woman with green eyes working on computer late night, green parrot resting, soft desk lamp light, overcast night, Studio Ghibli style"},
    {"id": "night-foggy", "time": "Night", "weather": "Foggy",
     "prompt": "Anime style: young blonde woman with green eyes looking out window at foggy night, mysterious atmosphere, green parrot nearby, ethereal foggy night scene, Studio Ghibli style"},
    {"id": "night-stormy", "time": "Night", "weather": "Stormy",
     "prompt": "Anime style: young blonde woman with green eyes cozied up with blanket during night storm, green parrot huddled close, thunder and lightning outside, warm safe interior, Studio Ghibli style"},
    {"id": "night-clear-night", "time": "Night", "weather": "Clear Night",
     "prompt": "Anime style: young blonde woman with green eyes stargazing from balcony, telescope nearby, green parrot companion, beautiful clear starry night, Studio Ghibli style"},
]


def generate_image(image_data: dict, output_dir: Path, gen_script: str) -> bool:
    """Generate a single image using DALL-E 3."""
    
    filename = f"{image_data['id']}.png"
    output_path = output_dir / filename
    
    if output_path.exists():
        print(f"⏭️  Skipping {image_data['id']} (already exists)")
        return True
    
    print(f"🎨 Generating: {image_data['id']} ({image_data['time']} + {image_data['weather']})")
    
    cmd = [
        "python3", gen_script,
        "--model", "dall-e-3",
        "--quality", "standard",
        "--size", "1024x1024",
        "--count", "1",
        "--out-dir", str(output_dir),
        "--prompt", image_data["prompt"]
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # Rename the generated file to our naming convention
            generated_files = list(output_dir.glob("*.png"))
            latest_file = max(generated_files, key=lambda p: p.stat().st_mtime)
            if latest_file.name != filename:
                latest_file.rename(output_path)
            print(f"✅ Generated: {filename}")
            return True
        else:
            print(f"❌ Failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout generating {image_data['id']}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Batch generate MVP images")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts only")
    parser.add_argument("--start", type=int, default=0, help="Start from image number")
    parser.add_argument("--limit", type=int, help="Limit number of images")
    parser.add_argument("--delay", type=int, default=5, help="Delay between images (seconds)")
    args = parser.parse_args()
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "images" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    gen_script = "/opt/homebrew/lib/node_modules/openclaw/skills/openai-image-gen/scripts/gen.py"
    
    if not Path(gen_script).exists():
        print(f"❌ Generation script not found: {gen_script}")
        sys.exit(1)
    
    images_to_generate = MVP_IMAGES[args.start:]
    if args.limit:
        images_to_generate = images_to_generate[:args.limit]
    
    print(f"🎯 Generating {len(images_to_generate)} MVP images")
    print(f"📁 Output directory: {output_dir}\n")
    
    if args.dry_run:
        print("DRY RUN - Prompts only:\n")
        for i, img in enumerate(images_to_generate, 1):
            print(f"#{i}: {img['id']}")
            print(f"    Time: {img['time']}, Weather: {img['weather']}")
            print(f"    Prompt: {img['prompt'][:100]}...")
            print()
        return
    
    # Generate images
    success = 0
    failed = 0
    
    for i, img in enumerate(images_to_generate):
        print(f"\n[{i+1}/{len(images_to_generate)}]")
        
        if generate_image(img, output_dir, gen_script):
            success += 1
        else:
            failed += 1
        
        # Delay between requests to avoid rate limits
        if i < len(images_to_generate) - 1:
            print(f"⏳ Waiting {args.delay}s before next image...")
            time.sleep(args.delay)
    
    print(f"\n{'='*50}")
    print(f"✅ Successfully generated: {success}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Output: {output_dir}")


if __name__ == "__main__":
    main()
