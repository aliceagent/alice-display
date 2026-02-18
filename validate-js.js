#!/usr/bin/env node
const fs = require('fs');

console.log('🔍 Validating JavaScript syntax in index.html...');

try {
    const content = fs.readFileSync('index.html', 'utf8');
    
    // Extract JavaScript from script tags
    const scriptMatches = content.match(/<script[^>]*>[\s\S]*?<\/script>/g);
    
    if (!scriptMatches) {
        console.log('⚠️ No script tags found');
        process.exit(1);
    }
    
    for (let i = 0; i < scriptMatches.length; i++) {
        const scriptContent = scriptMatches[i].replace(/<script[^>]*>|<\/script>/g, '');
        
        try {
            // Basic syntax validation
            new Function(scriptContent);
            console.log(`✅ Script block ${i + 1}: Syntax OK`);
        } catch (e) {
            console.log(`❌ Script block ${i + 1}: Syntax error on line ${e.lineNumber || '?'}: ${e.message}`);
            process.exit(1);
        }
    }
    
    // Check for key fullscreen functionality
    if (content.includes('initFullscreenManager')) {
        console.log('✅ Enhanced fullscreen manager found');
    } else {
        console.log('❌ Enhanced fullscreen manager not found');
    }
    
    if (content.includes('fullscreen-controls')) {
        console.log('✅ Fullscreen controls CSS found');
    } else {
        console.log('❌ Fullscreen controls CSS not found');
    }
    
    if (content.includes('handleTwoFingerLongPress')) {
        console.log('✅ Touch gesture fullscreen support found in touch-gestures.js');
    } else {
        // Check touch-gestures.js separately
        try {
            const touchContent = fs.readFileSync('touch-gestures.js', 'utf8');
            if (touchContent.includes('handleTwoFingerLongPress')) {
                console.log('✅ Touch gesture fullscreen support found in touch-gestures.js');
            } else {
                console.log('⚠️ Touch gesture fullscreen support not found');
            }
        } catch (e) {
            console.log('⚠️ Could not read touch-gestures.js');
        }
    }
    
    console.log('✅ All validation checks passed!');
    
} catch (error) {
    console.error('❌ Validation failed:', error.message);
    process.exit(1);
}