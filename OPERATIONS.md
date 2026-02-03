# Alice Display System — Operations Guide

## 🦜 Overview

Alice Display is a dynamic weather-responsive display system that shows anime-style images of Alice based on real-time weather conditions in Hebron, Palestine.

**Live URL:** https://aliceagent.github.io/alice-display/index-dynamic.html

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  OpenWeatherMap │────▶│  GitHub Actions  │────▶│  GitHub Pages   │
│      API        │     │  (Hourly Cron)   │     │  (Static Host)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Python Scripts  │
                        │  - fetch_weather │
                        │  - select_image  │
                        │  - update_alice  │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ display-control  │
                        │     .json        │
                        └──────────────────┘
```

---

## 📁 Project Structure

```
alice-display-website/
├── .github/workflows/
│   ├── update-alice.yml    # Hourly weather update cron
│   └── test.yml            # CI tests on push
├── scripts/
│   ├── fetch_weather.py    # Weather API client
│   ├── select_image.py     # Image selection algorithm
│   ├── update_alice.py     # Main orchestrator
│   ├── export_notion.py    # Notion database export
│   ├── generate_prompts.py # AI art prompt generator
│   └── batch_generate_images.py  # DALL-E 3 batch generation
├── data/
│   ├── image-database.json # 389 image entries
│   ├── generated-images.json # Generated image manifest
│   ├── weather-cache.json  # Last known weather (fallback)
│   └── selection-history.json # Recent selections (variety)
├── images/generated/       # DALL-E 3 generated PNGs
├── tests/                  # Pytest test suite (36 tests)
├── index-dynamic.html      # Main PWA frontend
├── display-control.json    # Current display state
├── manifest.json           # PWA manifest
├── sw.js                   # Service worker (offline)
└── OPERATIONS.md           # This file
```

---

## ⚙️ Configuration

### Environment Variables (GitHub Secrets)

| Secret | Description |
|--------|-------------|
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key |

### Location Settings

- **City:** Hebron, Palestine
- **Coordinates:** 31.5326°N, 35.0998°E
- **Timezone:** Asia/Hebron (GMT+2/+3)

### Weather Categories

| Category | OpenWeather Codes |
|----------|-------------------|
| Sunny | 800 (clear sky) |
| Partly Cloudy | 801, 802 |
| Cloudy | 803, 804 |
| Overcast | 804 |
| Rainy | 500-531 |
| Stormy | 200-232 |
| Snowy | 600-622 |
| Foggy | 701-762 |
| Clear Night | 800 (night) |

### Time Periods

| Period | Hours |
|--------|-------|
| Dawn | Sunrise ± 1 hour |
| Morning | 6:00 - 11:59 |
| Afternoon | 12:00 - 16:59 |
| Evening | 17:00 - 20:59 |
| Night | 21:00 - 5:59 |

---

## 🔄 How Updates Work

1. **GitHub Actions** runs hourly at minute 0
2. **fetch_weather.py** gets current Hebron weather
3. **select_image.py** picks matching image (with fallbacks)
4. **update_alice.py** updates `display-control.json`
5. **Git push** deploys to GitHub Pages
6. **Frontend** polls every 5 minutes, crossfades new image

### Fallback Logic

**Weather fallbacks:**
- Rainy → Stormy → Cloudy → Overcast
- Snowy → Cloudy → Overcast
- Foggy → Cloudy → Overcast

**Time fallbacks:**
- Dawn → Morning
- Evening → Afternoon

**Variety:** Same image won't repeat within 24 hours

---

## 🛠️ Manual Operations

### Trigger Manual Update

```bash
# Via GitHub CLI
gh workflow run update-alice.yml

# Or via Actions UI
# Go to: Actions → Update Alice Display → Run workflow
```

### Test with Mock Weather

```bash
cd alice-display-website
python3 scripts/update_alice.py --mock sunny --force
python3 scripts/update_alice.py --mock rainy --time evening --force
```

### Run Tests

```bash
cd alice-display-website
pytest tests/ -v
```

### Generate New Image

```bash
python3 scripts/batch_generate_images.py \
  --weather Sunny --time Morning --id morning-sunny-v2
```

### Clear Service Worker Cache

In browser console:
```javascript
caches.keys().then(names => names.forEach(n => caches.delete(n)));
```

---

## 🚨 Troubleshooting

### Image Not Updating

1. Check GitHub Actions ran: [Actions Tab](https://github.com/aliceagent/alice-display/actions)
2. Check `display-control.json` updated
3. Hard refresh browser: `Ctrl+Shift+R`
4. Clear service worker cache (see above)

### Weather API Errors

1. Check API key in GitHub Secrets
2. Verify quota: [OpenWeatherMap Dashboard](https://home.openweathermap.org/)
3. Check `data/weather-cache.json` for fallback

### Missing Image Combination

1. Check `data/image-database.json` for entry
2. Generate missing image with `batch_generate_images.py`
3. Fallback chain will use similar image

### GitHub Actions Failing

1. Check workflow logs for error
2. Common issues:
   - API rate limit (wait 1 hour)
   - Invalid JSON (check script output)
   - Git push conflict (re-run workflow)

---

## 📊 Monitoring

### Health Checks

- **Frontend:** Visit live URL, check image loads
- **Actions:** Check [workflow runs](https://github.com/aliceagent/alice-display/actions)
- **Data:** Verify `display-control.json` timestamp

### Key Files to Watch

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `display-control.json` | Current image | Hourly |
| `data/weather-cache.json` | Weather backup | Hourly |
| `data/selection-history.json` | Variety tracking | Hourly |

---

## 📱 PWA Features

- **Offline:** Works without internet (cached)
- **Install:** Add to home screen prompt
- **Fullscreen:** No browser chrome
- **Auto-update:** Checks for new content

### Supported Browsers

| Browser | Install | Offline |
|---------|---------|---------|
| Chrome (Android) | ✅ | ✅ |
| Safari (iOS) | ✅ (manual) | ✅ |
| Chrome (Desktop) | ✅ | ✅ |
| Firefox | ❌ | ✅ |
| Edge | ✅ | ✅ |

---

## 🔐 Security

- API keys stored in GitHub Secrets (not in code)
- No sensitive data in frontend
- Service worker scoped to same origin

---

## 📈 Future Improvements

- [ ] Cloudinary CDN for faster image loads
- [ ] More image variety (420 total planned)
- [ ] Weather alerts overlay
- [ ] Multiple location support
- [ ] Admin dashboard

---

## 📞 Support

- **Repository:** https://github.com/aliceagent/alice-display
- **Notion Blueprint:** [Alice Display Implementation](https://notion.so/2fc41906-4d30-81f4-96a0-dad7f895d8a3)

---

*Last updated: 2026-02-03*
