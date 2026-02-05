# Vacuum Control Setup for Alice Display

The Alice Display now includes Yiko vacuum control! 🤖

## Features

- **Battery Display**: Shows current battery level with appropriate icons
- **Three Actions**: Start cleaning, Stop, Go Home
- **Auto-collapse**: Command Center closes automatically after successful actions
- **Toast Notifications**: Confirms actions and shows status

## Setup Instructions

### 1. Install Dependencies

```bash
cd /Users/agentcaras/.openclaw/workspace/alice-display-website
npm install
```

### 2. Start the Vacuum API Server

```bash
npm start
```

This starts the API server on `http://localhost:3001` with these endpoints:
- `POST /api/vacuum/status` - Get battery level and status
- `POST /api/vacuum/command` - Execute vacuum commands (clean/stop/charge)

### 3. Open Alice Display

Open the Alice Display website (locally or from GitHub Pages). The vacuum panel will now have full functionality!

## How It Works

1. **Tap the 🤖 icon** in the Command Center (bottom-right)
2. **View battery status** - automatically loaded when panel opens
3. **Choose an action**:
   - **▶️ Start Cleaning**: Begins automatic cleaning
   - **⏹️ Stop**: Stops current activity
   - **🏠 Go Home**: Returns to charging dock
4. **Auto-collapse**: Panel and Command Center close after successful actions

## Without API Server

If the API server isn't running, the vacuum panel will still appear but show:
- Battery status as "Yiko Ready" 
- Helpful messages about starting the API server
- Commands will show setup instructions

## Technical Details

- **Device**: Yiko (Ecovacs device index 1)
- **Script**: `/Users/agentcaras/.openclaw/workspace/scripts/ecovacs.mjs`
- **Battery Icons**: 
  - 🔋 Full/Good (50%+)
  - 🪫 Low/Very Low (<50%)
  - 🔌 Charging
- **Timeout**: 30 seconds for commands, 5 seconds for status

## Troubleshooting

### "API server needed" message
- Run `npm start` in the alice-display-website directory
- Refresh the page

### Commands fail
- Check that Ecovacs credentials are in keychain:
  ```bash
  security find-generic-password -s "ecovacs" -a "username"
  security find-generic-password -s "ecovacs" -a "password"
  ```

### Battery status shows "Status unavailable"
- Ensure Yiko is online and connected to Wi-Fi
- Check the API server logs for errors

## Files Modified

- `index-dynamic.html` - Added vacuum panel UI and functionality
- `vacuum-api.js` - New API server for vacuum commands
- `package.json` - Dependencies for API server

Enjoy controlling Yiko directly from Alice Display! 🎉