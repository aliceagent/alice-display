/**
 * Alice Display Vacuum API Configuration
 * 
 * Handles environment detection and API endpoint configuration
 * for vacuum control via local API or OpenClaw webhook
 */

class VacuumAPIConfig {
    constructor() {
        this.config = this.detectEnvironment();
        console.log('Vacuum API Config:', this.config);
    }
    
    /**
     * Detect environment and configure appropriate API endpoints
     */
    detectEnvironment() {
        const location = window.location;
        
        // Check if we're on GitHub Pages or external hosting
        const isExternal = (
            location.protocol === 'https:' && 
            (
                location.hostname.includes('github.io') ||
                location.hostname.includes('vercel.app') ||
                location.hostname.includes('netlify.app') ||
                (location.hostname !== 'localhost' && location.hostname !== '127.0.0.1')
            )
        );
        
        // Check if we're on local file system
        const isLocalFile = location.protocol === 'file:';
        
        if (isExternal) {
            // External hosting - use OpenClaw webhook
            return {
                type: 'webhook',
                baseUrl: this.getWebhookBaseUrl(),
                statusEndpoint: '/webhook/vacuum/status',
                commandEndpoint: '/webhook/vacuum/command',
                authRequired: true,
                authToken: this.getWebhookToken(),
                timeout: {
                    status: 10000,
                    command: 30000
                }
            };
        } else {
            // Local development - try local API first, fallback to webhook
            return {
                type: 'local-with-fallback',
                primaryUrl: 'http://localhost:3001',
                primaryStatusEndpoint: '/api/vacuum/status',
                primaryCommandEndpoint: '/api/vacuum/command',
                fallbackUrl: 'http://127.0.0.1:18790',
                fallbackStatusEndpoint: '/webhook/vacuum/status',
                fallbackCommandEndpoint: '/webhook/vacuum/command',
                authRequired: false, // For local API
                fallbackAuthRequired: true,
                fallbackAuthToken: this.getWebhookToken(),
                timeout: {
                    status: 5000,
                    command: 30000
                }
            };
        }
    }
    
    /**
     * Get OpenClaw webhook base URL
     */
    getWebhookBaseUrl() {
        // In production, this would be the actual OpenClaw Gateway URL
        // For MVP, we'll use the local webhook server
        const webhookUrl = window.VACUUM_WEBHOOK_URL || 'http://127.0.0.1:18790';
        return webhookUrl;
    }
    
    /**
     * Get webhook authentication token
     */
    getWebhookToken() {
        // In production, this would be fetched securely or embedded
        // For MVP, we'll use a known development token
        const devToken = window.VACUUM_WEBHOOK_TOKEN || '5b062bb748027ccabdc37f46b25b3e062e4c11b2e23c5ec3c5a44e7e7b8c2f4a';
        return devToken;
    }
    
    /**
     * Make vacuum API request with appropriate configuration
     */
    async makeVacuumRequest(endpoint, data = {}) {
        const config = this.config;
        
        if (config.type === 'webhook') {
            return await this.makeWebhookRequest(endpoint, data);
        } else if (config.type === 'local-with-fallback') {
            return await this.makeLocalWithFallbackRequest(endpoint, data);
        } else {
            throw new Error('Unknown API configuration type');
        }
    }
    
    /**
     * Make webhook request
     */
    async makeWebhookRequest(endpoint, data = {}) {
        const config = this.config;
        const url = config.baseUrl + (endpoint === 'status' ? config.statusEndpoint : config.commandEndpoint);
        const timeout = endpoint === 'status' ? config.timeout.status : config.timeout.command;
        
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (config.authRequired && config.authToken) {
            headers['Authorization'] = `Bearer ${config.authToken}`;
        }
        
        console.log('Making webhook request:', { url, data, timeout });
        
        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(data),
            signal: AbortSignal.timeout(timeout)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'API request failed');
        }
        
        return result;
    }
    
    /**
     * Make local request with webhook fallback
     */
    async makeLocalWithFallbackRequest(endpoint, data = {}) {
        const config = this.config;
        
        // Try local API first
        try {
            const url = config.primaryUrl + (endpoint === 'status' ? config.primaryStatusEndpoint : config.primaryCommandEndpoint);
            console.log('Trying local API:', url);
            
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
                signal: AbortSignal.timeout(config.timeout.status)
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Local API success');
                return result;
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (localError) {
            console.warn('Local API failed, trying webhook fallback:', localError.message);
            
            // Fallback to webhook
            try {
                const fallbackUrl = config.fallbackUrl + (endpoint === 'status' ? config.fallbackStatusEndpoint : config.fallbackCommandEndpoint);
                const timeout = endpoint === 'status' ? config.timeout.status : config.timeout.command;
                
                const headers = {
                    'Content-Type': 'application/json'
                };
                
                if (config.fallbackAuthRequired && config.fallbackAuthToken) {
                    headers['Authorization'] = `Bearer ${config.fallbackAuthToken}`;
                }
                
                console.log('Trying webhook fallback:', fallbackUrl);
                
                const response = await fetch(fallbackUrl, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify(data),
                    signal: AbortSignal.timeout(timeout)
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                if (!result.success) {
                    throw new Error(result.error || 'Webhook request failed');
                }
                
                console.log('Webhook fallback success');
                return result;
            } catch (webhookError) {
                console.error('Both local and webhook APIs failed:', { localError: localError.message, webhookError: webhookError.message });
                throw new Error(`API unavailable: ${localError.message} (webhook: ${webhookError.message})`);
            }
        }
    }
    
    /**
     * Get configuration info for debugging
     */
    getConfigInfo() {
        return {
            type: this.config.type,
            environment: window.location.protocol + '//' + window.location.hostname,
            endpoints: this.config.type === 'webhook' ? 
                { status: this.config.baseUrl + this.config.statusEndpoint, command: this.config.baseUrl + this.config.commandEndpoint } :
                { primary: this.config.primaryUrl, fallback: this.config.fallbackUrl },
            auth: this.config.authRequired || this.config.fallbackAuthRequired,
            timeout: this.config.timeout
        };
    }
}

// Export for use in main application
window.VacuumAPIConfig = VacuumAPIConfig;