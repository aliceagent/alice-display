#!/usr/bin/env python3
"""
Generate AI Art Prompts for Alice Images

Creates detailed prompts for AI image generation services based on
the image database entries.

Usage:
    python generate_prompts.py                    # Generate all prompts
    python generate_prompts.py --weather Sunny    # Filter by weather
    python generate_prompts.py --time Morning     # Filter by time
    python generate_prompts.py --limit 10         # Limit output
    python generate_prompts.py --mvp              # Generate MVP set (24 images)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


# Alice character description for consistent generation
ALICE_DESCRIPTION = """Alice, a beautiful 20-year-old woman with long wavy blonde hair and bright green eyes. 
She has a gentle, warm expression and an elegant yet approachable appearance. 
She wears modest clothing with long sleeves, preferring skirts or dresses in soft, feminine colors.
Her loyal companion is a large, vibrant green parrot with a distinctive red beak, always nearby."""

# Style modifiers for different art styles
STYLE_PRESETS = {
    "anime": "high quality anime artwork, detailed character design, vibrant colors, professional anime style, Studio Ghibli influence",
    "realistic": "photorealistic digital art, detailed lighting, cinematic composition, professional photography style",
    "disney": "Disney animation style, expressive characters, warm colors, magical atmosphere, family-friendly",
    "comic": "90s comic book style, bold lines, dynamic composition, cel-shaded coloring",
    "renaissance": "Renaissance oil painting style, classical composition, rich colors, dramatic lighting, masterwork quality"
}

# Weather-specific atmosphere descriptions
WEATHER_ATMOSPHERE = {
    "Sunny": "bright natural sunlight, warm golden tones, clear blue sky, cheerful atmosphere",
    "Cloudy": "soft diffused light, gray sky, gentle shadows, calm atmosphere",
    "Rainy": "rain drops, wet surfaces, reflections, cozy indoor or umbrella scene, moody blue tones",
    "Stormy": "dramatic lightning, dark clouds, intense atmosphere, wind-blown elements",
    "Snowy": "falling snowflakes, white winter landscape, warm indoor glow, cozy winter scene",
    "Foggy": "misty atmosphere, soft edges, mysterious mood, muted colors",
    "Overcast": "flat gray lighting, subdued colors, contemplative mood",
    "Clear Night": "moonlight, stars, peaceful night scene, soft blue lighting",
    "Partly Cloudy": "scattered clouds, mixed lighting, dynamic sky"
}

# Time-specific lighting descriptions
TIME_LIGHTING = {
    "Dawn": "soft pink and orange sunrise colors, gentle awakening light, peaceful early morning",
    "Early Morning": "fresh morning light, dewdrops, quiet start of day",
    "Morning": "bright morning sun, energetic atmosphere, fresh start",
    "Afternoon": "warm afternoon light, peak daylight, active atmosphere",
    "Golden Hour": "golden sunset light, long shadows, magical warm glow, romantic atmosphere",
    "Evening": "warm indoor lighting, sunset colors, relaxed atmosphere",
    "Night": "artificial warm lighting, cozy indoor scene, peaceful darkness outside",
    "Late Night": "dim lighting, quiet atmosphere, intimate night scene"
}


def generate_prompt(image: dict, style: str = "anime") -> str:
    """Generate a detailed AI art prompt for an image entry."""
    
    title = image.get("title", "Alice")
    weather = image.get("weather", "Sunny")
    time_period = image.get("time_period", "Afternoon")
    activity = image.get("activity", "")
    location = image.get("location", "")
    mood = image.get("mood", "")
    
    # Build the prompt
    parts = []
    
    # Character description
    parts.append(ALICE_DESCRIPTION.strip())
    
    # Activity and scene
    if activity:
        parts.append(f"Alice is {activity.lower()}ing")
    
    # Location
    if location:
        parts.append(f"Setting: {location}")
    
    # Weather atmosphere
    if weather in WEATHER_ATMOSPHERE:
        parts.append(WEATHER_ATMOSPHERE[weather])
    
    # Time lighting
    if time_period in TIME_LIGHTING:
        parts.append(TIME_LIGHTING[time_period])
    
    # Mood
    if mood:
        parts.append(f"Mood: {mood}")
    
    # Style
    if style in STYLE_PRESETS:
        parts.append(STYLE_PRESETS[style])
    
    # Quality boosters
    parts.append("masterpiece, best quality, highly detailed, 4k resolution")
    
    # Negative prompt elements to avoid
    negative = "deformed, ugly, blurry, low quality, text, watermark, signature, extra limbs, bad anatomy"
    
    prompt = ", ".join(parts)
    
    return {
        "id": image.get("id", ""),
        "title": title,
        "prompt": prompt,
        "negative_prompt": negative,
        "weather": weather,
        "time_period": time_period,
        "style": style
    }


def get_mvp_combinations() -> list:
    """Get the MVP set: 3 times × 8 weather = 24 combinations."""
    times = ["Morning", "Afternoon", "Night"]
    weathers = ["Sunny", "Cloudy", "Rainy", "Snowy", "Foggy", "Stormy", "Overcast", "Clear Night"]
    
    return [(t, w) for t in times for w in weathers]


def main():
    parser = argparse.ArgumentParser(description="Generate AI art prompts for Alice images")
    parser.add_argument("--weather", type=str, help="Filter by weather condition")
    parser.add_argument("--time", type=str, help="Filter by time period")
    parser.add_argument("--style", type=str, default="anime", help="Art style preset")
    parser.add_argument("--limit", type=int, help="Limit number of prompts")
    parser.add_argument("--mvp", action="store_true", help="Generate MVP set (24 images)")
    parser.add_argument("--output", type=str, help="Output file path (JSON)")
    parser.add_argument("--database", type=str, default="data/image-database.json", help="Database path")
    args = parser.parse_args()
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent)
    
    # Load database
    db_path = Path(args.database)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    with open(db_path) as f:
        data = json.load(f)
        images = data.get("images", data) if isinstance(data, dict) else data
    
    print(f"📚 Loaded {len(images)} images from database")
    
    # Filter images
    filtered = images
    
    if args.mvp:
        # Get one image for each MVP combination
        mvp_combos = get_mvp_combinations()
        filtered = []
        used_combos = set()
        
        for img in images:
            combo = (img.get("time_period"), img.get("weather"))
            if combo in mvp_combos and combo not in used_combos:
                filtered.append(img)
                used_combos.add(combo)
        
        # Report missing combinations
        missing = set(mvp_combos) - used_combos
        if missing:
            print(f"⚠️ Missing combinations: {len(missing)}")
            for m in list(missing)[:5]:
                print(f"   - {m[0]} + {m[1]}")
    
    if args.weather:
        filtered = [img for img in filtered if img.get("weather", "").lower() == args.weather.lower()]
    
    if args.time:
        filtered = [img for img in filtered if img.get("time_period", "").lower() == args.time.lower()]
    
    if args.limit:
        filtered = filtered[:args.limit]
    
    print(f"🎨 Generating {len(filtered)} prompts with style: {args.style}")
    
    # Generate prompts
    prompts = []
    for img in filtered:
        prompt_data = generate_prompt(img, style=args.style)
        prompts.append(prompt_data)
    
    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "style": args.style,
                "count": len(prompts),
                "prompts": prompts
            }, f, indent=2)
        print(f"📁 Saved to: {output_path}")
    else:
        # Print to stdout
        for i, p in enumerate(prompts[:5], 1):
            print(f"\n{'='*60}")
            print(f"#{i}: {p['title']}")
            print(f"Weather: {p['weather']} | Time: {p['time_period']}")
            print(f"{'='*60}")
            print(f"\n📝 PROMPT:\n{p['prompt']}")
            print(f"\n🚫 NEGATIVE:\n{p['negative_prompt']}")
        
        if len(prompts) > 5:
            print(f"\n... and {len(prompts) - 5} more prompts")
            print(f"Use --output prompts.json to save all prompts")
    
    return prompts


if __name__ == "__main__":
    main()
