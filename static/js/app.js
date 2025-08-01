// Global variables
let recentChart = null;
let longTermChart = null;
let currentFilter = { type: 'overview', value: null };
let allData = null;
let isMobile = false;

// Selection state management
let selectionState = {
    clients: new Set(),     // Set of selected client IDs
    funds: new Set(),       // Set of selected fund names
    accounts: new Set()     // Set of selected account IDs
};

// Text filter state
let textFilters = {
    fundTicker: '',
    clientName: '',
    accountNumber: ''
};

// Get current selection parameters for v2 API
function getCurrentSelectionParams() {
    // Determine selection source (when selections are from a single table only)
    let selectionSource = null;
    const hasClients = selectionState.clients.size > 0;
    const hasFunds = selectionState.funds.size > 0;
    const hasAccounts = selectionState.accounts.size > 0;
    
    // Count how many TABLES have selections (not how many items are selected)
    const tablesWithSelections = (hasClients ? 1 : 0) + (hasFunds ? 1 : 0) + (hasAccounts ? 1 : 0);
    
    // If only one table has selections (regardless of how many items), set selection source
    if (tablesWithSelections === 1) {
        if (hasClients) selectionSource = 'client';
        else if (hasFunds) selectionSource = 'fund';
        else if (hasAccounts) selectionSource = 'account';
    }
    
    return {
        clientIds: Array.from(selectionState.clients),
        fundNames: Array.from(selectionState.funds),
        accountIds: Array.from(selectionState.accounts),
        textFilters: textFilters,
        date: currentFilter.type === 'date' ? currentFilter.value : null,
        queryString: buildQueryString(),
        selectionSource: selectionSource
    };
}

// Chart manager to handle v1/v2 chart routing
const chartManager = {
    // Update charts based on feature flag
    update: function(data) {
        if (window.featureFlags?.useV2Charts) {
            // V2 charts should use the data directly if available
            console.log('[Chart Manager] Using v2 charts');
            if (data && (data.recent_history || data.long_term_history)) {
                // Data already has chart data, update directly
                chartsV2.updateChartData(data);
            } else {
                // No chart data provided, let v2 fetch its own
                chartsV2.updateCharts(getCurrentSelectionParams());
            }
        } else {
            // V1 charts use passed data
            console.log('[Chart Manager] Using v1 charts');
            if (data && data.recent_history) {
                updateRecentChart(data.recent_history);
            }
            if (data && data.long_term_history) {
                updateLongTermChart(data.long_term_history);
            }
        }
    },
    
    // Initialize charts
    init: function() {
        if (window.featureFlags?.useV2Charts) {
            console.log('[Chart Manager] Initializing v2 charts');
            chartsV2.init();
        }
        // V1 charts initialize inline, no init needed
    },
    
    // Clear charts
    clear: function() {
        if (window.featureFlags?.useV2Charts) {
            chartsV2.clearCharts();
        } else {
            // Clear v1 charts
            updateRecentChart([]);
            updateLongTermChart([]);
        }
    }
};

// Table manager to handle v1/v2 table routing
const tableManager = {
    // Update tables based on feature flag
    update: async function(data) {
        if (window.featureFlags?.useV2Tables) {
            // V2 tables fetch their own data
            console.log('[Table Manager] Using v2 tables');
            const params = getCurrentSelectionParams();
            return await tablesV2.updateTables(params);
        } else {
            // V1 tables use passed data
            console.log('[Table Manager] Using v1 tables');
            updateClientTable(data.client_balances || []);
            updateFundTable(data.fund_balances || []);
            updateAccountTable(data.account_details || []);
            return data;
        }
    },
    
    // Initialize tables
    init: function() {
        if (window.featureFlags?.useV2Tables) {
            console.log('[Table Manager] Initializing v2 tables');
            tablesV2.init();
        }
        // V1 tables don't need initialization
    },
    
    // Clear tables
    clear: function() {
        if (window.featureFlags?.useV2Tables) {
            tablesV2.clearTables();
        } else {
            // Clear v1 tables
            updateClientTable([]);
            updateFundTable([]);
            updateAccountTable([]);
        }
    },
    
    // Update individual tables (for backwards compatibility)
    updateClientTable: function(data) {
        if (window.featureFlags?.useV2Tables) {
            tablesV2.updateClientTable(data);
        } else {
            updateClientTable(data);
        }
    },
    
    updateFundTable: function(data) {
        if (window.featureFlags?.useV2Tables) {
            tablesV2.updateFundTable(data);
        } else {
            updateFundTable(data);
        }
    },
    
    updateAccountTable: function(data) {
        if (window.featureFlags?.useV2Tables) {
            tablesV2.updateAccountTable(data);
        } else {
            updateAccountTable(data);
        }
    }
};

// Mobile detection function
function detectMobile() {
    // Check multiple conditions for mobile detection
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
    const touchSupport = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const screenWidth = window.innerWidth <= 768;
    
    return mobileRegex.test(userAgent) || (touchSupport && screenWidth);
}

// Apply mobile class to body
function applyMobileClass() {
    isMobile = detectMobile();
    if (isMobile) {
        document.body.classList.add('mobile');
        // Also fix html element for mobile scrolling
        document.documentElement.style.height = 'auto';
        document.documentElement.style.overflow = 'visible';
    } else {
        document.body.classList.remove('mobile');
        // Reset html element for desktop
        document.documentElement.style.height = '100%';
        document.documentElement.style.overflow = 'hidden';
    }
}

// Build query string with text filters
function buildQueryString(includeSelections = false) {
    const params = new URLSearchParams();
    
    if (textFilters.fundTicker) {
        params.append('fund_ticker', textFilters.fundTicker);
    }
    if (textFilters.clientName) {
        params.append('client_name', textFilters.clientName);
    }
    if (textFilters.accountNumber) {
        params.append('account_number', textFilters.accountNumber);
    }
    
    // Include selections if requested
    if (includeSelections) {
        selectionState.clients.forEach(clientId => {
            params.append('client_id', clientId);
        });
        selectionState.funds.forEach(fundName => {
            params.append('fund_name', fundName);
        });
        selectionState.accounts.forEach(accountId => {
            params.append('account_id', accountId);
        });
    }
    
    return params.toString() ? '?' + params.toString() : '';
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    applyMobileClass();
    // Initialize charts based on feature flag
    if (window.featureFlags?.useV2Charts) {
        chartManager.init();
    } else {
        initializeCharts();
    }
    initializeTableHandlers();
    initializeFilterInputs();
    initializeFilterToggle();
    updateDownloadButton();
    loadOverviewData();
    
    // Add document click listener for clearing selections
    document.addEventListener('click', function(e) {
        // Check if click is outside all tables and header
        if (isClickOutsideTables(e.target) && !e.target.closest('header') && !e.target.closest('.filter-section')) {
            // Clear all selections and go to overview
            if (hasAnySelections()) {
                clearAllSelections();
                // If we have a date filter active, reload date data, otherwise go to overview
                if (currentFilter.type === 'date' && currentFilter.value) {
                    loadDateData(currentFilter.value);
                } else {
                    loadOverviewData();
                }
            }
        }
    });
    
    // Re-detect mobile on resize
    window.addEventListener('resize', function() {
        applyMobileClass();
    });
});

