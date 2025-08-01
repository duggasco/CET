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
                datasets: []
            },
            options: this.getChartOptions('recent')
        });
        
        // Create long-term chart (3-year)
        this.longTermChart = new Chart(longTermCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: this.getChartOptions('longTerm')
        });
    },
    
    // Get chart options (matches v1 configuration)
    getChartOptions(type) {
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 750,
                easing: 'easeInOutQuart'
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Balance: ' + formatCurrency(context.raw);
                        }
                    },
                    filter: function(tooltipItem) {
                        // Only show the main dataset (index 0) in tooltip
                        return tooltipItem.datasetIndex === 0;
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyInMillions(value);
                        },
                        padding: 10
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
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
                this.updateChart(this.recentChart, data.recent_history, 'recent');
            }
            
            // Update long-term chart
            if (data.long_term_history) {
                this.updateChart(this.longTermChart, data.long_term_history, 'longTerm');
            }
            
            console.log('[Charts V2] Charts updated successfully');
        } catch (error) {
            console.error('[Charts V2] Error updating charts:', error);
            // Could show user-friendly error message here
        }
    },
    
    // Update charts with provided data (no API call)
    updateChartData(data) {
        if (!data) {
            console.error('[Charts V2] No data provided to updateChartData');
            return;
        }
        
        // Update recent chart
        if (data.recent_history) {
            this.updateChart(this.recentChart, data.recent_history, 'recent');
        }
        
        // Update long-term chart
        if (data.long_term_history) {
            this.updateChart(this.longTermChart, data.long_term_history, 'longTerm');
        }
        
        console.log('[Charts V2] Charts updated with provided data');
    },
    
    // Update individual chart
    updateChart(chart, historyData, chartType) {
        if (!chart || !historyData || historyData.length === 0) {
            return;
        }
        
        // Extract balances - support both v1 (total_balance) and v2 (balance) formats
        const balances = historyData.map(item => item.total_balance || item.balance);
        
        // Calculate statistics like v1
        const avgBalance = balances.reduce((sum, val) => sum + val, 0) / balances.length;
        const maxBalance = Math.max(...balances);
        const minBalance = Math.min(...balances);
        
        // Update the stats in the header (matching v1)
        const statsId = chartType === 'recent' ? 'recentChartStats' : 'longTermChartStats';
        const statsElement = document.getElementById(statsId);
        if (statsElement) {
            statsElement.innerHTML = `
                <span class="stat-item"><span class="stat-label">Max:</span> <span class="stat-value max">${formatCurrency(maxBalance)}</span></span>
                <span class="stat-item"><span class="stat-label">Avg:</span> <span class="stat-value avg">${formatCurrency(avgBalance)}</span></span>
                <span class="stat-item"><span class="stat-label">Min:</span> <span class="stat-value min">${formatCurrency(minBalance)}</span></span>
            `;
        }
        
        // Extract labels using v1 date formatters
        const labels = historyData.map(item => {
            if (chartType === 'recent') {
                return formatDate(item.balance_date || item.date);
            } else {
                return formatDateLong(item.balance_date || item.date);
            }
        });
        
        // Update chart data with v1 styling
        chart.data.labels = labels;
        chart.data.datasets = [
            {
                label: 'Total Balance',
                data: balances,
                borderColor: chartType === 'recent' ? '#0085ff' : '#00d647',
                backgroundColor: chartType === 'recent' ? 'rgba(0, 133, 255, 0.1)' : 'rgba(0, 214, 71, 0.1)',
                borderWidth: 2.5,
                pointRadius: 0,
                pointHoverRadius: chartType === 'recent' ? 5 : 4,
                pointHoverBackgroundColor: chartType === 'recent' ? '#0085ff' : '#00d647',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
                tension: 0.1,
                order: 1
            },
            {
                label: '',  // No label since it's shown in header
                data: Array(balances.length).fill(avgBalance),
                borderColor: 'rgba(107, 114, 128, 0.95)',  // Very dark gray
                borderDash: [5, 5],
                borderWidth: 0.5,  // Very thin
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                order: 2
            },
            {
                label: '',  // No label since it's shown in header
                data: Array(balances.length).fill(maxBalance),
                borderColor: 'rgba(59, 130, 246, 0.95)',  // Very dark blue
                borderDash: [5, 5],
                borderWidth: 0.5,  // Very thin
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                order: 3
            },
            {
                label: '',  // No label since it's shown in header
                data: Array(balances.length).fill(minBalance),
                borderColor: 'rgba(239, 68, 68, 0.95)',  // Very dark red
                borderDash: [5, 5],
                borderWidth: 0.5,  // Very thin
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false,
                order: 4
            }
        ];
        
        // Store original data for click handling
        chart._chartData = historyData;
        
        // Refresh chart with animation like v1
        chart.update();
    },
    
    // Handle chart click events
    handleChartClick(event, elements, chartType) {
        if (elements.length === 0) return;
        
        const element = elements[0];
        const index = element.index;
        
        // Get the chart instance and its data
        const chart = chartType === 'recent' ? this.recentChart : this.longTermChart;
        
        // Get the actual date value from the chart's dataset
        // The chart should have the original date data stored
        let clickedDate;
        if (chart._chartData && chart._chartData[index]) {
            clickedDate = chart._chartData[index].balance_date || chart._chartData[index].date;
        } else {
            // Fallback: try to parse the label
            const label = chart.data.labels[index];
            // This is tricky since we've formatted the dates, but we'll try
            const currentYear = new Date().getFullYear();
            clickedDate = new Date(label + ', ' + currentYear);
            if (isNaN(clickedDate.getTime())) {
                console.error('[Charts V2] Unable to parse date from label:', label);
                return;
            }
            clickedDate = clickedDate.toISOString().split('T')[0];
        }
        
        console.log(`[Charts V2] Chart clicked - Date: ${clickedDate}`);
        
        // Trigger date selection (integrates with existing date filtering)
        if (window.loadDateData) {
            window.loadDateData(clickedDate);
        }
    },
    
    // Clear charts
    clearCharts() {
        if (this.recentChart) {
            this.recentChart.data.labels = [];
            this.recentChart.data.datasets = [];
            this.recentChart.update();
        }
        
        if (this.longTermChart) {
            this.longTermChart.data.labels = [];
            this.longTermChart.data.datasets = [];
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