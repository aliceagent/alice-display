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

// Parse battery level from status output
function parseBatteryLevel(output) {
    const batteryMatch = output.match(/🔋 Battery: (\d+)%/);
    const chargingMatch = output.match(/🔌 Charge status: (\w+)/);
    
    return {
        battery: batteryMatch ? parseInt(batteryMatch[1]) : null,
        charging: chargingMatch ? chargingMatch[1].toLowerCase().includes('charging') : false
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