// Update KPI cards with data based on current filter context
function updateKPICards(data) {
    // Data is already filtered server-side
    const filteredData = data;
    
    // Use kpi_metrics if available, fallback to existing calculation
    const totalAUM = filteredData.kpi_metrics ? filteredData.kpi_metrics.total_aum : 
                     calculateFallbackAUM(filteredData);
    
    // Calculate AUM change using kpi_metrics
    let aumChange = null;
    if (filteredData.kpi_metrics) {
        aumChange = filteredData.kpi_metrics.change_30d_pct;
    } else if (data.recent_history && data.recent_history.length >= 30) {
        const thirtyDaysAgo = data.recent_history[data.recent_history.length - 30].total_balance;
        aumChange = ((totalAUM - thirtyDaysAgo) / thirtyDaysAgo * 100);
    }
    
    // Update label and count based on filter context
    let countLabel = 'Active Clients';
    let countValue = 0;
    let countIcon = 'C';
    
    if (currentFilter.type === 'client' || currentFilter.type === 'client-fund' || 
        currentFilter.type === 'client-account' || currentFilter.type === 'client-fund-account' ||
        currentFilter.type === 'client-fund-multi-account') {
        // When viewing a specific client, show account count
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_accounts : 
                     (filteredData.account_details ? filteredData.account_details.length : 0);
    } else if (currentFilter.type === 'multi-client') {
        // When viewing multiple clients, show account count
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_accounts : 
                     (filteredData.account_details ? filteredData.account_details.length : 0);
    } else if (currentFilter.type === 'fund' || currentFilter.type === 'fund-account') {
        // When viewing a specific fund, show client count for that fund
        countLabel = 'Active Clients';
        countValue = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_clients : 
                     (filteredData.client_balances ? filteredData.client_balances.length : 0);
    } else if (currentFilter.type === 'multi-fund') {
        // When viewing multiple funds, show client count
        countLabel = 'Active Clients';
        countValue = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_clients : 
                     (filteredData.client_balances ? filteredData.client_balances.length : 0);
    } else if (currentFilter.type === 'account' || currentFilter.type === 'account-fund') {
        // When viewing a specific account, show 1 account
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = 1;
    } else if (currentFilter.type === 'multi-client-fund') {
        // When viewing multiple clients and funds, show account count
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_accounts : 
                     (filteredData.account_details ? filteredData.account_details.length : 0);
    } else if (currentFilter.type === 'multi-account') {
        // When viewing multiple accounts, show account count
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_accounts : 
                     (filteredData.account_details ? filteredData.account_details.length : 0);
    } else {
        // Overview mode - show total clients
        countValue = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_clients : 
                     (filteredData.client_balances ? filteredData.client_balances.length : 0);
    }
    
    // Count funds using kpi_metrics or fallback
    let totalFunds = 0;
    if (filteredData.kpi_metrics) {
        totalFunds = filteredData.kpi_metrics.active_funds;
    } else {
        // Fallback to existing logic
        if (currentFilter.type === 'client' || currentFilter.type === 'client-account') {
            totalFunds = filteredData.fund_balances ? filteredData.fund_balances.length : 0;
        } else if (currentFilter.type === 'multi-client') {
            totalFunds = filteredData.fund_balances ? filteredData.fund_balances.length : 0;
        } else if (currentFilter.type === 'client-fund' || currentFilter.type === 'client-fund-account' || 
                   currentFilter.type === 'client-fund-multi-account') {
            totalFunds = 1;
        } else if (currentFilter.type === 'fund' || currentFilter.type === 'fund-account') {
            totalFunds = 1;
        } else if (currentFilter.type === 'multi-fund') {
            totalFunds = filteredData.fund_balances ? filteredData.fund_balances.length : 0;
        } else if (currentFilter.type === 'account' || currentFilter.type === 'account-fund') {
            totalFunds = filteredData.fund_allocation ? filteredData.fund_allocation.length : 0;
        } else if (currentFilter.type === 'multi-client-fund') {
            totalFunds = filteredData.fund_balances ? filteredData.fund_balances.length : 0;
        } else if (currentFilter.type === 'multi-account') {
            totalFunds = filteredData.fund_balances ? filteredData.fund_balances.length : 0;
        } else {
            totalFunds = filteredData.fund_balances ? filteredData.fund_balances.length : 0;
        }
    }
    
    // Calculate average YTD growth based on visible data (keep existing logic)
    let avgYtdGrowth = 0;
    let dataForGrowth = [];
    
    // Determine which data to use for growth calculation
    if (currentFilter.type === 'overview' || currentFilter.type === 'date') {
        dataForGrowth = filteredData.client_balances || [];
    } else if (currentFilter.type === 'client' || currentFilter.type === 'client-account') {
        dataForGrowth = filteredData.fund_balances || [];
    } else if (currentFilter.type === 'multi-client') {
        dataForGrowth = filteredData.client_balances || [];
    } else if (currentFilter.type === 'client-fund' || currentFilter.type === 'client-fund-account' || 
               currentFilter.type === 'client-fund-multi-account') {
        if (filteredData.fund_balance) {
            dataForGrowth = [filteredData.fund_balance];
        } else {
            dataForGrowth = filteredData.fund_balances || [];
        }
    } else if (currentFilter.type === 'fund' || currentFilter.type === 'fund-account') {
        dataForGrowth = filteredData.client_balances || [];
    } else if (currentFilter.type === 'multi-fund') {
        dataForGrowth = filteredData.fund_balances || [];
    } else if (currentFilter.type === 'account' || currentFilter.type === 'account-fund') {
        dataForGrowth = filteredData.account_details || [];
    } else if (currentFilter.type === 'multi-client-fund') {
        dataForGrowth = filteredData.fund_balances || [];
    } else if (currentFilter.type === 'multi-account') {
        dataForGrowth = filteredData.account_details || [];
    }
    
    if (dataForGrowth.length > 0) {
        let totalWeight = 0;
        let totalWeightedYtd = 0;
        
        dataForGrowth.forEach(item => {
            const balance = item.total_balance || item.balance || 0;
            if (item.ytd_change !== null && item.ytd_change !== undefined && balance > 0) {
                totalWeightedYtd += item.ytd_change * balance;
                totalWeight += balance;
            }
        });
        
        if (totalWeight > 0) {
            avgYtdGrowth = totalWeightedYtd / totalWeight;
        }
    }
    
    // Update the KPI elements
    document.getElementById('totalAUM').textContent = formatCurrency(totalAUM);
    
    // Update client/account count
    const clientIcon = document.querySelector('.kpi-card:nth-child(2) .kpi-icon');
    const clientLabel = document.querySelector('.kpi-card:nth-child(2) .kpi-label');
    clientIcon.textContent = countIcon;
    clientLabel.textContent = countLabel;
    document.getElementById('totalClients').textContent = countValue;
    
    document.getElementById('totalFunds').textContent = totalFunds;
    document.getElementById('avgGrowth').textContent = (avgYtdGrowth !== undefined && avgYtdGrowth !== null && !isNaN(avgYtdGrowth)) ? avgYtdGrowth.toFixed(1) + '%' : '0.0%';
    
    // Update AUM change indicator
    const aumChangeEl = document.getElementById('aumChange');
    if (aumChange !== null) {
        const changeClass = aumChange > 0 ? 'positive' : aumChange < 0 ? 'negative' : 'neutral';
        const prefix = aumChange > 0 ? '+' : '';
        aumChangeEl.textContent = `${prefix}${(aumChange !== undefined && aumChange !== null && !isNaN(aumChange)) ? aumChange.toFixed(1) : '0.0'}% last 30 days`;
        aumChangeEl.className = `kpi-change ${changeClass}`;
    } else {
        aumChangeEl.textContent = '-';
        aumChangeEl.className = 'kpi-change neutral';
    }
    
    // Update growth trend
    const growthTrendEl = document.getElementById('growthTrend');
    const trendClass = avgYtdGrowth > 0 ? 'positive' : avgYtdGrowth < 0 ? 'negative' : 'neutral';
    const trendPrefix = avgYtdGrowth > 0 ? '↑' : avgYtdGrowth < 0 ? '↓' : '→';
    growthTrendEl.textContent = `${trendPrefix} Trending`;
    growthTrendEl.className = `kpi-change ${trendClass}`;
}

// Helper function for fallback AUM calculation
function calculateFallbackAUM(filteredData) {
    let totalAUM = 0;
    if (filteredData.client_balances && filteredData.client_balances.length > 0) {
        totalAUM = filteredData.client_balances.reduce((sum, client) => sum + (client.total_balance || 0), 0);
    } else if (filteredData.fund_balances && filteredData.fund_balances.length > 0) {
        totalAUM = filteredData.fund_balances.reduce((sum, fund) => sum + (fund.total_balance || 0), 0);
    } else if (filteredData.account_details && filteredData.account_details.length > 0) {
        totalAUM = filteredData.account_details.reduce((sum, account) => sum + (account.balance || account.total_balance || 0), 0);
    } else if (filteredData.recent_history && filteredData.recent_history.length > 0) {
        totalAUM = filteredData.recent_history[filteredData.recent_history.length - 1].total_balance;
    }
    return totalAUM;
}

