// V2 API client for unified dashboard endpoint
const v2Api = {
    // Base configuration
    config: {
        endpoint: '/api/v2/dashboard',
        timeout: 30000, // 30 seconds
        retryAttempts: 2,
        retryDelay: 1000 // 1 second
    },

    // Main fetch function
    async fetchDataV2(selections = {}) {
        // Build query parameters
        const params = this.buildQueryParams(selections);
        
        // Generate cache key
        const cacheKey = appCache.generateQueryHash(this.config.endpoint, params);
        
        // Check cache first
        const cachedResult = appCache.getQuery(cacheKey);
        if (cachedResult) {
            console.log('Cache hit for query:', cacheKey);
            return appCache.getDenormalizedData(cachedResult);
        }

        // Make API request
        try {
            const response = await this.makeRequest(params);
            
            // Normalize and cache the response
            const normalized = appCache.normalizeResponse(response);
            appCache.setQuery(cacheKey, normalized);
            
            // Return denormalized data for UI
            return appCache.getDenormalizedData(normalized);
        } catch (error) {
            console.error('V2 API fetch error:', error);
            throw error;
        }
    },

    // Build query parameters from selections
    buildQueryParams(selections) {
        const params = {};

        // Handle client selections
        if (selections.clients && selections.clients.size > 0) {
            params.client_ids = Array.from(selections.clients).join(',');
        }

        // Handle fund selections
        if (selections.funds && selections.funds.size > 0) {
            params.fund_names = Array.from(selections.funds).join(',');
        }

        // Handle account selections
        if (selections.accounts && selections.accounts.size > 0) {
            params.account_ids = Array.from(selections.accounts).join(',');
        }

        // Handle text filters
        if (selections.textFilters) {
            Object.assign(params, selections.textFilters);
        }

        // Handle date selection
        if (selections.date) {
            params.as_of_date = selections.date;
        }

        // Handle selection source
        if (selections.selectionSource) {
            params.selection_source = selections.selectionSource;
        }

        return params;
    },

    // Make the actual HTTP request with retry logic
    async makeRequest(params, attempt = 1) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${this.config.endpoint}?${queryString}` : this.config.endpoint;

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            // Retry logic
            if (attempt < this.config.retryAttempts && !error.message.includes('abort')) {
                console.log(`Retrying request (attempt ${attempt + 1})...`);
                await new Promise(resolve => setTimeout(resolve, this.config.retryDelay));
                return this.makeRequest(params, attempt + 1);
            }
            throw error;
        }
    },

    // Prefetch data for better UX
    async prefetchData(selections) {
        // Prefetch in background without blocking
        setTimeout(() => {
            this.fetchDataV2(selections).catch(err => {
                console.log('Prefetch failed (non-critical):', err);
            });
        }, 0);
    },

    // Invalidate cache based on user actions
    invalidateCache(action, data) {
        switch (action) {
            case 'selection_changed':
                appCache.invalidateBySelections(data);
                break;
            case 'filter_changed':
                appCache.clear(); // Clear all on filter change
                break;
            case 'data_updated':
                // Invalidate specific entities
                if (data.clientId) appCache.invalidateClient(data.clientId);
                if (data.fundName) appCache.invalidateFund(data.fundName);
                if (data.accountId) appCache.invalidateAccount(data.accountId);
                break;
            default:
                console.warn('Unknown invalidation action:', action);
        }
    },

    // Get current cache statistics
    getCacheStats() {
        return appCache.getCacheStats();
    },

    // Transform v2 response to match v1 format (for compatibility)
    transformToV1Format(v2Data) {
        // Extract chart data from nested structure
        const chartData = v2Data.charts || {};
        
        return {
            client_balances: v2Data.client_balances || v2Data.clients || [],
            fund_balances: v2Data.fund_balances || v2Data.funds || [],
            account_details: v2Data.account_details || v2Data.accounts || [],
            recent_history: chartData.recent_history || [],
            long_term_history: chartData.long_term_history || []
        };
    }
};

// Make v2Api available globally
window.v2Api = v2Api;

// Convenience function for migration
window.fetchDataV2 = async function(selections) {
    // Check feature flag
    if (window.featureFlags && window.featureFlags.useV2DashboardApi) {
        const v2Data = await v2Api.fetchDataV2(selections);
        // Transform to v1 format for compatibility during migration
        return v2Api.transformToV1Format(v2Data);
    }
    
    // Fallback to v1 behavior (to be implemented based on existing code)
    console.warn('V2 API not enabled, falling back to v1');
    return null; // Existing v1 code will handle this
};