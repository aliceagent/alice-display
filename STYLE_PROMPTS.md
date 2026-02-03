# Alice Gallery - 5 Style Prompt Templates

## Overview
Each of the 383 Notion database entries will be generated in 5 different artistic styles:

1. **Anime** - Your breakthrough artistic approach ✅
2. **90s Comic Book** - Bold, vibrant comic book aesthetic  
3. **Realistic** - Photorealistic/photography style
4. **Renaissance** - Classical oil painting techniques
5. **Disney** - Classic Disney animation style

## Base Template
All styles include:
- Alice: 20-year-old blonde woman with green eyes and long hair
- Long-sleeved clothing (appropriate to scene/style)
- Green parrot companion with red beak
- Scene description from Notion database entry

---

## 1. ANIME STYLE ✅
**Proven Approach - Your Breakthrough Prompt:**

```
Japanese anime style image: Hand-painted, 2D animated illustration style with soft watercolor and gouache textures. Organic brushstrokes, subtle paper grain, and gently blended colors. Warm, natural color palette with pastel undertones and muted saturation. Soft, diffused lighting with an airy, luminous quality. [ALICE_DESCRIPTION] [SCENE_FROM_DATABASE]. Simplified forms with rounded shapes and minimal linework. Expressive yet understated details, prioritizing mood and atmosphere over realism. A calm, whimsical, storybook aesthetic that feels nostalgic, gentle, and emotionally warm. Painterly, cinematic, and timeless.
```

---

## 2. 90S COMIC BOOK STYLE

```
1990s comic book illustration style: Bold, vibrant colors with high contrast and dramatic lighting. Clean, thick black outlines with cel-shaded coloring technique. Dynamic action poses and exaggerated expressions. Bright primary colors - reds, blues, yellows - with dramatic shadows and highlights. [ALICE_DESCRIPTION] [SCENE_FROM_DATABASE]. Classic superhero comic book aesthetic with Ben-Day dot textures and speech bubble-ready composition. Bold graphic design with flat color fills and strong silhouettes. Reminiscent of X-Men, Spider-Man era artwork with energetic, eye-catching style.
```

---

## 3. REALISTIC STYLE

```
Photorealistic photography style: High-resolution, professional photography with natural lighting and authentic textures. Shallow depth of field with bokeh background blur. Crisp details, natural skin tones, and realistic fabric textures. [ALICE_DESCRIPTION] [SCENE_FROM_DATABASE]. Shot with professional DSLR camera, 85mm lens, natural window lighting. Genuine human expressions and authentic poses. Rich color grading with balanced exposure and professional retouching. Magazine-quality portrait photography with lifelike detail and dimensional lighting.
```

---

## 4. RENAISSANCE STYLE  

```
Renaissance oil painting style: Classical European art technique with rich, deep colors and dramatic chiaroscuro lighting. Smooth brushwork and sfumato blending techniques. Warm golden undertones with deep shadows and luminous highlights. [ALICE_DESCRIPTION] [SCENE_FROM_DATABASE]. Painted in the style of Leonardo da Vinci, Raphael, and Botticelli. Rich oil paint textures with classical composition and renaissance portraiture techniques. Museum-quality fine art with period-appropriate clothing and classical beauty standards. Masterful use of light and shadow with timeless, elegant aesthetic.
```

---

## 5. DISNEY ANIMATION STYLE

```
Classic Disney animation style: Traditional hand-drawn 2D animation with clean, flowing lines and bright, cheerful colors. Rounded, appealing character design with expressive large eyes and smooth animation-ready features. [ALICE_DESCRIPTION] [SCENE_FROM_DATABASE]. Disney's Golden Age aesthetic - think Snow White, Cinderella, Sleeping Beauty era. Warm, inviting color palette with soft shading and dimensional lighting. Character design suitable for animation with clear silhouettes and appealing proportions. Magical, fairy-tale atmosphere with Disney's signature charm and warmth.
```

---

## Variable Replacement System

For each image generation:

1. **[ALICE_DESCRIPTION]** → "Alice, a 20-year-old blonde woman with green eyes and long hair, wearing [scene-appropriate long-sleeved clothing], with her green parrot companion with red beak nearby"

2. **[SCENE_FROM_DATABASE]** → Pull from Notion database:
   - Activity description
   - Location details  
   - Weather/time conditions
   - Mood/atmosphere
   - Props and setting

## Example Implementation

**Database Row 042: "Alice Coding at Dawn"**
- Weather: Clear Night → Dawn
- Time: Dawn  
- Activity: Work
- Location: Modern home office with large windows
- Description: Alice coding as golden dawn light streams through windows

**Generated for each style:**
- `042-anime.png` - Soft watercolor aesthetic
- `042-comic-90s.png` - Bold comic book style  
- `042-realistic.png` - Professional photography
- `042-renaissance.png` - Classical oil painting
- `042-disney.png` - Disney animation style

## Systematic Generation Plan

1. **Fetch all 383 entries** from Notion database
2. **For each entry (1-383):**
   - Generate 5 images (one per style)
   - Upload to Cloudinary with systematic naming
   - Log results and handle errors
3. **Total output**: 383 × 5 = 1,915 images

## Quality Control

- **Test each style** with 5-10 sample images first
- **Refine prompts** based on results
- **Batch generate** in manageable chunks (50-100 at a time)
- **Monitor costs** and API usage
- **Verify uploads** to Cloudinary after each batch