// Handle chart clicks for drill-down
function handleChartClick(chartType, dataIndex, event) {
    // Stop event propagation to prevent clearing selections
    if (event && typeof event.stopPropagation === 'function') {
        event.stopPropagation();
    }
    
    // Get the clicked date
    const chart = chartType === 'recent' ? recentChart : longTermChart;
    const clickedDate = chart.data.labels[dataIndex];
    const clickedValue = chart.data.datasets[0].data[dataIndex];
    
    console.log(`Chart clicked: ${chartType}, Date: ${clickedDate}, Value: ${clickedValue}`);
    console.log(`Data index: ${dataIndex}`);
    
    // Check if allData exists
    if (!allData) {
        console.error('allData is not available');
        return;
    }
    
    // Get the actual date value from the chart data
    const chartData = chartType === 'recent' ? allData.recent_history : allData.long_term_history;
    
    if (!chartData || !chartData[dataIndex]) {
        console.error('Chart data not found for index:', dataIndex);
        return;
    }
    
    const actualDate = chartData[dataIndex].balance_date;
    console.log(`Loading data for date: ${actualDate}`);
    
    // Load data for the selected date
    loadDateData(actualDate);
}

// Initialize Chart.js charts
function initializeCharts() {
    const recentCtx = document.getElementById('recentChart').getContext('2d');
    const longTermCtx = document.getElementById('longTermChart').getContext('2d');
    
    // Mobile-specific chart options
    const mobileChartOptions = {
        scales: {
            x: {
                ticks: {
                    font: {
                        size: 8
                    },
                    maxTicksLimit: 6
                }
            },
            y: {
                ticks: {
                    font: {
                        size: 8
                    },
                    maxTicksLimit: 4
                }
            }
        }
    };

    recentChart = new Chart(recentCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Balance',
                data: [],
                borderColor: '#0085ff',
                backgroundColor: 'rgba(0, 133, 255, 0.1)',
                borderWidth: 2.5,
                pointRadius: 0,  // Hide points for cleaner display with daily data
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#0085ff',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 3,
                tension: 0.2  // Smoother curve for professional look
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                tooltip: {
                    filter: function(tooltipItem) {
                        // Only show tooltip for the main dataset (index 0)
                        return tooltipItem.datasetIndex === 0;
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#f1f5f9',
                        lineWidth: 1,
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            size: isMobile ? 8 : 9,
                            weight: '500'
                        },
                        color: '#64748b',
                        padding: 4,
                        maxTicksLimit: isMobile ? 6 : 10
                    }
                },
                y: {
                    grid: {
                        color: '#f1f5f9',
                        lineWidth: 1,
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyInMillions(value);
                        },
                        font: {
                            size: isMobile ? 8 : 9,
                            weight: '500'
                        },
                        color: '#64748b',
                        padding: 4,
                        maxTicksLimit: isMobile ? 4 : 6
                    }
                }
            },
            onClick: (event, elements, chart) => {
                // Chart click handler for drill-down
                console.log('Recent chart clicked', elements);
                // Filter to only handle clicks on the main dataset (index 0)
                const mainDatasetElements = elements.filter(el => el.datasetIndex === 0);
                if (mainDatasetElements.length > 0) {
                    // Clicked on a data point from main dataset
                    handleChartClick('recent', mainDatasetElements[0].index, event.native);
                } else {
                    // Clicked on empty area - find nearest point
                    const canvasPosition = Chart.helpers.getRelativePosition(event, chart);
                    const dataX = chart.scales.x.getValueForPixel(canvasPosition.x);
                    const dataIndex = chart.scales.x.getValueForPixel(canvasPosition.x);
                    
                    // Find the closest data point
                    if (dataIndex >= 0 && dataIndex < chart.data.labels.length) {
                        const nearestIndex = Math.round(dataIndex);
                        console.log('Nearest index:', nearestIndex);
                        handleChartClick('recent', nearestIndex, event.native);
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });

    longTermChart = new Chart(longTermCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Balance',
                data: [],
                borderColor: '#00d647',
                backgroundColor: 'rgba(0, 214, 71, 0.1)',
                borderWidth: 2.5,
                pointRadius: 0,  // Hide points for cleaner display with daily data
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#00d647',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 3,
                tension: 0.2  // Smoother curve for professional look
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                tooltip: {
                    filter: function(tooltipItem) {
                        // Only show tooltip for the main dataset (index 0)
                        return tooltipItem.datasetIndex === 0;
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#f1f5f9',
                        lineWidth: 1,
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            size: isMobile ? 8 : 9,
                            weight: '500'
                        },
                        color: '#64748b',
                        maxTicksLimit: isMobile ? 6 : 12,  // Show ~12 labels for 3 years (quarterly)
                        autoSkip: true,
                        maxRotation: 0,
                        minRotation: 0,
                        padding: 4
                    }
                },
                y: {
                    grid: {
                        color: '#f1f5f9',
                        lineWidth: 1,
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrencyInMillions(value);
                        },
                        font: {
                            size: isMobile ? 8 : 9,
                            weight: '500'
                        },
                        color: '#64748b',
                        padding: 4,
                        maxTicksLimit: isMobile ? 4 : 6
                    }
                }
            },
            onClick: (event, elements, chart) => {
                // Chart click handler for drill-down
                console.log('Long-term chart clicked', elements);
                // Filter to only handle clicks on the main dataset (index 0)
                const mainDatasetElements = elements.filter(el => el.datasetIndex === 0);
                if (mainDatasetElements.length > 0) {
                    // Clicked on a data point from main dataset
                    handleChartClick('longTerm', mainDatasetElements[0].index, event.native);
                } else {
                    // Clicked on empty area - find nearest point
                    const canvasPosition = Chart.helpers.getRelativePosition(event, chart);
                    const dataX = chart.scales.x.getValueForPixel(canvasPosition.x);
                    const dataIndex = chart.scales.x.getValueForPixel(canvasPosition.x);
                    
                    // Find the closest data point
                    if (dataIndex >= 0 && dataIndex < chart.data.labels.length) {
                        const nearestIndex = Math.round(dataIndex);
                        console.log('Nearest index:', nearestIndex);
                        handleChartClick('longTerm', nearestIndex, event.native);
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Load overview data
async function loadOverviewData() {
    try {
        let data;
        
        // Check if v2 API should be used
        if (window.featureFlags?.useV2DashboardApi) {
            // Use v2 API for consistency with multi-selection
            const queryString = buildQueryString();
            const response = await fetch(`/api/v2/dashboard${queryString}`);
            data = await response.json();
            
            if (!response.ok) {
                console.error('Error loading overview data from v2:', data.error);
                // Fallback to v1
                const v1Response = await fetch('/api/overview' + buildQueryString());
                data = await v1Response.json();
            }
        } else {
            // Use v1 API
            const response = await fetch('/api/overview' + buildQueryString());
            data = await response.json();
        }
        
        allData = data;
        
        currentFilter = { type: 'overview', value: null };
        updateFilterIndicator('All Clients - All Funds');
        updateKPICards(data);
        
        // Handle chart updates based on API version
        if (data.charts) {
            // v2 API format - extract chart data
            chartManager.update({
                recent_history: data.charts.recent_history,
                long_term_history: data.charts.long_term_history
            });
        } else {
            // v1 API format
            chartManager.update(data);
        }
        
        // Update all tables with v2 (eliminates double API call)
        await tablesV2.updateTables(data);
        
        // Update CSV row count
        updateDownloadButton();
    } catch (error) {
        console.error('Error loading overview data:', error);
    }
}

// Load data for a specific date
async function loadDateData(dateString) {
    try {
        const hasClientSelection = selectionState.clients.size > 0;
        const hasFundSelection = selectionState.funds.size > 0;
        const hasAccountSelection = selectionState.accounts.size > 0;
        
        // Get date data with text filters and selections
        const response = await fetch(`/api/date/${dateString}` + buildQueryString(true));
        const data = await response.json();
        
        // Store the full date data before filtering
        const fullDateData = data;
        
        // If we have selections, filter the date data on the frontend for tables only
        // Chart data is now properly filtered on the backend
        if (hasClientSelection || hasFundSelection || hasAccountSelection) {
            // Filter client balances
            if (hasClientSelection) {
                data.client_balances = data.client_balances.filter(client => 
                    selectionState.clients.has(client.client_id)
                );
            }
            
            // Filter fund balances
            if (hasFundSelection) {
                data.fund_balances = data.fund_balances.filter(fund => 
                    selectionState.funds.has(fund.fund_name)
                );
            }
            
            // Filter account details
            if (hasAccountSelection) {
                data.account_details = data.account_details.filter(account => 
                    selectionState.accounts.has(account.account_id)
                );
            } else if (hasClientSelection || hasFundSelection) {
                // Filter accounts based on client/fund selections
                data.account_details = data.account_details.filter(account => {
                    let matchClient = !hasClientSelection;
                    let matchFund = !hasFundSelection;
                    
                    if (hasClientSelection && account.client_name) {
                        // Find client ID for this account
                        const client = fullDateData.client_balances.find(c => 
                            c.client_name === account.client_name
                        );
                        if (client) {
                            matchClient = selectionState.clients.has(client.client_id);
                        }
                    }
                    
                    if (hasFundSelection && account.fund_name) {
                        matchFund = selectionState.funds.has(account.fund_name);
                    }
                    
                    return matchClient && matchFund;
                });
            }
        }
        
        // Build filter description
        let filterParts = [`Date: ${formatDateLong(dateString)}`];
        if (hasClientSelection) {
            filterParts.push(`${selectionState.clients.size} Client${selectionState.clients.size > 1 ? 's' : ''}`);
        }
        if (hasFundSelection) {
            filterParts.push(`${selectionState.funds.size} Fund${selectionState.funds.size > 1 ? 's' : ''}`);
        }
        if (hasAccountSelection) {
            filterParts.push(`${selectionState.accounts.size} Account${selectionState.accounts.size > 1 ? 's' : ''}`);
        }
        
        currentFilter = { type: 'date', value: dateString, hasSelections: hasClientSelection || hasFundSelection || hasAccountSelection };
        updateFilterIndicator(filterParts.join(' | '));
        updateKPICards(data);
        
        // Update charts and tables with filtered data
        chartManager.update(data);
        
        // For tables, show full data if no selections, filtered data if selections exist
        if (hasClientSelection || hasFundSelection || hasAccountSelection) {
            await tablesV2.updateTables(data);
        } else {
            // Show all data for the date
            await tablesV2.updateTables(fullDateData);
        }
        
        // Update CSV row count
        updateDownloadButton();
    } catch (error) {
        console.error('Error loading date data:', error);
    }
}

// Load client-specific data
async function loadClientData(clientId, clientName) {
    try {
        let data;
        
        // Check if v2 API should be used
        if (window.featureFlags?.useV2DashboardApi) {
            // Use v2 API with client filter
            const queryString = buildQueryString();
            const clientParam = queryString ? `${queryString}&client_id=${clientId}` : `?client_id=${clientId}`;
            const response = await fetch(`/api/v2/dashboard${clientParam}`);
            data = await response.json();
            
            if (!response.ok) {
                console.error('Error loading client data from v2:', data.error);
                // Fallback to v1
                const v1Response = await fetch(`/api/client/${clientId}` + buildQueryString());
                data = await v1Response.json();
            }
        } else {
            // Use v1 API
            const response = await fetch(`/api/client/${clientId}` + buildQueryString());
            data = await response.json();
        }
        
        currentFilter = { type: 'client', value: clientId, name: clientName };
        
        // Handle chart updates based on API version
        if (data.charts) {
            // v2 API format - extract chart data
            chartManager.update({
                recent_history: data.charts.recent_history,
                long_term_history: data.charts.long_term_history
            });
        } else {
            // v1 API format
            chartManager.update(data);
        }
        
        // For Tableau-like behavior, we need to show ALL clients but with filtered funds/accounts
        // When using v2 API, we need to fetch all clients separately
        let allClientsData = null;
        if (window.featureFlags?.useV2DashboardApi) {
            // Fetch all clients to show in the table
            const allClientsResponse = await fetch(`/api/v2/dashboard?selection_source=client`);
            if (allClientsResponse.ok) {
                allClientsData = await allClientsResponse.json();
            }
        }
        
        // Update tables with proper data
        const tableData = {
            // Use all clients if available, otherwise fall back to filtered data
            client_balances: allClientsData?.client_balances || data.client_balances || allData?.client_balances || [],
            fund_balances: data.fund_balances || data.funds || [],
            account_details: data.account_details || data.accounts || []
        };
        
        // Add client name to accounts if missing
        if (tableData.account_details && tableData.account_details.length > 0) {
            tableData.account_details = tableData.account_details.map(acc => ({ ...acc, client_name: acc.client_name || clientName }));
        }
        
        await tablesV2.updateTables(tableData);
        
        // Update KPIs with client data
        updateKPICards(data);
        
        // Restore visual selections
        restoreSelectionVisuals();
        
    } catch (error) {
        console.error('Error loading client data:', error);
    }
}

// Load fund-specific data
async function loadFundData(fundName) {
    try {
        const response = await fetch(`/api/fund/${encodeURIComponent(fundName)}` + buildQueryString());
        const data = await response.json();
        
        currentFilter = { type: 'fund', value: fundName };
        chartManager.update(data);
        
        // Update tables with fund-specific data
        const tableData = {
            client_balances: data.client_balances,
            fund_balances: allData?.fund_balances || data.fund_balances,
            account_details: data.account_details.map(acc => ({ ...acc, fund_name: fundName }))
        };
        await tablesV2.updateTables(tableData);
        
        // Update KPIs with fund data
        updateKPICards(data);
        
        // Update CSV row count
        updateDownloadButton();
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading fund data:', error);
    }
}

// Load account-specific data
async function loadAccountData(accountId) {
    try {
        const response = await fetch(`/api/account/${encodeURIComponent(accountId)}` + buildQueryString());
        const data = await response.json();
        
        currentFilter = { type: 'account', value: accountId };
        
        // Update charts with account history
        chartManager.update(data);
        
        // For account view, show related data
        // Find the client for this account
        let clientName = '';
        let clientId = '';
        if (allData && allData.account_details) {
            const account = allData.account_details.find(acc => acc.account_id === accountId);
            if (account) {
                clientName = account.client_name;
                // Find client ID
                const client = allData.client_balances.find(c => c.client_name === clientName);
                if (client) clientId = client.client_id;
            }
        }
        
        // Show the client that owns this account with account-specific total
        let clientData = [];
        if (clientId) {
            const client = allData.client_balances.find(c => c.client_id === clientId);
            if (client) {
                // Calculate total balance for this account across all funds
                const accountTotal = data.fund_allocation.reduce((sum, fund) => sum + fund.balance, 0);
                clientData = [{
                    ...client,
                    total_balance: accountTotal
                }];
            }
        }
        
        // Prepare table data
        const fundData = data.fund_allocation.map(f => ({ 
            ...f, 
            total_balance: f.balance, 
            account_count: 1,
            qtd_change: null,
            ytd_change: null
        }));
        
        // Determine which accounts to show based on current selection context
        let accountData = [];
        if (selectionState.clients.size > 0 && selectionState.funds.size > 0) {
            // If client and fund are selected, show only accounts for that combination
            const selectedClientId = Array.from(selectionState.clients)[0];
            const selectedFundName = Array.from(selectionState.funds)[0];
            
            // Fetch the filtered account list
            const filteredResponse = await fetch(`/api/client/${selectedClientId}/fund/${encodeURIComponent(selectedFundName)}` + buildQueryString());
            const filteredData = await filteredResponse.json();
            accountData = filteredData.account_details;
        } else if (selectionState.clients.size > 0) {
            // If only client is selected, show accounts for that client
            const selectedClientId = Array.from(selectionState.clients)[0];
            const clientResponse = await fetch(`/api/client/${selectedClientId}` + buildQueryString());
            const clientData = await clientResponse.json();
            accountData = clientData.account_details;
        } else if (selectionState.funds.size > 0) {
            // If only fund is selected, show accounts for that fund
            const selectedFundName = Array.from(selectionState.funds)[0];
            const fundResponse = await fetch(`/api/fund/${encodeURIComponent(selectedFundName)}` + buildQueryString());
            const fundResponseData = await fundResponse.json();
            accountData = fundResponseData.account_details;
        } else {
            // No other selections, show all accounts
            accountData = allData?.account_details || [];
        }
        
        // Update all tables with the prepared data
        const tableData = {
            client_balances: clientData,
            fund_balances: fundData,
            account_details: accountData
        };
        await tablesV2.updateTables(tableData);
        
        // Update KPIs with account data
        updateKPICards(data);
        
        // Update CSV row count
        updateDownloadButton();
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading account data:', error);
    }
}

// Load account data filtered by fund
async function loadAccountDataForFund(accountId, fundName) {
    try {
        const response = await fetch(`/api/account/${encodeURIComponent(accountId)}/fund/${encodeURIComponent(fundName)}` + buildQueryString());
        const data = await response.json();
        
        currentFilter = { type: 'account-fund', accountId, fundName };
        
        // Update charts with account history for this specific fund
        chartManager.update(data);
        
        // For account view, show related data
        // Find the client for this account
        let clientName = '';
        let clientId = '';
        if (allData && allData.account_details) {
            const account = allData.account_details.find(acc => acc.account_id === accountId);
            if (account) {
                clientName = account.client_name;
                // Find client ID
                const client = allData.client_balances.find(c => c.client_name === clientName);
                if (client) clientId = client.client_id;
            }
        }
        
        // Show the client that owns this account with filtered balance
        let clientData = [];
        if (clientId) {
            const client = allData.client_balances.find(c => c.client_id === clientId);
            if (client) {
                // Show client with only the account-fund specific balance
                clientData = [{
                    ...client,
                    total_balance: data.fund_allocation[0]?.balance || 0
                }];
            }
        }
        
        // Show only the selected fund for this account
        const fundData = [{ 
            fund_name: fundName,
            total_balance: data.fund_allocation[0]?.balance || 0,
            account_count: 1,
            qtd_change: null,
            ytd_change: null
        }];
        
        // Determine which accounts to show based on current selection context
        let accountData = [];
        if (selectionState.clients.size > 0 && selectionState.funds.size > 0) {
            // If client and fund are selected, show only accounts for that combination
            const selectedClientId = Array.from(selectionState.clients)[0];
            const selectedFundName = Array.from(selectionState.funds)[0];
            
            // Fetch the filtered account list
            const filteredResponse = await fetch(`/api/client/${selectedClientId}/fund/${encodeURIComponent(selectedFundName)}` + buildQueryString());
            const filteredData = await filteredResponse.json();
            accountData = filteredData.account_details;
        } else if (selectionState.funds.size > 0) {
            // If only fund is selected, show accounts for that fund
            const selectedFundName = Array.from(selectionState.funds)[0];
            const fundResponse = await fetch(`/api/fund/${encodeURIComponent(selectedFundName)}` + buildQueryString());
            const fundResponseData = await fundResponse.json();
            accountData = fundResponseData.account_details;
        } else {
            // No other selections, show all accounts
            accountData = allData?.account_details || [];
        }
        
        // Update all tables with the prepared data
        const tableData = {
            client_balances: clientData,
            fund_balances: fundData,
            account_details: accountData
        };
        await tablesV2.updateTables(tableData);
        
        // Update KPIs with account data
        updateKPICards(data);
        
        // Restore visual selections
        restoreSelectionVisuals();
        
        // Update CSV row count
        updateDownloadButton();
    } catch (error) {
        console.error('Error loading account data for fund:', error);
    }
}

// Update filter indicator
function updateFilterIndicator(text) {
    // Add text filter info if any are active
    let filterText = text;
    const activeTextFilters = [];
    
    if (textFilters.fundTicker) {
        activeTextFilters.push(`Ticker: ${textFilters.fundTicker}`);
    }
    if (textFilters.clientName) {
        activeTextFilters.push(`Client: ${textFilters.clientName}`);
    }
    if (textFilters.accountNumber) {
        activeTextFilters.push(`Account: ${textFilters.accountNumber}`);
    }
    
    if (activeTextFilters.length > 0) {
        filterText += ` | ${activeTextFilters.join(', ')}`;
    }
    
    // Check if we need to add a clear date button
    const filterElement = document.getElementById('current-filter');
    if (currentFilter.type === 'date' && filterText.includes('Date:')) {
        // Replace the date part with HTML that includes a clear button
        filterText = filterText.replace(/Date: ([^|]+)/, 
            'Date: $1 <button class="clear-date-btn" onclick="clearDateFilter()">×</button>');
        filterElement.innerHTML = `Viewing: ${filterText}`;
    } else {
        filterElement.textContent = `Viewing: ${filterText}`;
    }
    
    // Show/hide clear filters button
    const clearButton = document.getElementById('clear-filters');
    const hasActiveFilters = hasAnySelections() ||
                           (currentFilter.type !== 'overview' && currentFilter.type !== null) ||
                           textFilters.fundTicker || textFilters.clientName || textFilters.accountNumber;
    
    clearButton.style.display = hasActiveFilters ? 'block' : 'none';
}

// Update recent chart (90 days)
function updateRecentChart(data) {
    if (!data || data.length === 0) return;
    
    // Calculate average, max, and min values
    const balances = data.map(item => item.total_balance);
    const avgBalance = balances.reduce((sum, val) => sum + val, 0) / balances.length;
    const maxBalance = Math.max(...balances);
    const minBalance = Math.min(...balances);
    
    // Update the stats in the header
    const statsElement = document.getElementById('recentChartStats');
    if (statsElement) {
        statsElement.innerHTML = `
            <span class="stat-item"><span class="stat-label">Max:</span> <span class="stat-value max">${formatCurrency(maxBalance)}</span></span>
            <span class="stat-item"><span class="stat-label">Avg:</span> <span class="stat-value avg">${formatCurrency(avgBalance)}</span></span>
            <span class="stat-item"><span class="stat-label">Min:</span> <span class="stat-value min">${formatCurrency(minBalance)}</span></span>
        `;
    }
    
    // Update labels
    recentChart.data.labels = data.map(item => formatDate(item.balance_date));
    
    // Clear existing datasets and rebuild
    recentChart.data.datasets = [
        {
            label: 'Total Balance',
            data: balances,
            borderColor: '#0085ff',
            backgroundColor: 'rgba(0, 133, 255, 0.1)',
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#0085ff',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 3,
            tension: 0.2,
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
    
    // Keep legend hidden since we show stats in the header
    recentChart.options.plugins.legend = {
        display: false
    };
    
    recentChart.update();
}

// Update long-term chart (3 years)
function updateLongTermChart(data) {
    if (!data || data.length === 0) return;
    
    // Calculate average, max, and min values
    const balances = data.map(item => item.total_balance);
    const avgBalance = balances.reduce((sum, val) => sum + val, 0) / balances.length;
    const maxBalance = Math.max(...balances);
    const minBalance = Math.min(...balances);
    
    // Update the stats in the header
    const statsElement = document.getElementById('longTermChartStats');
    if (statsElement) {
        statsElement.innerHTML = `
            <span class="stat-item"><span class="stat-label">Max:</span> <span class="stat-value max">${formatCurrency(maxBalance)}</span></span>
            <span class="stat-item"><span class="stat-label">Avg:</span> <span class="stat-value avg">${formatCurrency(avgBalance)}</span></span>
            <span class="stat-item"><span class="stat-label">Min:</span> <span class="stat-value min">${formatCurrency(minBalance)}</span></span>
        `;
    }
    
    // Update labels
    longTermChart.data.labels = data.map(item => formatDateLong(item.balance_date));
    
    // Clear existing datasets and rebuild
    longTermChart.data.datasets = [
        {
            label: 'Total Balance',
            data: balances,
            borderColor: '#00d647',
            backgroundColor: 'rgba(0, 214, 71, 0.1)',
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: '#00d647',
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 3,
            tension: 0.2,
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
    
    // Keep legend hidden since we show stats in the header
    longTermChart.options.plugins.legend = {
        display: false
    };
    
    longTermChart.update();
}

// Sample data points for long-term view
function sampleDataPoints(data, maxPoints) {
    if (data.length <= maxPoints) return data;
    
    const step = Math.ceil(data.length / maxPoints);
    const sampled = [];
    
    for (let i = 0; i < data.length; i += step) {
        sampled.push(data[i]);
    }
    
    // Always include the last data point
    if (sampled[sampled.length - 1] !== data[data.length - 1]) {
        sampled.push(data[data.length - 1]);
    }
    
    return sampled;
}

// Filter data based on text filters

// Update client table
function updateClientTable(data) {
    const tbody = document.querySelector('#clientTable tbody');
    tbody.innerHTML = '';
    
    if (!data || !Array.isArray(data)) {
        console.error('Invalid data for client table:', data);
        return;
    }
    
    // Data is already filtered server-side
    console.log('Updating client table with', data.length, 'items');
    data.forEach(client => {
        const row = tbody.insertRow();
        row.dataset.clientId = client.client_id;
        row.dataset.clientName = client.client_name;
        // Check if this client is selected
        if (selectionState.clients.has(client.client_id)) {
            row.classList.add('selected');
        }
        row.innerHTML = `
            <td>${client.client_name}</td>
            <td class="number">${formatCurrency(client.total_balance)}</td>
            <td class="number">${formatPercentage(client.qtd_change)}</td>
            <td class="number">${formatPercentage(client.ytd_change)}</td>
        `;
    });
}

// Update fund table
function updateFundTable(data) {
    const tbody = document.querySelector('#fundTable tbody');
    tbody.innerHTML = '';
    
    if (!data || !Array.isArray(data)) {
        console.error('Invalid data for fund table:', data);
        return;
    }
    
    // Data is already filtered server-side
    data.forEach(fund => {
        const row = tbody.insertRow();
        row.dataset.fundName = fund.fund_name;
        row.dataset.fundTicker = fund.fund_ticker;
        // Check if this fund is selected
        if (selectionState.funds.has(fund.fund_name)) {
            row.classList.add('selected');
        }
        row.innerHTML = `
            <td>${fund.fund_name}</td>
            <td class="number">${formatCurrency(fund.total_balance)}</td>
            <td class="number">${formatPercentage(fund.qtd_change)}</td>
            <td class="number">${formatPercentage(fund.ytd_change)}</td>
        `;
    });
}

// Update account table
function updateAccountTable(data) {
    const tbody = document.querySelector('#accountTable tbody');
    tbody.innerHTML = '';
    
    if (!data || !Array.isArray(data)) {
        console.error('Invalid data for account table:', data);
        return;
    }
    
    // Data is already filtered server-side
    data.forEach(account => {
        const row = tbody.insertRow();
        row.dataset.accountId = account.account_id;
        // Store client and fund info in data attributes for filtering
        if (account.client_name) row.dataset.clientName = account.client_name;
        if (account.fund_name) row.dataset.fundName = account.fund_name;
        // Check if this account is selected
        if (selectionState.accounts.has(account.account_id)) {
            row.classList.add('selected');
        }
        row.innerHTML = `
            <td>${account.account_id}</td>
            <td class="number">${formatCurrency(account.balance || account.total_balance || 0)}</td>
            <td class="number">${formatPercentage(account.qtd_change)}</td>
            <td class="number">${formatPercentage(account.ytd_change)}</td>
        `;
    });
}

// Initialize table click handlers once on page load
// Initialize filter input handlers
function initializeFilterInputs() {
    const fundTickerInput = document.getElementById('fundTickerFilter');
    const clientNameInput = document.getElementById('clientNameFilter');
    const accountNumberInput = document.getElementById('accountNumberFilter');
    const applyButton = document.getElementById('applyFilters');
    
    // Apply filters on button click
    applyButton.addEventListener('click', applyTextFilters);
    
    // Apply filters on Enter key
    [fundTickerInput, clientNameInput, accountNumberInput].forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyTextFilters();
            }
        });
    });
    
    // Update clear filters button to also clear text filters
    const clearButton = document.getElementById('clear-filters');
    clearButton.addEventListener('click', function() {
        // Clear text filters
        fundTickerInput.value = '';
        clientNameInput.value = '';
        accountNumberInput.value = '';
        textFilters = {
            fundTicker: '',
            clientName: '',
            accountNumber: ''
        };
        
        // Update active filter count
        updateActiveFilterCount();
        
        // Clear selections
        clearAllSelections();
        loadOverviewData();
    });
}

// Apply text filters
function applyTextFilters() {
    // Get filter values
    textFilters.fundTicker = document.getElementById('fundTickerFilter').value.trim();
    textFilters.clientName = document.getElementById('clientNameFilter').value.trim();
    textFilters.accountNumber = document.getElementById('accountNumberFilter').value.trim();
    
    // Update active filter count
    updateActiveFilterCount();
    
    // Reload data with filters
    updateDataBasedOnSelections();
}

// Initialize filter toggle functionality
function initializeFilterToggle() {
    const toggleBtn = document.getElementById('toggle-filters');
    const filterSection = document.getElementById('filterSection');
    const activeFilterCount = toggleBtn.querySelector('.active-filter-count');
    
    // Check localStorage for saved state
    const savedState = localStorage.getItem('filterSectionCollapsed');
    if (savedState === 'true') {
        filterSection.classList.add('collapsed');
        toggleBtn.classList.remove('active');
    } else {
        toggleBtn.classList.add('active');
    }
    
    // Toggle button click handler
    toggleBtn.addEventListener('click', function() {
        const isCollapsed = filterSection.classList.contains('collapsed');
        
        if (isCollapsed) {
            filterSection.classList.remove('collapsed');
            toggleBtn.classList.add('active');
            localStorage.setItem('filterSectionCollapsed', 'false');
        } else {
            filterSection.classList.add('collapsed');
            toggleBtn.classList.remove('active');
            localStorage.setItem('filterSectionCollapsed', 'true');
        }
    });
    
    // Update active filter count
    updateActiveFilterCount();
    
    // Keyboard shortcut (Ctrl+F)
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            toggleBtn.click();
            
            // Focus first input if expanding
            if (!filterSection.classList.contains('collapsed')) {
                setTimeout(() => {
                    document.getElementById('fundTickerFilter').focus();
                }, 300);
            }
        }
    });
}

