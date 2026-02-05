#!/usr/bin/env node

/**
 * Alice Display - Lights API Server
 * Simple Express server to handle OpenHue light control commands
 * Run this locally while using the Alice Display to enable lights control
 */

const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const app = express();
const port = 3001;

// Enable CORS for all origins (since GitHub Pages will call this)
app.use(cors());
app.use(express.json());

// Light IDs from the Hue system
const lightIds = [
    "6a704bb0-d201-4343-8939-3cd98ee80643", // Kitchen fan 3-24
    "2923d843-cf08-4ed8-aa79-27c722c08bbe", // Kitchen BW fan
    "24da2926-210d-4b34-af37-7ecbf613b576", // Kitchen fan 2- 3/24
    "1c124fbc-0d5f-4d3d-b84c-35fe208cff84", // Kitchen high lamp
    "aa86140d-999d-465e-8c90-ba4d64664e72", // Zahava lamp
    "a02ac2d6-482e-48c9-9f39-397008b6670a", // Outside Flood
    "f0390f66-031a-4131-83de-b31b3fa9a05b", // Hue color lamp 2
    "741900cf-413a-43e3-be6c-6a3f49c23cfb", // Hue color lamp 1
    "9376f857-21b9-4a96-9cf4-92cd50cf987d", // Dining room fan - 4/24
    "9993b466-9fcd-436e-8d78-1e7d835f7b80", // Living room lamp 3/24
    "0dc211bd-b00a-42b6-b484-e49dbe79d05e", // Living room fan 3-24 #2
    "9bd2567a-1683-4eeb-83c7-c66f2b214873", // Downstairs entrance 2
    "fd64c7ac-4a70-4015-87d4-48264e7a9631", // fan above table
    "c3edaddf-d9a0-4277-ad19-9a5ad8b3085c", // Dinning room March 23
    "ebf4d80f-5b73-4a08-84a2-0250808f5533", // Living Room Fan 2
    "ca5e5869-8b91-4135-94e7-69277f8d4beb", // Downstairs entrance 1
    "9f2037a2-116c-4147-96a1-d6098fc44a03", // dinning room strip
    "4122d13e-0c3e-4a06-b752-4b90add03a6f", // Living room tv strip
    "dfc85340-54aa-44e1-82a4-4b6d2d46a8b4", // living room piano
    "7e629fd1-c5c3-4e59-b650-b7d0f342ce7c", // Master bedroom left July 22
    "5c0681a9-d2f9-4716-8844-4d91e996deac", // master bed left
    "346c7450-096e-4857-b0a0-887ef98c3e8b"  // master bed right
];

// Color-capable lights (based on the JSON data)
const colorCapableLights = [
    "6a704bb0-d201-4343-8939-3cd98ee80643", // Kitchen fan 3-24
    "24da2926-210d-4b34-af37-7ecbf613b576", // Kitchen fan 2- 3/24
    "1c124fbc-0d5f-4d3d-b84c-35fe208cff84", // Kitchen high lamp
    "aa86140d-999d-465e-8c90-ba4d64664e72", // Zahava lamp
    "a02ac2d6-482e-48c9-9f39-397008b6670a", // Outside Flood
    "f0390f66-031a-4131-83de-b31b3fa9a05b", // Hue color lamp 2
    "741900cf-413a-43e3-be6c-6a3f49c23cfb", // Hue color lamp 1
    "9376f857-21b9-4a96-9cf4-92cd50cf987d", // Dining room fan - 4/24
    "9993b466-9fcd-436e-8d78-1e7d835f7b80", // Living room lamp 3/24
    "0dc211bd-b00a-42b6-b484-e49dbe79d05e", // Living room fan 3-24 #2
    "fd64c7ac-4a70-4015-87d4-48264e7a9631", // fan above table
    "c3edaddf-d9a0-4277-ad19-9a5ad8b3085c", // Dinning room March 23
    "ebf4d80f-5b73-4a08-84a2-0250808f5533", // Living Room Fan 2
    "9f2037a2-116c-4147-96a1-d6098fc44a03", // dinning room strip
    "4122d13e-0c3e-4a06-b752-4b90add03a6f", // Living room tv strip
    "dfc85340-54aa-44e1-82a4-4b6d2d46a8b4", // living room piano
    "7e629fd1-c5c3-4e59-b650-b7d0f342ce7c", // Master bedroom left July 22
    "5c0681a9-d2f9-4716-8844-4d91e996deac", // master bed left
    "346c7450-096e-4857-b0a0-887ef98c3e8b"  // master bed right
];

