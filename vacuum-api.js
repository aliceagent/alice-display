#!/usr/bin/env node
/**
 * Simple Express server to provide vacuum control API for Alice Display
 * Usage: node vacuum-api.js
 * 
 * Endpoints:
 *   POST /api/vacuum/status - Get battery and status
 *   POST /api/vacuum/command - Execute vacuum command (clean/stop/charge)
 */

const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const cors = require('cors');

const app = express();
const port = process.env.PORT || 3001;

// Enable CORS for the Alice Display website
app.use(cors({
    origin: [
        'http://localhost:3000',
        'http://localhost:8080',
        'https://aliceagent.github.io',
        'file://'  // Allow local file access during development
    ]
}));

app.use(express.json());

// Path to the ecovacs script
const ECOVACS_SCRIPT = '/Users/agentcaras/.openclaw/workspace/scripts/ecovacs.mjs';

// Telegram notification config
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = '450517777';  // Jonathan's chat ID

// Send Telegram notification
async function sendTelegramNotification(message) {
    if (!TELEGRAM_BOT_TOKEN) {
        console.log('⚠️ TELEGRAM_BOT_TOKEN not set, skipping notification');
        return;
    }
    
    try {
        const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML'
            })
        });
        
        if (response.ok) {
            console.log('📱 Telegram notification sent');
        } else {
            console.error('📱 Telegram notification failed:', await response.text());
        }
    } catch (error) {
        console.error('📱 Telegram notification error:', error.message);
    }
}

// Execute ecovacs command with timeout
function executeVacuumCommand(command, deviceIndex = 1) {
    return new Promise((resolve, reject) => {
        const cmd = `node "${ECOVACS_SCRIPT}" ${command} ${deviceIndex}`;
        
        exec(cmd, { timeout: 30000 }, (error, stdout, stderr) => {
            if (error) {
                console.error('Command error:', error);
                reject(error);
                return;
            }
            
            if (stderr) {
                console.error('Command stderr:', stderr);
            }
            
            console.log('Command stdout:', stdout);
            resolve(stdout);
        });
    });
}

// Parse battery level and status from output
function parseBatteryLevel(output) {
    const batteryMatch = output.match(/🔋 Battery: (\d+)%/);
    const chargingMatch = output.match(/🔌 Charge status: (\w+)/);
    const cleanMatch = output.match(/📍 Clean status: (\w+)/);
    
    return {
        battery: batteryMatch ? parseInt(batteryMatch[1]) : null,
        charging: chargingMatch ? chargingMatch[1].toLowerCase().includes('charging') : false,
        clean_status: cleanMatch ? cleanMatch[1].toLowerCase() : 'unknown'
    };
}

// API endpoint to get vacuum status
app.post('/api/vacuum/status', async (req, res) => {
    try {
        const { device = 1 } = req.body;
        
        console.log(`📱 Getting status for device ${device}...`);
        const output = await executeVacuumCommand('status', device);
        const batteryInfo = parseBatteryLevel(output);
        
        res.json({
            success: true,
            ...batteryInfo,
            raw: output
        });
        
    } catch (error) {
        console.error('Status request failed:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// API endpoint to execute vacuum commands
app.post('/api/vacuum/command', async (req, res) => {
    try {
        const { device = 1, command } = req.body;
        
        // Validate command
        if (!['clean', 'stop', 'charge'].includes(command)) {
            return res.status(400).json({
                success: false,
                error: 'Invalid command. Use: clean, stop, or charge'
            });
        }
        
        console.log(`🤖 Executing ${command} for device ${device}...`);
        const output = await executeVacuumCommand(command, device);
        
        // Send Telegram notification for clean command
        if (command === 'clean') {
            sendTelegramNotification('🤖 <b>Yiko started cleaning!</b>\n\nTriggered from Alice Display Command Center.');
        } else if (command === 'stop') {
            sendTelegramNotification('⏹️ <b>Yiko stopped</b>\n\nCleaning paused via Command Center.');
        } else if (command === 'charge') {
            sendTelegramNotification('🏠 <b>Yiko going home</b>\n\nReturning to charging dock.');
        }
        
        res.json({
            success: true,
            command: command,
            raw: output
        });
        
    } catch (error) {
        console.error('Command execution failed:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString()
    });
});

// Start server
app.listen(port, () => {
    console.log(`🤖 Vacuum API server running on port ${port}`);
    console.log(`📱 Endpoints:`);
    console.log(`   POST http://localhost:${port}/api/vacuum/status`);
    console.log(`   POST http://localhost:${port}/api/vacuum/command`);
    console.log(`   GET  http://localhost:${port}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 Shutting down vacuum API server...');
    process.exit(0);
});