// Update active filter count badge
function updateActiveFilterCount() {
    const toggleBtn = document.getElementById('toggle-filters');
    const activeFilterCount = toggleBtn.querySelector('.active-filter-count');
    
    let count = 0;
    if (textFilters.fundTicker) count++;
    if (textFilters.clientName) count++;
    if (textFilters.accountNumber) count++;
    
    if (count > 0) {
        activeFilterCount.textContent = count;
        activeFilterCount.style.display = 'inline-block';
    } else {
        activeFilterCount.style.display = 'none';
    }
}

function initializeTableHandlers() {
    // Client table clicks
    document.querySelector('#clientTable').addEventListener('click', function(e) {
        const row = e.target.closest('tbody tr');
        if (row) {
            const clientId = row.dataset.clientId;
            const clientName = row.dataset.clientName;
            if (clientId) {
                handleClientClick(clientId, clientName, row);
            }
        }
    });
    
    // Fund table clicks
    document.querySelector('#fundTable').addEventListener('click', function(e) {
        const row = e.target.closest('tbody tr');
        if (row) {
            const fundName = row.dataset.fundName;
            if (fundName) {
                handleFundClick(fundName, row);
            }
        }
    });
    
    // Account table clicks
    document.querySelector('#accountTable').addEventListener('click', function(e) {
        const row = e.target.closest('tbody tr');
        if (row) {
            const accountId = row.dataset.accountId;
            if (accountId) {
                handleAccountClick(accountId, row);
            }
        }
    });
    
    // Header click to reset
    document.querySelector('header h1').addEventListener('click', function() {
        clearAllSelections();
        loadOverviewData();
    });
    
    // Clear filters button click
    document.getElementById('clear-filters').addEventListener('click', function() {
        clearAllSelections();
        currentFilter = { type: 'overview', value: null };
        loadOverviewData();
    });
}