function executeOpenHueCommand(command) {
    return new Promise((resolve, reject) => {
        exec(command, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error executing: ${command}`);
                console.error(`Error: ${error.message}`);
                reject(error);
            } else {
                console.log(`✅ Executed: ${command}`);
                if (stdout) console.log(`Output: ${stdout}`);
                resolve(stdout);
            }
        });
    });
}

async function executeMultipleCommands(commands) {
    const results = [];
    
    for (const command of commands) {
        try {
            const result = await executeOpenHueCommand(command);
            results.push({ command, success: true, result });
        } catch (error) {
            results.push({ command, success: false, error: error.message });
        }
        
        // Small delay between commands to avoid overwhelming the bridge
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    return results;
}

function generatePresetCommands(preset) {
    let commands = [];
    
    switch (preset) {
        case 'bedtime':
            // Set all lights to 1% brightness
            lightIds.forEach(lightId => {
                commands.push(`openhue set light "${lightId}" --on --brightness 1`);
            });
            break;
            
        case 'daytime':
            // Set all lights to 100% brightness
            lightIds.forEach(lightId => {
                commands.push(`openhue set light "${lightId}" --on --brightness 100`);
            });
            break;
            
        case 'movie':
            // Set all lights to 30% brightness, add blue color for color-capable lights
            lightIds.forEach(lightId => {
                if (colorCapableLights.includes(lightId)) {
                    commands.push(`openhue set light "${lightId}" --on --brightness 30 --color blue`);
                } else {
                    commands.push(`openhue set light "${lightId}" --on --brightness 30`);
                }
            });
            break;
            
        default:
            throw new Error(`Unknown preset: ${preset}`);
    }
    
    return commands;
}

// API endpoint for lights control
app.post('/api/lights', async (req, res) => {
    try {
        const { preset } = req.body;
        
        if (!preset) {
            return res.status(400).json({
                success: false,
                error: 'Preset is required'
            });
        }
        
        if (!['bedtime', 'daytime', 'movie'].includes(preset)) {
            return res.status(400).json({
                success: false,
                error: 'Invalid preset. Must be: bedtime, daytime, or movie'
            });
        }
        
        console.log(`🎯 Activating ${preset} preset...`);
        
        const commands = generatePresetCommands(preset);
        console.log(`📋 Generated ${commands.length} commands`);
        
        const results = await executeMultipleCommands(commands);
        
        const successful = results.filter(r => r.success).length;
        const failed = results.filter(r => !r.success).length;
        
        if (failed === 0) {
            console.log(`✅ All ${successful} commands executed successfully`);
            res.json({
                success: true,
                message: `${preset} preset activated successfully`,
                stats: { successful, failed },
                results: results
            });
        } else {
            console.log(`⚠️  ${successful} commands succeeded, ${failed} failed`);
            res.json({
                success: true,
                message: `${preset} preset activated with ${failed} failures`,
                stats: { successful, failed },
                results: results
            });
        }
        
    } catch (error) {
        console.error('❌ Error in lights control:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        service: 'Alice Display Lights API',
        timestamp: new Date().toISOString(),
        lights: lightIds.length
    });
});

// Start server
app.listen(port, () => {
    console.log(`🎆 Alice Display Lights API server running on port ${port}`);
    console.log(`💡 Managing ${lightIds.length} lights`);
    console.log(`🌈 ${colorCapableLights.length} color-capable lights`);
    console.log(`📡 Ready to receive commands from Alice Display`);
    console.log(`🔗 Test with: curl http://localhost:${port}/api/health`);
});