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

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    applyMobileClass();
    initializeCharts();
    initializeTableHandlers();
    loadOverviewData();
    
    // Add document click listener for clearing selections
    document.addEventListener('click', function(e) {
        // Check if click is outside all tables and header
        if (isClickOutsideTables(e.target) && !e.target.closest('header')) {
            // Clear all selections and go to overview
            if (selectionState.clients.size > 0 || selectionState.funds.size > 0 || selectionState.accounts.size > 0) {
                clearAllSelections();
                loadOverviewData();
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
    // Calculate Total AUM from latest balance data
    const latestBalance = data.recent_history && data.recent_history.length > 0 
        ? data.recent_history[data.recent_history.length - 1].total_balance 
        : 0;
    
    // Calculate AUM change (compare to 30 days ago)
    let aumChange = null;
    if (data.recent_history && data.recent_history.length >= 30) {
        const thirtyDaysAgo = data.recent_history[data.recent_history.length - 30].total_balance;
        aumChange = ((latestBalance - thirtyDaysAgo) / thirtyDaysAgo * 100);
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
        countValue = data.account_details ? data.account_details.length : 0;
    } else if (currentFilter.type === 'multi-client') {
        // When viewing multiple clients, show account count
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = data.account_details ? data.account_details.length : 0;
    } else if (currentFilter.type === 'fund' || currentFilter.type === 'fund-account') {
        // When viewing a specific fund, show client count for that fund
        countLabel = 'Active Clients';
        countValue = data.client_balances ? data.client_balances.length : 0;
    } else if (currentFilter.type === 'multi-fund') {
        // When viewing multiple funds, show client count
        countLabel = 'Active Clients';
        countValue = data.client_balances ? data.client_balances.length : 0;
    } else if (currentFilter.type === 'account' || currentFilter.type === 'account-fund') {
        // When viewing a specific account, show 1 account
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = 1;
    } else if (currentFilter.type === 'multi-client-fund') {
        // When viewing multiple clients and funds, show account count
        countLabel = 'Active Accounts';
        countIcon = 'A';
        countValue = data.account_details ? data.account_details.length : 0;
    } else {
        // Overview mode - show total clients
        countValue = data.client_balances ? data.client_balances.length : 0;
    }
    
    // Count funds based on context
    let totalFunds = 0;
    if (currentFilter.type === 'client' || currentFilter.type === 'client-account') {
        // When viewing a client, show funds they're invested in
        totalFunds = data.fund_balances ? data.fund_balances.length : 0;
    } else if (currentFilter.type === 'multi-client') {
        // When viewing multiple clients, show funds across all clients
        totalFunds = data.fund_balances ? data.fund_balances.length : 0;
    } else if (currentFilter.type === 'client-fund' || currentFilter.type === 'client-fund-account' || 
               currentFilter.type === 'client-fund-multi-account') {
        // When viewing a client-fund combination, show 1 fund
        totalFunds = 1;
    } else if (currentFilter.type === 'fund' || currentFilter.type === 'fund-account') {
        // When viewing a fund, show 1 fund
        totalFunds = 1;
    } else if (currentFilter.type === 'multi-fund') {
        // When viewing multiple funds, show selected fund count
        totalFunds = data.fund_balances ? data.fund_balances.length : 0;
    } else if (currentFilter.type === 'account' || currentFilter.type === 'account-fund') {
        // When viewing an account, count unique funds
        totalFunds = data.fund_allocation ? data.fund_allocation.length : 0;
    } else if (currentFilter.type === 'multi-client-fund') {
        // When viewing multiple clients and funds, show fund count
        totalFunds = data.fund_balances ? data.fund_balances.length : 0;
    } else {
        // Overview mode - show total funds
        totalFunds = data.fund_balances ? data.fund_balances.length : 0;
    }
    
    // Calculate average YTD growth based on visible data
    let avgYtdGrowth = 0;
    let dataForGrowth = [];
    
    // Determine which data to use for growth calculation
    if (currentFilter.type === 'overview' || currentFilter.type === 'date') {
        dataForGrowth = data.client_balances || [];
    } else if (currentFilter.type === 'client' || currentFilter.type === 'client-account') {
        // For client view, use fund balances to calculate weighted average
        dataForGrowth = data.fund_balances || [];
    } else if (currentFilter.type === 'multi-client') {
        // For multi-client view, use client balances
        dataForGrowth = data.client_balances || [];
    } else if (currentFilter.type === 'client-fund' || currentFilter.type === 'client-fund-account' || 
               currentFilter.type === 'client-fund-multi-account') {
        // For client-fund view, use the single fund balance data
        if (data.fund_balance) {
            dataForGrowth = [data.fund_balance];
        } else {
            dataForGrowth = data.fund_balances || [];
        }
    } else if (currentFilter.type === 'fund' || currentFilter.type === 'fund-account') {
        dataForGrowth = data.client_balances || [];
    } else if (currentFilter.type === 'multi-fund') {
        // For multi-fund view, use fund balances
        dataForGrowth = data.fund_balances || [];
    } else if (currentFilter.type === 'account' || currentFilter.type === 'account-fund') {
        // For single account, use account details if available
        dataForGrowth = data.account_details || [];
    } else if (currentFilter.type === 'multi-client-fund') {
        // For multi-client-fund view, use fund balances
        dataForGrowth = data.fund_balances || [];
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
    document.getElementById('totalAUM').textContent = formatCurrency(latestBalance);
    
    // Update client/account count
    const clientIcon = document.querySelector('.kpi-card:nth-child(2) .kpi-icon');
    const clientLabel = document.querySelector('.kpi-card:nth-child(2) .kpi-label');
    clientIcon.textContent = countIcon;
    clientLabel.textContent = countLabel;
    document.getElementById('totalClients').textContent = countValue;
    
    document.getElementById('totalFunds').textContent = totalFunds;
    document.getElementById('avgGrowth').textContent = avgYtdGrowth.toFixed(1) + '%';
    
    // Update AUM change indicator
    const aumChangeEl = document.getElementById('aumChange');
    if (aumChange !== null) {
        const changeClass = aumChange > 0 ? 'positive' : aumChange < 0 ? 'negative' : 'neutral';
        const prefix = aumChange > 0 ? '+' : '';
        aumChangeEl.textContent = `${prefix}${aumChange.toFixed(1)}% last 30 days`;
        aumChangeEl.className = `kpi-change ${changeClass}`;
    } else {
        aumChangeEl.textContent = '--';
        aumChangeEl.className = 'kpi-change neutral';
    }
    
    // Update growth trend
    const growthTrendEl = document.getElementById('growthTrend');
    const trendClass = avgYtdGrowth > 0 ? 'positive' : avgYtdGrowth < 0 ? 'negative' : 'neutral';
    const trendPrefix = avgYtdGrowth > 0 ? '↑' : avgYtdGrowth < 0 ? '↓' : '→';
    growthTrendEl.textContent = `${trendPrefix} Trending`;
    growthTrendEl.className = `kpi-change ${trendClass}`;
}

// Handle chart clicks for drill-down
function handleChartClick(chartType, dataIndex) {
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
                            return formatCurrency(value);
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
                if (elements.length > 0) {
                    // Clicked on a data point
                    handleChartClick('recent', elements[0].index);
                } else {
                    // Clicked on empty area - find nearest point
                    const canvasPosition = Chart.helpers.getRelativePosition(event, chart);
                    const dataX = chart.scales.x.getValueForPixel(canvasPosition.x);
                    const dataIndex = chart.scales.x.getValueForPixel(canvasPosition.x);
                    
                    // Find the closest data point
                    if (dataIndex >= 0 && dataIndex < chart.data.labels.length) {
                        const nearestIndex = Math.round(dataIndex);
                        console.log('Nearest index:', nearestIndex);
                        handleChartClick('recent', nearestIndex);
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
                        maxRotation: 45,
                        minRotation: 45,
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
                            return formatCurrency(value);
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
                if (elements.length > 0) {
                    // Clicked on a data point
                    handleChartClick('longTerm', elements[0].index);
                } else {
                    // Clicked on empty area - find nearest point
                    const canvasPosition = Chart.helpers.getRelativePosition(event, chart);
                    const dataX = chart.scales.x.getValueForPixel(canvasPosition.x);
                    const dataIndex = chart.scales.x.getValueForPixel(canvasPosition.x);
                    
                    // Find the closest data point
                    if (dataIndex >= 0 && dataIndex < chart.data.labels.length) {
                        const nearestIndex = Math.round(dataIndex);
                        console.log('Nearest index:', nearestIndex);
                        handleChartClick('longTerm', nearestIndex);
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
        const response = await fetch('/api/overview');
        const data = await response.json();
        allData = data;
        
        currentFilter = { type: 'overview', value: null };
        updateFilterIndicator('All Clients - All Funds');
        updateKPICards(data);
        updateRecentChart(data.recent_history);
        updateLongTermChart(data.long_term_history);
        updateClientTable(data.client_balances);
        updateFundTable(data.fund_balances);
        updateAccountTable(data.account_details);
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading overview data:', error);
    }
}

// Load data for a specific date
async function loadDateData(dateString) {
    try {
        const response = await fetch(`/api/date/${dateString}`);
        const data = await response.json();
        
        currentFilter = { type: 'date', value: dateString };
        updateFilterIndicator(`Date: ${formatDateLong(dateString)}`);
        updateKPICards(data);
        
        // Keep the chart history but update tables with date-specific data
        updateRecentChart(data.recent_history);
        updateLongTermChart(data.long_term_history);
        
        // Update tables with data for the selected date (with QTD/YTD calculated relative to the date)
        updateClientTable(data.client_balances);
        updateFundTable(data.fund_balances);
        updateAccountTable(data.account_details);
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading date data:', error);
    }
}

// Load client-specific data
async function loadClientData(clientId, clientName) {
    try {
        const response = await fetch(`/api/client/${clientId}`);
        const data = await response.json();
        
        currentFilter = { type: 'client', value: clientId, name: clientName };
        updateRecentChart(data.recent_history);
        updateLongTermChart(data.long_term_history);
        
        // Update tables with filtered data
        // Keep full client list but highlight selected
        if (allData && allData.client_balances) {
            updateClientTable(allData.client_balances);
        }
        
        // Show funds for selected client
        updateFundTable(data.fund_balances);
        
        // Show accounts for selected client
        updateAccountTable(data.account_details.map(acc => ({ ...acc, client_name: clientName })));
        
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
        const response = await fetch(`/api/fund/${encodeURIComponent(fundName)}`);
        const data = await response.json();
        
        currentFilter = { type: 'fund', value: fundName };
        updateRecentChart(data.recent_history);
        updateLongTermChart(data.long_term_history);
        
        // Show clients that have this fund
        updateClientTable(data.client_balances);
        
        // Keep full fund list but highlight selected
        if (allData && allData.fund_balances) {
            updateFundTable(allData.fund_balances);
        }
        
        // Show accounts with this fund
        updateAccountTable(data.account_details.map(acc => ({ ...acc, fund_name: fundName })));
        
        // Update KPIs with fund data
        updateKPICards(data);
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading fund data:', error);
    }
}

// Load account-specific data
async function loadAccountData(accountId) {
    try {
        const response = await fetch(`/api/account/${encodeURIComponent(accountId)}`);
        const data = await response.json();
        
        currentFilter = { type: 'account', value: accountId };
        
        // Update charts with account history
        updateRecentChart(data.recent_history);
        updateLongTermChart(data.long_term_history);
        
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
        if (clientId) {
            const client = allData.client_balances.find(c => c.client_id === clientId);
            if (client) {
                // Calculate total balance for this account across all funds
                const accountTotal = data.fund_allocation.reduce((sum, fund) => sum + fund.balance, 0);
                updateClientTable([{
                    ...client,
                    total_balance: accountTotal
                }]);
            }
        }
        
        // Show funds in this account
        updateFundTable(data.fund_allocation.map(f => ({ 
            ...f, 
            total_balance: f.balance, 
            account_count: 1,
            qtd_change: null,
            ytd_change: null
        })));
        
        // Show accounts based on current selection context
        if (selectionState.clients.size > 0 && selectionState.funds.size > 0) {
            // If client and fund are selected, show only accounts for that combination
            const selectedClientId = Array.from(selectionState.clients)[0];
            const selectedFundName = Array.from(selectionState.funds)[0];
            
            // Fetch the filtered account list
            const filteredResponse = await fetch(`/api/client/${selectedClientId}/fund/${encodeURIComponent(selectedFundName)}`);
            const filteredData = await filteredResponse.json();
            updateAccountTable(filteredData.account_details);
        } else if (selectionState.clients.size > 0) {
            // If only client is selected, show accounts for that client
            const selectedClientId = Array.from(selectionState.clients)[0];
            const clientResponse = await fetch(`/api/client/${selectedClientId}`);
            const clientData = await clientResponse.json();
            updateAccountTable(clientData.account_details);
        } else if (selectionState.funds.size > 0) {
            // If only fund is selected, show accounts for that fund
            const selectedFundName = Array.from(selectionState.funds)[0];
            const fundResponse = await fetch(`/api/fund/${encodeURIComponent(selectedFundName)}`);
            const fundData = await fundResponse.json();
            updateAccountTable(fundData.account_details);
        } else {
            // No other selections, show all accounts
            if (allData && allData.account_details) {
                updateAccountTable(allData.account_details);
            }
        }
        
        // Update KPIs with account data
        updateKPICards(data);
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading account data:', error);
    }
}

// Load account data filtered by fund
async function loadAccountDataForFund(accountId, fundName) {
    try {
        const response = await fetch(`/api/account/${encodeURIComponent(accountId)}/fund/${encodeURIComponent(fundName)}`);
        const data = await response.json();
        
        currentFilter = { type: 'account-fund', accountId, fundName };
        
        // Update charts with account history for this specific fund
        updateRecentChart(data.recent_history);
        updateLongTermChart(data.long_term_history);
        
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
        if (clientId) {
            const client = allData.client_balances.find(c => c.client_id === clientId);
            if (client) {
                // Show client with only the account-fund specific balance
                updateClientTable([{
                    ...client,
                    total_balance: data.fund_allocation[0]?.balance || 0
                }]);
            }
        }
        
        // Show only the selected fund for this account
        updateFundTable([{ 
            fund_name: fundName,
            total_balance: data.fund_allocation[0]?.balance || 0,
            account_count: 1,
            qtd_change: null,
            ytd_change: null
        }]);
        
        // Show accounts based on current selection context
        if (selectionState.clients.size > 0 && selectionState.funds.size > 0) {
            // If client and fund are selected, show only accounts for that combination
            const selectedClientId = Array.from(selectionState.clients)[0];
            const selectedFundName = Array.from(selectionState.funds)[0];
            
            // Fetch the filtered account list
            const filteredResponse = await fetch(`/api/client/${selectedClientId}/fund/${encodeURIComponent(selectedFundName)}`);
            const filteredData = await filteredResponse.json();
            updateAccountTable(filteredData.account_details);
        } else if (selectionState.funds.size > 0) {
            // If only fund is selected, show accounts for that fund
            const selectedFundName = Array.from(selectionState.funds)[0];
            const fundResponse = await fetch(`/api/fund/${encodeURIComponent(selectedFundName)}`);
            const fundData = await fundResponse.json();
            updateAccountTable(fundData.account_details);
        } else {
            // No other selections, show all accounts
            if (allData && allData.account_details) {
                updateAccountTable(allData.account_details);
            }
        }
        
        // Update KPIs with account data
        updateKPICards(data);
        
        // Restore visual selections
        restoreSelectionVisuals();
    } catch (error) {
        console.error('Error loading account data for fund:', error);
    }
}

// Update filter indicator
function updateFilterIndicator(text) {
    document.getElementById('current-filter').textContent = `Viewing: ${text}`;
}

// Update recent chart (90 days)
function updateRecentChart(data) {
    if (!data || data.length === 0) return;
    
    recentChart.data.labels = data.map(item => formatDate(item.balance_date));
    recentChart.data.datasets[0].data = data.map(item => item.total_balance);
    recentChart.update();
}

// Update long-term chart (3 years)
function updateLongTermChart(data) {
    if (!data || data.length === 0) return;
    
    // Show all daily data points without sampling
    longTermChart.data.labels = data.map(item => formatDateLong(item.balance_date));
    longTermChart.data.datasets[0].data = data.map(item => item.total_balance);
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

// Update client table
function updateClientTable(data) {
    const tbody = document.querySelector('#clientTable tbody');
    tbody.innerHTML = '';
    
    data.forEach(client => {
        const row = tbody.insertRow();
        row.dataset.clientId = client.client_id;
        row.dataset.clientName = client.client_name;
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
    
    data.forEach(fund => {
        const row = tbody.insertRow();
        row.dataset.fundName = fund.fund_name;
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
    
    data.forEach(account => {
        const row = tbody.insertRow();
        row.dataset.accountId = account.account_id;
        // Store client and fund info in data attributes for filtering
        if (account.client_name) row.dataset.clientName = account.client_name;
        if (account.fund_name) row.dataset.fundName = account.fund_name;
        row.innerHTML = `
            <td>${account.account_id}</td>
            <td class="number">${formatCurrency(account.balance || account.total_balance || 0)}</td>
            <td class="number">${formatPercentage(account.qtd_change)}</td>
            <td class="number">${formatPercentage(account.ytd_change)}</td>
        `;
    });
}

// Initialize table click handlers once on page load
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
    
    // Update data based on current selections
    updateDataBasedOnSelections();
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
    
    // Update data based on current selections
    updateDataBasedOnSelections();
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

// Load filtered data based on multiple selections
async function loadFilteredData() {
    try {
        const hasClientSelection = selectionState.clients.size > 0;
        const hasFundSelection = selectionState.funds.size > 0;
        const hasAccountSelection = selectionState.accounts.size > 0;
        
        // Handle single client-fund combination with optional account selection
        if (selectionState.clients.size === 1 && selectionState.funds.size === 1) {
            const clientId = Array.from(selectionState.clients)[0];
            const fundName = Array.from(selectionState.funds)[0];
            const clientName = document.querySelector(`#clientTable tr[data-client-id="${clientId}"] td:first-child`)?.textContent || '';
            
            // Load client-fund data to maintain filtering
            const response = await fetch(`/api/client/${clientId}/fund/${encodeURIComponent(fundName)}`);
            const data = await response.json();
            
            currentFilter = { type: 'client-fund-multi-account', clientId, clientName, fundName };
            
            // If specific accounts are selected, calculate totals only for those accounts
            if (selectionState.accounts.size > 0) {
                // Filter account details to only selected accounts
                const selectedAccountIds = Array.from(selectionState.accounts);
                const filteredAccounts = data.account_details.filter(acc => 
                    selectedAccountIds.includes(acc.account_id)
                );
                
                // Calculate total balance for selected accounts only
                const selectedTotal = filteredAccounts.reduce((sum, acc) => sum + acc.balance, 0);
                
                // Update charts with the filtered total
                // We need to adjust the chart data to reflect only selected accounts
                const totalBalance = data.fund_balance.total_balance;
                updateRecentChart(data.recent_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * (selectedTotal / totalBalance)
                })));
                updateLongTermChart(data.long_term_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * (selectedTotal / totalBalance)
                })));
                
                // Update client table with selected accounts total
                updateClientTable([{ 
                    client_name: data.client_balance.client_name, 
                    client_id: data.client_balance.client_id, 
                    total_balance: selectedTotal,
                    qtd_change: data.fund_balance.qtd_change,
                    ytd_change: data.fund_balance.ytd_change
                }]);
                
                // Update fund table to show only the selected fund with selected accounts total
                updateFundTable([{
                    fund_name: fundName,
                    total_balance: selectedTotal,
                    account_count: selectedAccountIds.length,
                    qtd_change: data.fund_balance.qtd_change,
                    ytd_change: data.fund_balance.ytd_change
                }]);
            } else {
                // No specific accounts selected, show all data for client-fund
                updateRecentChart(data.recent_history);
                updateLongTermChart(data.long_term_history);
                
                updateClientTable([{ 
                    client_name: data.client_balance.client_name, 
                    client_id: data.client_balance.client_id, 
                    total_balance: data.client_balance.total_balance,
                    qtd_change: data.fund_balance.qtd_change,
                    ytd_change: data.fund_balance.ytd_change
                }]);
                
                // Show only the selected fund
                updateFundTable([{
                    fund_name: fundName,
                    total_balance: data.fund_balance.total_balance,
                    account_count: data.account_details.length,
                    qtd_change: data.fund_balance.qtd_change,
                    ytd_change: data.fund_balance.ytd_change
                }]);
            }
            
            // Show filtered accounts (only for this client-fund combination)
            updateAccountTable(data.account_details);
            updateKPICards(data);
            
            // Restore visual selections
            restoreSelectionVisuals();
        } 
        // Handle multiple clients only
        else if (hasClientSelection && !hasFundSelection && !hasAccountSelection) {
            const selectedClientIds = Array.from(selectionState.clients);
            
            // Fetch data for each selected client
            const clientDataPromises = selectedClientIds.map(clientId => 
                fetch(`/api/client/${clientId}`).then(r => r.json())
            );
            const clientDataArray = await Promise.all(clientDataPromises);
            
            // Aggregate client data
            const aggregatedClients = [];
            const fundMap = new Map();
            const accountsMap = new Map();
            let totalBalance = 0;
            
            // Combine data from all selected clients
            clientDataArray.forEach((data, index) => {
                const clientId = selectedClientIds[index];
                const clientInfo = allData.client_balances.find(c => c.client_id === clientId);
                
                if (clientInfo) {
                    aggregatedClients.push(clientInfo);
                    totalBalance += clientInfo.total_balance;
                }
                
                // Aggregate funds across clients
                data.fund_balances.forEach(fund => {
                    if (fundMap.has(fund.fund_name)) {
                        const existing = fundMap.get(fund.fund_name);
                        existing.total_balance += fund.total_balance;
                        existing.account_count += fund.account_count;
                    } else {
                        fundMap.set(fund.fund_name, { ...fund });
                    }
                });
                
                // Collect all accounts
                data.account_details.forEach(acc => {
                    accountsMap.set(acc.account_id, acc);
                });
            });
            
            // Aggregate chart data (combine from overview for now)
            const recentHistory = [];
            const longTermHistory = [];
            if (allData && allData.recent_history) {
                // Calculate the proportion of selected clients vs total
                const totalSystemBalance = allData.client_balances.reduce((sum, c) => sum + c.total_balance, 0);
                const selectedProportion = totalBalance / totalSystemBalance;
                
                recentHistory.push(...allData.recent_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * selectedProportion
                })));
                
                longTermHistory.push(...allData.long_term_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * selectedProportion
                })));
            }
            
            // Update UI
            currentFilter = { type: 'multi-client', clientIds: selectedClientIds };
            updateRecentChart(recentHistory);
            updateLongTermChart(longTermHistory);
            
            // Show ALL clients, not just selected ones
            if (allData && allData.client_balances) {
                updateClientTable(allData.client_balances);
            } else {
                updateClientTable(aggregatedClients);
            }
            
            updateFundTable(Array.from(fundMap.values()));
            updateAccountTable(Array.from(accountsMap.values()));
            updateKPICards({ 
                client_balances: aggregatedClients,
                fund_balances: Array.from(fundMap.values()),
                account_details: Array.from(accountsMap.values()),
                recent_history: recentHistory,
                long_term_history: longTermHistory
            });
            
            restoreSelectionVisuals();
        }
        // Handle multiple funds only
        else if (!hasClientSelection && hasFundSelection && !hasAccountSelection) {
            const selectedFundNames = Array.from(selectionState.funds);
            
            // Fetch data for each selected fund
            const fundDataPromises = selectedFundNames.map(fundName => 
                fetch(`/api/fund/${encodeURIComponent(fundName)}`).then(r => r.json())
            );
            const fundDataArray = await Promise.all(fundDataPromises);
            
            // Aggregate fund data
            const clientMap = new Map();
            const aggregatedFunds = [];
            const accountsMap = new Map();
            let totalBalance = 0;
            
            // Combine data from all selected funds
            fundDataArray.forEach((data, index) => {
                const fundName = selectedFundNames[index];
                const fundInfo = allData.fund_balances.find(f => f.fund_name === fundName);
                
                if (fundInfo) {
                    aggregatedFunds.push(fundInfo);
                    totalBalance += fundInfo.total_balance;
                }
                
                // Aggregate clients across funds
                data.client_balances.forEach(client => {
                    if (clientMap.has(client.client_id)) {
                        const existing = clientMap.get(client.client_id);
                        existing.total_balance += client.total_balance;
                    } else {
                        clientMap.set(client.client_id, { ...client });
                    }
                });
                
                // Collect all accounts
                data.account_details.forEach(acc => {
                    accountsMap.set(acc.account_id, acc);
                });
            });
            
            // Aggregate chart data
            const recentHistory = [];
            const longTermHistory = [];
            if (allData && allData.recent_history) {
                // Calculate the proportion of selected funds vs total
                const totalSystemBalance = allData.fund_balances.reduce((sum, f) => sum + f.total_balance, 0);
                const selectedProportion = totalBalance / totalSystemBalance;
                
                recentHistory.push(...allData.recent_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * selectedProportion
                })));
                
                longTermHistory.push(...allData.long_term_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * selectedProportion
                })));
            }
            
            // Update UI
            currentFilter = { type: 'multi-fund', fundNames: selectedFundNames };
            updateRecentChart(recentHistory);
            updateLongTermChart(longTermHistory);
            updateClientTable(Array.from(clientMap.values()));
            
            // Show ALL funds, not just selected ones
            if (allData && allData.fund_balances) {
                updateFundTable(allData.fund_balances);
            } else {
                updateFundTable(aggregatedFunds);
            }
            
            updateAccountTable(Array.from(accountsMap.values()));
            updateKPICards({ 
                client_balances: Array.from(clientMap.values()),
                fund_balances: aggregatedFunds,
                account_details: Array.from(accountsMap.values()),
                recent_history: recentHistory,
                long_term_history: longTermHistory
            });
            
            restoreSelectionVisuals();
        }
        // Handle multiple clients AND multiple funds (intersection)
        else if (hasClientSelection && hasFundSelection && (selectionState.clients.size > 1 || selectionState.funds.size > 1)) {
            const selectedClientIds = Array.from(selectionState.clients);
            const selectedFundNames = Array.from(selectionState.funds);
            
            // For intersection, we need to fetch client-fund combinations
            const promises = [];
            selectedClientIds.forEach(clientId => {
                selectedFundNames.forEach(fundName => {
                    promises.push(
                        fetch(`/api/client/${clientId}/fund/${encodeURIComponent(fundName)}`)
                            .then(r => r.json())
                            .then(data => ({ clientId, fundName, data }))
                            .catch(() => ({ clientId, fundName, data: null }))
                    );
                });
            });
            
            const results = await Promise.all(promises);
            
            // Aggregate the intersection data
            const clientTotals = new Map();
            const fundTotals = new Map();
            const accounts = [];
            let totalBalance = 0;
            
            results.forEach(({ clientId, fundName, data }) => {
                if (data && data.client_balance) {
                    // Track client totals
                    if (!clientTotals.has(clientId)) {
                        clientTotals.set(clientId, {
                            ...data.client_balance,
                            total_balance: 0
                        });
                    }
                    clientTotals.get(clientId).total_balance += data.fund_balance.total_balance;
                    
                    // Track fund totals
                    if (!fundTotals.has(fundName)) {
                        fundTotals.set(fundName, {
                            fund_name: fundName,
                            total_balance: 0,
                            account_count: 0,
                            qtd_change: data.fund_balance.qtd_change,
                            ytd_change: data.fund_balance.ytd_change
                        });
                    }
                    fundTotals.get(fundName).total_balance += data.fund_balance.total_balance;
                    fundTotals.get(fundName).account_count += data.account_details.length;
                    
                    // Collect accounts
                    accounts.push(...data.account_details);
                    totalBalance += data.fund_balance.total_balance;
                }
            });
            
            // Aggregate chart data based on intersection
            const recentHistory = [];
            const longTermHistory = [];
            if (allData && allData.recent_history && totalBalance > 0) {
                const totalSystemBalance = allData.client_balances.reduce((sum, c) => sum + c.total_balance, 0);
                const selectedProportion = totalBalance / totalSystemBalance;
                
                recentHistory.push(...allData.recent_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * selectedProportion
                })));
                
                longTermHistory.push(...allData.long_term_history.map(item => ({
                    ...item,
                    total_balance: item.total_balance * selectedProportion
                })));
            }
            
            // Update UI
            currentFilter = { type: 'multi-client-fund', clientIds: selectedClientIds, fundNames: selectedFundNames };
            updateRecentChart(recentHistory);
            updateLongTermChart(longTermHistory);
            
            // Show ALL clients and funds, not just selected ones
            if (allData && allData.client_balances) {
                updateClientTable(allData.client_balances);
            } else {
                updateClientTable(Array.from(clientTotals.values()));
            }
            
            if (allData && allData.fund_balances) {
                updateFundTable(allData.fund_balances);
            } else {
                updateFundTable(Array.from(fundTotals.values()));
            }
            
            updateAccountTable(accounts);
            updateKPICards({
                client_balances: Array.from(clientTotals.values()),
                fund_balances: Array.from(fundTotals.values()),
                account_details: accounts,
                recent_history: recentHistory,
                long_term_history: longTermHistory
            });
            
            restoreSelectionVisuals();
        }
        else {
            // For other complex selections, load overview
            await loadOverviewData();
        }
    } catch (error) {
        console.error('Error loading filtered data:', error);
        // Fallback to overview on error
        await loadOverviewData();
    }
}

// Load client-fund combination data
async function loadClientFundData(clientId, clientName, fundName) {
    try {
        const response = await fetch(`/api/client/${clientId}/fund/${encodeURIComponent(fundName)}`);
        const data = await response.json();
        
        currentFilter = { type: 'client-fund', clientId, clientName, fundName };
        
        updateRecentChart(data.recent_history);
        updateLongTermChart(data.long_term_history);
        
        // Update tables with filtered data
        updateClientTable([{ 
            client_name: data.client_balance.client_name, 
            client_id: data.client_balance.client_id, 
            total_balance: data.client_balance.total_balance,
            qtd_change: data.fund_balance.qtd_change,
            ytd_change: data.fund_balance.ytd_change
        }]);
        
        // Show all funds for this client
        const clientResponse = await fetch(`/api/client/${clientId}`);
        const clientData = await clientResponse.json();
        updateFundTable(clientData.fund_balances);
        
        updateAccountTable(data.account_details);
        updateKPICards(data);
        
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

// Restore visual selections after data refresh
function restoreSelectionVisuals() {
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

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
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
    const formatted = value.toFixed(1);
    const prefix = value > 0 ? '+' : '';
    const className = value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';
    return `<span class="${className}">${prefix}${formatted}%</span>`;
}