// Handle client row click
function handleClientClick(clientId, clientName, row) {
    const isSelected = selectionState.clients.has(clientId);
    
    if (isSelected) {
        // Deselect
        selectionState.clients.delete(clientId);
        row.classList.remove('selected');
    } else {
        // Select
        selectionState.clients.add(clientId);
        row.classList.add('selected');
    }
    
    // Store current scroll positions before update
    const clientTableScroll = document.querySelector('#clientTable').parentElement.scrollTop;
    const fundTableScroll = document.querySelector('#fundTable').parentElement.scrollTop;
    const accountTableScroll = document.querySelector('#accountTable').parentElement.scrollTop;
    
    // Update data based on current selections
    updateDataBasedOnSelections();
    
    // Restore scroll positions after update
    setTimeout(() => {
        document.querySelector('#clientTable').parentElement.scrollTop = clientTableScroll;
        document.querySelector('#fundTable').parentElement.scrollTop = fundTableScroll;
        document.querySelector('#accountTable').parentElement.scrollTop = accountTableScroll;
    }, 0);
}

// Handle fund row click
function handleFundClick(fundName, row) {
    const isSelected = selectionState.funds.has(fundName);
    
    if (isSelected) {
        // Deselect
        selectionState.funds.delete(fundName);
        row.classList.remove('selected');
    } else {
        // Select
        selectionState.funds.add(fundName);
        row.classList.add('selected');
    }
    
    // Store current scroll positions before update
    const clientTableScroll = document.querySelector('#clientTable').parentElement.scrollTop;
    const fundTableScroll = document.querySelector('#fundTable').parentElement.scrollTop;
    const accountTableScroll = document.querySelector('#accountTable').parentElement.scrollTop;
    
    // Update data based on current selections
    updateDataBasedOnSelections();
    
    // Restore scroll positions after update
    setTimeout(() => {
        document.querySelector('#clientTable').parentElement.scrollTop = clientTableScroll;
        document.querySelector('#fundTable').parentElement.scrollTop = fundTableScroll;
        document.querySelector('#accountTable').parentElement.scrollTop = accountTableScroll;
    }, 0);
}

