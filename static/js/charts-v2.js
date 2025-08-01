// V2 Chart implementation using v2 API
const chartsV2 = {
    // Chart instances
    recentChart: null,
    longTermChart: null,
    
    // Chart configuration (matches v1 styling)
    chartConfig: {
        recent: {
            borderColor: '#0085ff',
            backgroundColor: 'rgba(0, 133, 255, 0.1)',
            tension: 0.1,
            pointRadius: 2,
            pointHoverRadius: 4
        },
        longTerm: {
            borderColor: '#00d647',
            backgroundColor: 'rgba(0, 214, 71, 0.1)',
            tension: 0.1,
            pointRadius: 1,
            pointHoverRadius: 3
        }
    },
    
    // Initialize charts (called once on page load)
    init() {
        console.log('[Charts V2] Initializing charts with v2 API');
        this.createChartInstances();
    },
    
    // Create Chart.js instances
    createChartInstances() {
        const recentCtx = document.getElementById('recentChart').getContext('2d');
        const longTermCtx = document.getElementById('longTermChart').getContext('2d');
        
        // Create recent chart (90-day)
        this.recentChart = new Chart(recentCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '90-Day Balance',
                    data: [],
                    ...this.chartConfig.recent
                }]
            },
            options: this.getChartOptions('recent')
        });
        
        // Create long-term chart (3-year)
        this.longTermChart = new Chart(longTermCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '3-Year Balance',
                    data: [],
                    ...this.chartConfig.longTerm
                }]
            },
            options: this.getChartOptions('longTerm')
        });
    },
    
    // Get chart options (matches v1 configuration)
    getChartOptions(type) {
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Balance: ' + formatCurrency(context.raw);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyInMillions(value);
                        }
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true
                    }
                }
            },
            onClick: (event, elements) => this.handleChartClick(event, elements, type)
        };
        
        // Adjust for chart type
        if (type === 'longTerm') {
            options.scales.x.ticks.maxTicksLimit = 12; // Monthly for 3-year
        } else {
            options.scales.x.ticks.maxTicksLimit = 10; // ~Weekly for 90-day
        }
        
        return options;
    },
    
    // Update charts with new data
    async updateCharts(params = {}) {
        try {
            // Use apiWrapper to fetch data
            const data = await apiWrapper.loadData(params);
            
            if (!data) {
                console.error('[Charts V2] No data received');
                return;
            }
            
            // Update recent chart
            if (data.recent_history) {
                this.updateChart(this.recentChart, data.recent_history);
            }
            
            // Update long-term chart
            if (data.long_term_history) {
                this.updateChart(this.longTermChart, data.long_term_history);
            }
            
            console.log('[Charts V2] Charts updated successfully');
        } catch (error) {
            console.error('[Charts V2] Error updating charts:', error);
            // Could show user-friendly error message here
        }
    },
    
    // Update individual chart
    updateChart(chart, historyData) {
        if (!chart || !historyData || historyData.length === 0) {
            return;
        }
        
        // Extract labels and values
        const labels = historyData.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric',
                year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
            });
        });
        
        const values = historyData.map(item => item.balance);
        
        // Update chart data
        chart.data.labels = labels;
        chart.data.datasets[0].data = values;
        
        // Refresh chart
        chart.update('none'); // No animation for smoother updates
    },
    
    // Handle chart click events
    handleChartClick(event, elements, chartType) {
        if (elements.length === 0) return;
        
        const element = elements[0];
        const index = element.index;
        
        // Get the date from the clicked point
        const chart = chartType === 'recent' ? this.recentChart : this.longTermChart;
        const labels = chart.data.labels;
        const clickedDate = labels[index];
        
        // Parse date back to YYYY-MM-DD format
        const date = new Date(clickedDate);
        const formattedDate = date.toISOString().split('T')[0];
        
        console.log(`[Charts V2] Chart clicked - Date: ${formattedDate}`);
        
        // Trigger date selection (integrates with existing date filtering)
        if (window.loadDateData) {
            window.loadDateData(formattedDate);
        }
    },
    
    // Clear charts
    clearCharts() {
        if (this.recentChart) {
            this.recentChart.data.labels = [];
            this.recentChart.data.datasets[0].data = [];
            this.recentChart.update();
        }
        
        if (this.longTermChart) {
            this.longTermChart.data.labels = [];
            this.longTermChart.data.datasets[0].data = [];
            this.longTermChart.update();
        }
    },
    
    // Destroy charts (for cleanup)
    destroy() {
        if (this.recentChart) {
            this.recentChart.destroy();
            this.recentChart = null;
        }
        
        if (this.longTermChart) {
            this.longTermChart.destroy();
            this.longTermChart = null;
        }
    }
};

// Export for global access
window.chartsV2 = chartsV2;