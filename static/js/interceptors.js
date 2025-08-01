// Request/Response interceptors for API monitoring
const interceptors = {
    // Store original fetch
    originalFetch: window.fetch,
    
    // Interceptor configuration
    config: {
        enabled: true,
        logRequests: true,
        logResponses: true,
        measurePerformance: true,
        interceptPatterns: ['/api/']  // Only intercept API calls
    },
    
    // Request interceptors
    requestInterceptors: [],
    
    // Response interceptors
    responseInterceptors: [],
    
    // Add request interceptor
    addRequestInterceptor(interceptor) {
        this.requestInterceptors.push(interceptor);
        return () => {
            const index = this.requestInterceptors.indexOf(interceptor);
            if (index > -1) {
                this.requestInterceptors.splice(index, 1);
            }
        };
    },
    
    // Add response interceptor
    addResponseInterceptor(interceptor) {
        this.responseInterceptors.push(interceptor);
        return () => {
            const index = this.responseInterceptors.indexOf(interceptor);
            if (index > -1) {
                this.responseInterceptors.splice(index, 1);
            }
        };
    },
    
    // Initialize interceptors
    init() {
        if (!this.config.enabled) return;
        
        // Override global fetch
        window.fetch = async (url, options = {}) => {
            // Check if URL should be intercepted
            const shouldIntercept = this.config.interceptPatterns.some(pattern => 
                url.toString().includes(pattern)
            );
            
            if (!shouldIntercept) {
                return this.originalFetch(url, options);
            }
            
            // Create request context
            const context = {
                url: url.toString(),
                method: options.method || 'GET',
                headers: options.headers || {},
                startTime: Date.now(),
                metadata: {}
            };
            
            // Run request interceptors
            for (const interceptor of this.requestInterceptors) {
                try {
                    await interceptor(context, options);
                } catch (error) {
                    console.error('Request interceptor error:', error);
                }
            }
            
            if (this.config.logRequests) {
                console.log(`[API Request] ${context.method} ${context.url}`);
            }
            
            try {
                // Make the actual request (preserve context with call)
                const response = await this.originalFetch.call(window, url, options);
                
                // Clone response for reading
                const responseClone = response.clone();
                
                // Create response context
                const responseContext = {
                    ...context,
                    status: response.status,
                    statusText: response.statusText,
                    headers: Object.fromEntries(response.headers.entries()),
                    duration: Date.now() - context.startTime,
                    ok: response.ok
                };
                
                // Run response interceptors
                for (const interceptor of this.responseInterceptors) {
                    try {
                        await interceptor(responseContext, responseClone);
                    } catch (error) {
                        console.error('Response interceptor error:', error);
                    }
                }
                
                if (this.config.logResponses) {
                    console.log(`[API Response] ${context.method} ${context.url} - ${response.status} (${responseContext.duration}ms)`);
                }
                
                // Collect performance metrics
                if (this.config.measurePerformance) {
                    this.collectPerformanceMetrics(responseContext);
                }
                
                return response;
            } catch (error) {
                // Handle network errors
                const errorContext = {
                    ...context,
                    error: error.message,
                    duration: Date.now() - context.startTime
                };
                
                // Run error interceptors
                for (const interceptor of this.responseInterceptors) {
                    try {
                        await interceptor(errorContext, null, error);
                    } catch (interceptorError) {
                        console.error('Error interceptor error:', interceptorError);
                    }
                }
                
                if (this.config.logResponses) {
                    console.error(`[API Error] ${context.method} ${context.url} - ${error.message} (${errorContext.duration}ms)`);
                }
                
                throw error;
            }
        };
        
        // Add default interceptors
        this.addDefaultInterceptors();
    },
    
    // Add default interceptors
    addDefaultInterceptors() {
        // Performance tracking interceptor
        this.addResponseInterceptor(async (context, response) => {
            if (context.duration > 1000) {
                console.warn(`[Performance] Slow API call: ${context.url} took ${context.duration}ms`);
            }
        });
        
        // Error tracking interceptor
        this.addResponseInterceptor(async (context, response, error) => {
            if (error || !context.ok) {
                const errorData = {
                    url: context.url,
                    method: context.method,
                    status: context.status,
                    error: error?.message || context.statusText,
                    duration: context.duration
                };
                
                // Send to monitoring service
                if (window.apiWrapper) {
                    window.apiWrapper.collectMetrics({
                        type: 'api_error_intercepted',
                        ...errorData,
                        timestamp: Date.now()
                    });
                }
            }
        });
        
        // Cache header interceptor
        this.addRequestInterceptor(async (context, options) => {
            // Add cache control headers if needed
            if (window.featureFlags?.enableAggressiveCaching) {
                options.headers = {
                    ...options.headers,
                    'Cache-Control': 'max-age=300' // 5 minutes
                };
            }
        });
    },
    
    // Collect performance metrics
    performanceBuffer: [],
    collectPerformanceMetrics(context) {
        const metric = {
            endpoint: context.url.split('?')[0],
            method: context.method,
            status: context.status,
            duration: context.duration,
            timestamp: Date.now()
        };
        
        this.performanceBuffer.push(metric);
        
        // Aggregate metrics every minute
        if (!this.performanceInterval) {
            this.performanceInterval = setInterval(() => {
                this.aggregatePerformanceMetrics();
            }, 60000);
        }
    },
    
    // Aggregate performance metrics
    aggregatePerformanceMetrics() {
        if (this.performanceBuffer.length === 0) return;
        
        const metrics = [...this.performanceBuffer];
        this.performanceBuffer = [];
        
        // Group by endpoint
        const aggregated = metrics.reduce((acc, metric) => {
            const key = `${metric.method} ${metric.endpoint}`;
            if (!acc[key]) {
                acc[key] = {
                    endpoint: metric.endpoint,
                    method: metric.method,
                    count: 0,
                    totalDuration: 0,
                    minDuration: Infinity,
                    maxDuration: 0,
                    errors: 0
                };
            }
            
            const agg = acc[key];
            agg.count++;
            agg.totalDuration += metric.duration;
            agg.minDuration = Math.min(agg.minDuration, metric.duration);
            agg.maxDuration = Math.max(agg.maxDuration, metric.duration);
            if (metric.status >= 400) {
                agg.errors++;
            }
            
            return acc;
        }, {});
        
        // Calculate averages
        Object.values(aggregated).forEach(agg => {
            agg.avgDuration = Math.round(agg.totalDuration / agg.count);
            agg.errorRate = (agg.errors / agg.count * 100).toFixed(2) + '%';
        });
        
        console.log('[Performance Summary]', aggregated);
        
        // Send to monitoring service
        if (window.apiWrapper) {
            window.apiWrapper.collectMetrics({
                type: 'performance_summary',
                data: aggregated,
                timestamp: Date.now()
            });
        }
    },
    
    // Disable interceptors
    disable() {
        window.fetch = this.originalFetch;
        this.config.enabled = false;
        if (this.performanceInterval) {
            clearInterval(this.performanceInterval);
            this.performanceInterval = null;
        }
    }
};

// Initialize interceptors
interceptors.init();

// Export for global access
window.interceptors = interceptors;