// Handle account row click
function handleAccountClick(accountId, row) {
    const isSelected = selectionState.accounts.has(accountId);
    
    if (isSelected) {
        // Deselect
        selectionState.accounts.delete(accountId);
        row.classList.remove('selected');
    } else {
        // Select
        selectionState.accounts.add(accountId);
        row.classList.add('selected');
    }
    
    // Update data based on current selections
    updateDataBasedOnSelections();
}

// Update data based on current selections
async function updateDataBasedOnSelections() {
    // Determine what data to load based on selections
    const hasClientSelection = selectionState.clients.size > 0;
    const hasFundSelection = selectionState.funds.size > 0;
    const hasAccountSelection = selectionState.accounts.size > 0;
    
    // Build filter description
    let filterParts = [];
    if (hasClientSelection) {
        filterParts.push(`${selectionState.clients.size} Client${selectionState.clients.size > 1 ? 's' : ''}`);
    }
    if (hasFundSelection) {
        filterParts.push(`${selectionState.funds.size} Fund${selectionState.funds.size > 1 ? 's' : ''}`);
    }
    if (hasAccountSelection) {
        filterParts.push(`${selectionState.accounts.size} Account${selectionState.accounts.size > 1 ? 's' : ''}`);
    }
    
    const filterText = filterParts.length > 0 ? filterParts.join(', ') : 'All Clients - All Funds';
    updateFilterIndicator(filterText);
    
    // Load appropriate data
    if (!hasClientSelection && !hasFundSelection && !hasAccountSelection) {
        // No selections - show overview
        await loadOverviewData();
    } else if (hasClientSelection && !hasFundSelection && !hasAccountSelection) {
        // Only client(s) selected
        if (selectionState.clients.size === 1) {
            const clientId = Array.from(selectionState.clients)[0];
            const clientName = document.querySelector(`#clientTable tr[data-client-id="${clientId}"] td:first-child`)?.textContent || '';
            await loadClientData(clientId, clientName);
        } else {
            // Multiple clients - load filtered overview
            await loadFilteredData();
        }
    } else if (!hasClientSelection && hasFundSelection && !hasAccountSelection) {
        // Only fund(s) selected
        if (selectionState.funds.size === 1) {
            const fundName = Array.from(selectionState.funds)[0];
            await loadFundData(fundName);
        } else {
            // Multiple funds - load filtered overview
            await loadFilteredData();
        }
    } else if (!hasClientSelection && !hasFundSelection && hasAccountSelection) {
        // Only account(s) selected
        if (selectionState.accounts.size === 1) {
            const accountId = Array.from(selectionState.accounts)[0];
            await loadAccountData(accountId);
        } else {
            // Multiple accounts - load filtered overview
            await loadFilteredData();
        }
    } else if (hasClientSelection && hasFundSelection && !hasAccountSelection) {
        // Client and fund selected (no account)
        if (selectionState.clients.size === 1 && selectionState.funds.size === 1) {
            const clientId = Array.from(selectionState.clients)[0];
            const fundName = Array.from(selectionState.funds)[0];
            const clientName = document.querySelector(`#clientTable tr[data-client-id="${clientId}"] td:first-child`)?.textContent || '';
            await loadClientFundData(clientId, clientName, fundName);
        } else {
            // Multiple selections - load filtered overview
            await loadFilteredData();
        }
    } else if (hasAccountSelection && (hasClientSelection || hasFundSelection)) {
        // Account selected with other selections - prioritize account view
        if (selectionState.accounts.size === 1) {
            const accountId = Array.from(selectionState.accounts)[0];
            // If a specific fund is selected, load account data filtered by that fund
            if (selectionState.funds.size === 1) {
                const fundName = Array.from(selectionState.funds)[0];
                await loadAccountDataForFund(accountId, fundName);
            } else {
                await loadAccountData(accountId);
            }
        } else {
            // Multiple accounts or complex selection - load filtered overview
            await loadFilteredData();
        }
    } else {
        // Other combinations - load filtered data
        await loadFilteredData();
    }
    
    // Restore visual selections after data load
    restoreSelectionVisuals();
}

