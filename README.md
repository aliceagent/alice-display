# 🦜 Alice Display System

A dynamic, weather-responsive display system that shows Alice in different scenarios based on real-time weather conditions and time of day.

![Status](https://img.shields.io/badge/status-live-brightgreen)
![Tests](https://img.shields.io/badge/tests-36%20passing-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![PWA](https://img.shields.io/badge/PWA-offline%20ready-purple)

**🔗 Live Demo:** https://aliceagent.github.io/alice-display/index-dynamic.html

**📖 Operations Guide:** [OPERATIONS.md](OPERATIONS.md)

## 🎯 Overview

Alice Display automatically updates every hour, selecting the perfect Alice image based on:
- **Weather conditions** (Sunny, Cloudy, Rainy, Snowy, Foggy, Stormy, etc.)
- **Time of day** (Dawn, Morning, Afternoon, Evening, Night)
- **Activity matching** (Work, Creative, Leisure, Exercise, Social, Learning, Sleeping)

## 📊 Database

- **383 unique Alice images** defined in Notion
- **8 weather conditions** with fallback chains
- **8 time periods** with intelligent transitions
- **7 activity types** for contextual variety

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Weather API    │───▶│ GitHub Actions  │───▶│  GitHub Pages   │
│ (OpenWeather)   │    │ (Hourly Cron)   │    │  (Static CDN)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                     │                      │
         ▼                     ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Weather Cache  │    │ Image Selection │    │ Display Control │
│ (Fallback Data) │    │   Algorithm     │    │     (JSON)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
alice-display-website/
├── scripts/
│   ├── fetch_weather.py      # Weather API client
│   ├── select_image.py       # Image selection algorithm
│   ├── update_alice.py       # Main orchestrator
│   └── export_notion.py      # Notion database export
├── data/
│   ├── image-database.json   # 383 Alice images
│   ├── current-weather.json  # Cached weather
│   └── selection-history.json # Recent selections
├── tests/
│   ├── test_weather_api.py   # 20 weather tests
│   ├── test_image_selection.py # 16 selection tests
│   └── conftest.py           # Pytest fixtures
├── .github/workflows/
│   ├── update-alice.yml      # Hourly update workflow
│   └── test.yml              # CI test workflow
├── index-dynamic.html        # Main display page
├── display-control.json      # Current display state
├── manifest.json             # PWA manifest
└── README.md
```

## 🚀 Quick Start

### Local Testing

```bash
# Clone the repository
git clone https://github.com/aliceagent/alice-display.git
cd alice-display

# Test with mock weather
python scripts/update_alice.py --mock sunny --force

# Run tests
pytest tests/ -v

# View the display
open index-dynamic.html
```

### Environment Variables

```bash
# Required for live weather
export OPENWEATHER_API_KEY="your_api_key"

# Optional: Notion export
export NOTION_API_KEY="your_notion_key"
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=scripts --cov-report=html

# Test specific module
pytest tests/test_weather_api.py -v
```

### Test Scenarios

```bash
# Test different weather conditions
python scripts/update_alice.py --mock sunny --dry-run
python scripts/update_alice.py --mock rainy --dry-run
python scripts/update_alice.py --mock stormy --dry-run

# View database statistics
python scripts/select_image.py --stats
```

## 🔄 How It Works

1. **GitHub Actions** triggers every hour (`:00`)
2. **Weather API** fetches current conditions for Hebron
3. **Selection Algorithm** finds matching Alice image
4. **Fallback System** activates if no exact match
5. **display-control.json** is updated with new image
6. **GitHub Pages** serves the update
7. **Frontend** smoothly transitions to new image

## 🌤️ Weather Mapping

| OpenWeather Code | Our Category |
|-----------------|--------------|
| 200-232 | Stormy |
| 300-321, 500-504 | Rainy |
| 505-531 | Stormy |
| 600-622 | Snowy |
| 700-749 | Foggy |
| 800 | Sunny |
| 801 | Partly Cloudy |
| 802 | Cloudy |
| 803-804 | Overcast |

## ⏰ Time Periods

| Period | Hours |
|--------|-------|
| Dawn | Sunrise ±1h |
| Morning | 7-11 |
| Afternoon | 12-16 |
| Evening | Sunset ±2h |
| Night | 21-5 |

## 🔗 Links

- **Live Display**: https://aliceagent.github.io/alice-display/
- **Notion Database**: [Alice Image Gallery](https://notion.so/...)
- **Project Plan**: [Technical Blueprint](https://notion.so/...)

## 📝 License

MIT License - Feel free to use and modify!

---

Built with 💜 by Alice 🦜
