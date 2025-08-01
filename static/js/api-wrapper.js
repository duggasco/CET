// API wrapper to handle v1/v2 migration with feature flags
const apiWrapper = {
    // Check if v2 should be used based on feature flags and rollout percentage
    shouldUseV2() {
        if (!window.featureFlags) return false;
        
        // Check explicit feature flag first
        if (window.featureFlags.useV2DashboardApi !== undefined) {
            return window.featureFlags.useV2DashboardApi;
        }
        
        // Check rollout percentage (for A/B testing)
        if (window.v2RolloutPercentage > 0) {
            // Use a stable hash of user identifier to determine group
            const userHash = this.getUserHash();
            return (userHash % 100) < window.v2RolloutPercentage;
        }
        
        return false;
    },
    
    // Generate stable user hash for A/B testing
    getUserHash() {
        // Use localStorage to persist user group assignment
        let userId = localStorage.getItem('cet_user_id');
        if (!userId) {
            userId = Math.random().toString(36).substring(2) + Date.now().toString(36);
            localStorage.setItem('cet_user_id', userId);
        }
        
        // Simple hash function
        let hash = 0;
        for (let i = 0; i < userId.length; i++) {
            hash = ((hash << 5) - hash) + userId.charCodeAt(i);
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash);
    },
    
    // Unified data loading function
    async loadData(params = {}) {
        if (this.shouldUseV2()) {
            console.log('Using v2 API');
            return await this.loadDataV2(params);
        } else {
            console.log('Using v1 API');
            return await this.loadDataV1(params);
        }
    },
    
    // V2 API implementation with fallback
    async loadDataV2(params) {
        const startTime = Date.now();
        
        try {
            // Convert params to v2 format
            const selections = {
                clients: params.clientIds ? new Set(params.clientIds) : selectionState.clients,
                funds: params.fundNames ? new Set(params.fundNames) : selectionState.funds,
                accounts: params.accountIds ? new Set(params.accountIds) : selectionState.accounts,
                textFilters: params.textFilters || getTextFilters(),
                date: params.date
            };
            
            // Use the v2Api fetchDataV2 function
            const v2Data = await v2Api.fetchDataV2(selections);
            
            // Log successful v2 usage
            this.logApiUsage('v2', '/api/v2/dashboard', Date.now() - startTime);
            
            // Transform to v1 format for compatibility
            return v2Api.transformToV1Format(v2Data);
        } catch (error) {
            console.error('V2 API failed, falling back to v1:', error);
            
            // Log v2 failure
            this.logApiFailure('v2', error);
            
            // Fallback to v1
            return await this.loadDataV1(params);
        }
    },
    
    // V1 API implementation (existing logic)
    async loadDataV1(params) {
        // Determine which v1 endpoint to use based on params
        if (params.clientId && params.fundName) {
            return await this.fetchV1(`/api/client/${params.clientId}/fund/${encodeURIComponent(params.fundName)}${params.queryString || ''}`);
        } else if (params.clientId) {
            return await this.fetchV1(`/api/client/${params.clientId}${params.queryString || ''}`);
        } else if (params.fundName) {
            return await this.fetchV1(`/api/fund/${encodeURIComponent(params.fundName)}${params.queryString || ''}`);
        } else if (params.accountId && params.fundName) {
            return await this.fetchV1(`/api/account/${encodeURIComponent(params.accountId)}/fund/${encodeURIComponent(params.fundName)}${params.queryString || ''}`);
        } else if (params.accountId) {
            return await this.fetchV1(`/api/account/${encodeURIComponent(params.accountId)}${params.queryString || ''}`);
        } else if (params.date) {
            return await this.fetchV1(`/api/date/${params.date}${params.queryString || ''}`);
        } else if (params.useDataEndpoint) {
            return await this.fetchV1(`/api/data${params.queryString || ''}`);
        } else {
            return await this.fetchV1(`/api/overview${params.queryString || ''}`);
        }
    },
    
    // Helper to make v1 fetch calls with error handling
    async fetchV1(url) {
        const startTime = Date.now();
        
        try {
            const response = await fetch(url);
            
            if (!response.ok) {
                // Try to parse error response
                let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorData.error || errorDetail;
                } catch (e) {
                    // Failed to parse error response, use default
                }
                throw new Error(errorDetail);
            }
            
            const data = await response.json();
            
            // Log successful v1 usage
            this.logApiUsage('v1', url.split('?')[0], Date.now() - startTime);
            
            return data;
        } catch (error) {
            // Handle network errors
            if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                throw new Error('Network error: Unable to connect to server');
            }
            
            // Log v1 failure
            this.logApiFailure('v1', error);
            
            throw error;
        }
    },
    
    // Migration helper - log API usage for monitoring
    logApiUsage(apiVersion, endpoint, duration) {
        if (window.console && window.console.log) {
            console.log(`[API Usage] Version: ${apiVersion}, Endpoint: ${endpoint}, Duration: ${duration}ms`);
        }
        
        // Collect metrics
        this.collectMetrics({
            type: 'api_usage',
            version: apiVersion,
            endpoint: endpoint,
            duration: duration,
            timestamp: Date.now()
        });
    },
    
    // Log API failures for monitoring
    logApiFailure(apiVersion, error) {
        console.error(`[API Failure] Version: ${apiVersion}, Error:`, error);
        
        // Collect error metrics
        this.collectMetrics({
            type: 'api_error',
            version: apiVersion,
            error: error.message,
            timestamp: Date.now()
        });
    },
    
    // Collect metrics (buffer for batch sending)
    metricsBuffer: [],
    metricsFlushInterval: null,
    
    collectMetrics(metric) {
        // Add to buffer
        this.metricsBuffer.push(metric);
        
        // Start flush interval if not running
        if (!this.metricsFlushInterval && window.featureFlags?.enableApiMonitoring) {
            this.metricsFlushInterval = setInterval(() => this.flushMetrics(), 30000); // 30 seconds
        }
        
        // Flush immediately if buffer is large
        if (this.metricsBuffer.length >= 50) {
            this.flushMetrics();
        }
    },
    
    // Send buffered metrics to backend
    async flushMetrics() {
        if (!window.featureFlags?.enableApiMonitoring || this.metricsBuffer.length === 0) {
            return;
        }
        
        const metrics = [...this.metricsBuffer];
        this.metricsBuffer = [];
        
        try {
            // TODO: Implement metrics endpoint
            console.log('[Metrics] Would send:', metrics);
        } catch (error) {
            console.error('[Metrics] Failed to send:', error);
            // Re-add metrics to buffer if send failed
            this.metricsBuffer.unshift(...metrics);
        }
    }
};

// Export for use in app.js
window.apiWrapper = apiWrapper;