// Helper function to append selection_source parameter correctly
function appendSelectionSource(queryString, source) {
    const separator = queryString ? '&' : '?';
    return `${queryString}${separator}selection_source=${source}`;
}

// Load filtered data based on multiple selections
async function loadFilteredData() {
    try {
        const hasClients = selectionState.clients.size > 0;
        const hasFunds = selectionState.funds.size > 0;
        const hasAccounts = selectionState.accounts.size > 0;
        
        // Get filtered intersection data for charts, KPIs, and non-selected tables
        const queryString = buildQueryString(true);
        const response = await fetch(`/api/v2/dashboard${queryString}`);
        const data = await response.json();
        
        if (!response.ok) {
            console.error('Error loading filtered data:', data.error);
            return;
        }
        
        // Prepare promises for parallel fetching of "all items" data
        const promises = [];
        const sources = [];
        
        if (hasClients) {
            const url = `/api/v2/dashboard${appendSelectionSource(queryString, 'client')}`;
            promises.push(fetch(url).then(r => r.json()));
            sources.push('client');
        }
        if (hasFunds) {
            const url = `/api/v2/dashboard${appendSelectionSource(queryString, 'fund')}`;
            promises.push(fetch(url).then(r => r.json()));
            sources.push('fund');
        }
        if (hasAccounts) {
            const url = `/api/v2/dashboard${appendSelectionSource(queryString, 'account')}`;
            promises.push(fetch(url).then(r => r.json()));
            sources.push('account');
        }
        
        // Execute all promises and handle failures gracefully
        let allClientsData = null;
        let allFundsData = null;
        let allAccountsData = null;
        
        if (promises.length > 0) {
            const results = await Promise.allSettled(promises);
            
            results.forEach((result, index) => {
                const source = sources[index];
                if (result.status === 'fulfilled') {
                    switch (source) {
                        case 'client':
                            allClientsData = result.value;
                            break;
                        case 'fund':
                            allFundsData = result.value;
                            break;
                        case 'account':
                            allAccountsData = result.value;
                            break;
                    }
                } else {
                    console.error(`Failed to fetch all ${source} data:`, result.reason);
                    // Fallback handled by null checks below
                }
            });
        }
        
        // Update filter type for indicator
        currentFilter = { type: 'multi', filters: data.metadata ? data.metadata.filters_applied : data.filters };
        
        // Update charts and KPIs with intersection data
        if (data.charts) {
            // v2 API format
            chartManager.update({
                recent_history: data.charts.recent_history,
                long_term_history: data.charts.long_term_history
            });
        } else {
            // v1 API format
            chartManager.update(data);
        }
        updateKPICards(data);
        
        // Combine data for tables with fallback to intersection data
        const tableData = {
            client_balances: hasClients && allClientsData ? allClientsData.client_balances : data.client_balances,
            fund_balances: hasFunds && allFundsData ? allFundsData.fund_balances : data.fund_balances,
            account_details: hasAccounts && allAccountsData ? allAccountsData.account_details : data.account_details
        };
        
        // Update all tables with combined data
        await tablesV2.updateTables(tableData);
        
        // Update CSV row count
        updateDownloadButton();
        
        // Restore visual selections
        restoreSelectionVisuals();
        
    } catch (error) {
        console.error('Error loading filtered data:', error);
        // Fallback to overview on error
        await loadOverviewData();
    }
}

