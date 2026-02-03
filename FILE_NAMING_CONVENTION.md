# Alice Gallery File Naming Convention

## Overview
- **420 concepts** × **5 artistic styles** = **2,100 total images**
- Each concept gets a sequential row number (001-420)
- Each style gets a consistent suffix

## File Structure
```
alice-display/
├── images/
│   ├── anime/          (420 images)
│   │   ├── 001-anime.png
│   │   ├── 002-anime.png
│   │   └── ... (up to 420-anime.png)
│   ├── comic-90s/      (420 images) 
│   │   ├── 001-comic-90s.png
│   │   ├── 002-comic-90s.png
│   │   └── ... (up to 420-comic-90s.png)
│   ├── realistic/      (420 images)
│   │   ├── 001-realistic.png  
│   │   ├── 002-realistic.png
│   │   └── ... (up to 420-realistic.png)
│   ├── renaissance/    (420 images)
│   │   ├── 001-renaissance.png
│   │   ├── 002-renaissance.png 
│   │   └── ... (up to 420-renaissance.png)
│   └── disney/         (420 images)
│       ├── 001-disney.png
│       ├── 002-disney.png
│       └── ... (up to 420-disney.png)
```

## Row Number Mapping
- **Row 001**: First concept in Notion database
- **Row 002**: Second concept in Notion database  
- **...** 
- **Row 420**: Final concept in Notion database

## Style Suffixes
1. **anime** - Your breakthrough artistic description approach
2. **comic-90s** - Bold comic book style with vibrant colors
3. **realistic** - Photorealistic/photography style  
4. **renaissance** - Classical oil painting, old master techniques
5. **disney** - Classic Disney animation style

## Display System Integration
- **Style selector**: Choose which artistic style to display
- **Concept selector**: Choose which of 420 concepts to display  
- **Combined**: Any concept can be shown in any style
- **URL format**: `images/{style}/{row:03d}-{style}.png`

## Examples
```
Row 001 (Alice Sleeping - Rainy Night):
- 001-anime.png
- 001-comic-90s.png 
- 001-realistic.png
- 001-renaissance.png
- 001-disney.png

Row 042 (Alice Coding at Dawn):
- 042-anime.png
- 042-comic-90s.png
- 042-realistic.png  
- 042-renaissance.png
- 042-disney.png

Row 420 (Final concept):
- 420-anime.png
- 420-comic-90s.png
- 420-realistic.png
- 420-renaissance.png
- 420-disney.png
```

## Benefits
- **Systematic organization**: Easy to find any concept in any style
- **Consistent numbering**: Row numbers match Notion database
- **Scalable**: Easy to add new styles or concepts
- **Programmatic access**: Simple to generate file paths
- **Clear mapping**: Direct correlation between database and files