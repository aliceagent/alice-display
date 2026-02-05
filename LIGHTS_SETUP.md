# Alice Display - Lights Control Setup

This document explains how to set up lights control for the Alice Display Command Center.

## Overview

The Alice Display runs on GitHub Pages (static hosting), so lights control requires a local API server to execute OpenHue commands. The system works as follows:

1. **Frontend (GitHub Pages)**: Alice Display with lights control UI
2. **Local API Server**: Receives commands and executes OpenHue CLI
3. **OpenHue CLI**: Controls Philips Hue lights via bridge

## Setup Instructions

### Prerequisites

1. **Node.js** installed on your local machine
2. **OpenHue CLI** installed and configured:
   ```bash
   brew install openhue/cli/openhue-cli
   openhue setup  # Follow setup instructions
   ```
3. **Hue Bridge** connected and configured

### Running the Lights API Server

1. **Install dependencies**:
   ```bash
   cd /Users/agentcaras/.openclaw/workspace/alice-display-website
   npm install
   ```

2. **Start the API server**:
   ```bash
   npm start
   ```
   
   You should see:
   ```
   🎆 Alice Display Lights API server running on port 3001
   💡 Managing 22 lights
   🌈 19 color-capable lights
   📡 Ready to receive commands from Alice Display
   ```

3. **Test the server** (optional):
   ```bash
   curl http://localhost:3001/api/health
   ```

### Using Lights Control

1. **Open Alice Display** in your browser:
   - **Local**: `file:///Users/agentcaras/.openclaw/workspace/alice-display-website/index-dynamic.html`
   - **GitHub Pages**: Your deployed URL

2. **Access Command Center**:
   - Tap the **⚙️** button in the bottom-right corner
   - Tap the **💡** lights icon

3. **Choose a preset**:
   - **🌙 Bedtime**: All lights to 1% brightness
   - **☀️ Daytime**: All lights to 100% brightness  
   - **🎬 Movie Mode**: All lights to 30% brightness + blue color

## Light Presets

### Bedtime Mode 🌙
- Sets all lights to 1% brightness
- Perfect for nighttime navigation

### Daytime Mode ☀️
- Sets all lights to 100% brightness
- Maximum illumination for daytime activities

### Movie Mode 🎬
- Sets all lights to 30% brightness
- Adds blue color to color-capable lights
- Creates ambient lighting for movie watching

## Architecture

```
┌─────────────────┐    HTTP POST     ┌──────────────────┐    CLI Commands    ┌─────────────┐
│ Alice Display   │ ──────────────►  │ Local API Server │ ───────────────►   │ OpenHue CLI │
│ (GitHub Pages)  │                  │ (localhost:3001) │                    │             │
└─────────────────┘                  └──────────────────┘                    └─────────────┘
                                                                                      │
                                                                                      ▼
                                                                              ┌─────────────┐
                                                                              │ Hue Bridge  │
                                                                              │ + Lights    │
                                                                              └─────────────┘
```

## Troubleshooting

### API Server Not Running
- **Error**: "Failed to fetch" or connection refused
- **Solution**: Make sure the API server is running (`npm start`)

### OpenHue Commands Fail
- **Error**: Commands logged to console but lights don't respond
- **Solution**: 
  1. Test OpenHue CLI manually: `openhue get light`
  2. Ensure Hue Bridge is connected
  3. Run `openhue setup` if needed

### CORS Issues
- **Error**: CORS policy errors in browser console
- **Solution**: The API server includes CORS headers, but make sure you're not running on `file://` protocol for best compatibility

## Manual Command Execution

If the API server isn't available, the lights commands are logged to the browser console. You can copy and run them manually:

```bash
# Example commands for bedtime mode:
openhue set light "6a704bb0-d201-4343-8939-3cd98ee80643" --on --brightness 1
openhue set light "2923d843-cf08-4ed8-aa79-27c722c08bbe" --on --brightness 1
# ... (continues for all lights)
```

## Development

To modify light presets or add new functionality:

1. **Edit presets**: Update `generatePresetCommands()` in `lights-api.js`
2. **Add lights**: Update `lightIds` array in `lights-api.js`
3. **Modify UI**: Edit the lights panel in `index-dynamic.html`

## Security Note

The API server runs on `localhost:3001` and only accepts commands from the local machine. It's designed for personal use and should not be exposed to external networks.