// Load client-fund combination data
async function loadClientFundData(clientId, clientName, fundName) {
    try {
        const response = await fetch(`/api/client/${clientId}/fund/${encodeURIComponent(fundName)}` + buildQueryString());
        const data = await response.json();
        
        currentFilter = { type: 'client-fund', clientId, clientName, fundName };
        
        chartManager.update(data);
        
        // Update all tables with the combined data
        await tablesV2.updateTables(data);
        updateKPICards(data);
        
        // Update CSV row count
        updateDownloadButton();
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading client-fund data:', error);
    }
}

// Clear all selections
function clearAllSelections() {
    selectionState.clients.clear();
    selectionState.funds.clear();
    selectionState.accounts.clear();
    
    document.querySelectorAll('tr.selected').forEach(r => r.classList.remove('selected'));
}

// Check if any selections exist
function hasAnySelections() {
    return selectionState.clients.size > 0 || 
           selectionState.funds.size > 0 || 
           selectionState.accounts.size > 0;
}

// Clear only the date filter while preserving selections
function clearDateFilter() {
    currentFilter = { type: 'overview', value: null };
    if (hasAnySelections()) {
        updateDataBasedOnSelections();
    } else {
        loadOverviewData();
    }
}

// Restore visual selections after data refresh
function restoreSelectionVisuals() {
    // Use requestAnimationFrame to ensure DOM has updated
    requestAnimationFrame(() => {
        // Restore client selections
        selectionState.clients.forEach(clientId => {
            const row = document.querySelector(`#clientTable tr[data-client-id="${clientId}"]`);
            if (row) {
                row.classList.add('selected');
            }
        });
        
        // Restore fund selections
        selectionState.funds.forEach(fundName => {
            const rows = document.querySelectorAll('#fundTable tbody tr');
            rows.forEach(row => {
                if (row.dataset.fundName === fundName) {
                    row.classList.add('selected');
                }
            });
        });
        
        // Restore account selections
        selectionState.accounts.forEach(accountId => {
            const row = document.querySelector(`#accountTable tr[data-account-id="${accountId}"]`);
            if (row) {
                row.classList.add('selected');
            }
        });
    });
}

// Check if click is outside all tables
function isClickOutsideTables(target) {
    const tables = ['clientTable', 'fundTable', 'accountTable'];
    for (let tableId of tables) {
        const table = document.getElementById(tableId);
        if (table && table.contains(target)) {
            return false;
        }
    }
    return true;
}

// Format currency (for display in tables, KPIs, etc.)
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

// Format currency in millions for chart axes
function formatCurrencyInMillions(value) {
    const millions = value / 1000000;
    return '$' + millions.toFixed(1) + 'M';
}

// Format date for recent chart
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Format date for long-term chart
function formatDateLong(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: '2-digit', month: 'short' });
}

// Format percentage
function formatPercentage(value) {
    if (value === null || value === undefined) return '<span class="neutral">N/A</span>';
    
    // If we receive HTML content (already formatted), extract the numeric value
    if (typeof value === 'string') {
        if (value.includes('<span')) {
            // Extract number from already formatted HTML
            const match = value.match(/([+-]?\d+\.?\d*)/);
            if (match) {
                value = parseFloat(match[1]);
            } else {
                return '<span class="neutral">N/A</span>';
            }
        } else {
            // Parse regular string number
            value = parseFloat(value);
        }
    }
    
    if (isNaN(value)) return '<span class="neutral">N/A</span>';
    
    const formatted = value.toFixed(1);
    const prefix = value > 0 ? '+' : '';
    const className = value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';
    return `<span class="${className}">${prefix}${formatted}%</span>`;
}

// CSV Download Functions
// Helper function to build download parameters
function getDownloadParams() {
    const params = new URLSearchParams();
    
    selectionState.clients.forEach(clientId => params.append('client_id', clientId));
    selectionState.funds.forEach(fundName => params.append('fund_name', fundName));
    selectionState.accounts.forEach(accountId => params.append('account_id', accountId));
    
    if (textFilters.fundTicker) params.append('fund_ticker', textFilters.fundTicker);
    if (textFilters.clientName) params.append('client_name', textFilters.clientName);
    if (textFilters.accountNumber) params.append('account_number', textFilters.accountNumber);
    
    if (currentFilter.type === 'date' && currentFilter.value) {
        params.append('date', currentFilter.value);
    }
    
    return params;
}

async function fetchDownloadCount() {
    try {
        const params = getDownloadParams();
        const response = await fetch(`/api/download_csv/count?${params.toString()}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error fetching count:', data.error);
            return null;
        }
        
        return data.count;
    } catch (error) {
        console.error('Error fetching download count:', error);
        return null;
    }
}

function updateDownloadButton() {
    const downloadBtn = document.getElementById('download-csv-btn');
    const downloadText = document.getElementById('download-text');
    
    if (!downloadBtn || !downloadText) return;
    
    // Show loading state
    downloadText.textContent = 'Download Loading...';
    downloadBtn.disabled = true;
    
    fetchDownloadCount().then(count => {
        if (count !== null) {
            downloadText.textContent = `Download ${count.toLocaleString()} rows`;
            downloadBtn.disabled = false;
            
            // Add warning styling if large
            if (count > 100000) {
                downloadBtn.classList.add('warning');
            } else {
                downloadBtn.classList.remove('warning');
            }
            
            // Adjust font size based on text length
            const textLength = downloadText.textContent.length;
            if (textLength > 25) {
                downloadText.style.fontSize = '11px';
            } else if (textLength > 20) {
                downloadText.style.fontSize = '12px';
            } else {
                downloadText.style.fontSize = '13px';
            }
        } else {
            downloadText.textContent = 'Download Error';
            downloadBtn.disabled = true;
        }
    });
}

function downloadCSV() {
    const downloadBtn = document.getElementById('download-csv-btn');
    const downloadText = document.getElementById('download-text');
    const originalText = downloadText.textContent;
    
    // Show downloading state
    downloadText.textContent = 'Downloading...';
    downloadBtn.disabled = true;
    
    // Build download URL
    const params = getDownloadParams();
    
    // Trigger download
    window.location.href = `/api/download_csv?${params.toString()}`;
    
    // Reset button after a delay
    setTimeout(() => {
        downloadText.textContent = originalText;
        downloadBtn.disabled = false;
    }, 2000);
}

// Update existing updateDataBasedOnSelections to also update download count
const originalUpdateData = updateDataBasedOnSelections;
updateDataBasedOnSelections = function() {
    originalUpdateData();
    updateDownloadButton();
}