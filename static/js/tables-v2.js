// V2 Table implementation using v2 API
const tablesV2 = {
    // Table update functions
    updateClientTable(data) {
        const tbody = document.querySelector('#clientTable tbody');
        tbody.innerHTML = '';
        
        if (!data || !Array.isArray(data)) {
            console.error('[Tables V2] Invalid data for client table:', data);
            return;
        }
        
        console.log('[Tables V2] Updating client table with', data.length, 'items');
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
    },
    
    updateFundTable(data) {
        const tbody = document.querySelector('#fundTable tbody');
        tbody.innerHTML = '';
        
        if (!data || !Array.isArray(data)) {
            console.error('[Tables V2] Invalid data for fund table:', data);
            return;
        }
        
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
    },
    
    updateAccountTable(data) {
        const tbody = document.querySelector('#accountTable tbody');
        tbody.innerHTML = '';
        
        if (!data || !Array.isArray(data)) {
            console.error('[Tables V2] Invalid data for account table:', data);
            return;
        }
        
        data.forEach(account => {
            const row = tbody.insertRow();
            row.dataset.accountId = account.account_id;
            
            // Check if this account is selected
            if (selectionState.accounts.has(account.account_id)) {
                row.classList.add('selected');
            }
            
            row.innerHTML = `
                <td>${account.account_id}</td>
                <td class="number">${formatCurrency(account.total_balance || account.balance || 0)}</td>
                <td class="number">${formatPercentage(account.qtd_change)}</td>
                <td class="number">${formatPercentage(account.ytd_change)}</td>
            `;
        });
    },
    
    // Main update function that accepts either data or params
    async updateTables(dataOrParams) {
        try {
            let data;
            
            // Check if we received data directly (has the expected properties)
            if (dataOrParams && (dataOrParams.client_balances !== undefined || 
                                 dataOrParams.fund_balances !== undefined || 
                                 dataOrParams.account_details !== undefined)) {
                console.log('[Tables V2] Using provided data');
                data = dataOrParams;
            } else {
                // Legacy path: fetch data using params
                console.log('[Tables V2] Fetching data with params:', dataOrParams);
                const params = dataOrParams || {};
                
                // Build params for apiWrapper.loadData
                const apiParams = {
                    useDataEndpoint: true, // Use /api/data endpoint for v1 compatibility
                    queryString: params.queryString || '' // Use queryString from app.js
                };
                
                // Add specific params if provided
                if (params.clientId) apiParams.clientId = params.clientId;
                if (params.fundName) apiParams.fundName = params.fundName;
                if (params.accountId) apiParams.accountId = params.accountId;
                if (params.date) apiParams.date = params.date;
                
                // Use the API wrapper to fetch data
                data = await apiWrapper.loadData(apiParams);
            }
            
            // Only update tables that have data (avoid clearing with undefined)
            if (data.client_balances !== undefined) {
                this.updateClientTable(data.client_balances);
            }
            if (data.fund_balances !== undefined) {
                this.updateFundTable(data.fund_balances);
            }
            if (data.account_details !== undefined) {
                this.updateAccountTable(data.account_details);
            }
            
            // Return the data for other components that might need it
            return data;
            
        } catch (error) {
            console.error('[Tables V2] Error updating tables:', error);
            // Clear tables on error
            this.clearTables();
            throw error;
        }
    },
    
    // Clear all tables
    clearTables() {
        console.log('[Tables V2] Clearing all tables');
        document.querySelector('#clientTable tbody').innerHTML = '';
        document.querySelector('#fundTable tbody').innerHTML = '';
        document.querySelector('#accountTable tbody').innerHTML = '';
    },
    
    // Initialize (called once on page load)
    init() {
        console.log('[Tables V2] Initialized with v2 API');
        // Tables don't need special initialization like charts
        // Event handlers are managed by the main app.js
    }
};

// Make it available globally
window.tablesV2 = tablesV2;