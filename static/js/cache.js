// Normalized cache implementation for v2 API migration
const appCache = {
    // Configuration
    config: {
        defaultTTL: 5 * 60 * 1000, // 5 minutes
        queryTTL: 2 * 60 * 1000,   // 2 minutes for query results
    },

    // Normalized entities storage
    entities: {
        clients: {},    // { clientId: { ...clientData } }
        funds: {},      // { fundName: { ...fundData } }
        accounts: {},   // { accountId: { ...accountData } }
    },

    // Query results storage (stores entity IDs/names, not full data)
    queries: {}, // { queryHash: { result: {...}, timestamp: Date.now() } }

    // Entity management
    setClient(clientData) {
        if (!clientData.client_id) return;
        this.entities.clients[clientData.client_id] = {
            ...clientData,
            _timestamp: Date.now()
        };
    },

    setFund(fundData) {
        if (!fundData.fund_name) return;
        this.entities.funds[fundData.fund_name] = {
            ...fundData,
            _timestamp: Date.now()
        };
    },

    setAccount(accountData) {
        if (!accountData.account_id) return;
        this.entities.accounts[accountData.account_id] = {
            ...accountData,
            _timestamp: Date.now()
        };
    },

    getClient(clientId) {
        return this.entities.clients[clientId] || null;
    },

    getFund(fundName) {
        return this.entities.funds[fundName] || null;
    },

    getAccount(accountId) {
        return this.entities.accounts[accountId] || null;
    },

    // Bulk entity operations
    setClients(clientsArray) {
        clientsArray.forEach(client => this.setClient(client));
    },

    setFunds(fundsArray) {
        fundsArray.forEach(fund => this.setFund(fund));
    },

    setAccounts(accountsArray) {
        accountsArray.forEach(account => this.setAccount(account));
    },

    // Query management
    setQuery(queryHash, result, ttl = null) {
        this.queries[queryHash] = {
            result: result,
            timestamp: Date.now(),
            ttl: ttl || this.config.queryTTL
        };
    },

    getQuery(queryHash) {
        const query = this.queries[queryHash];
        if (!query) return null;

        const now = Date.now();
        if (now - query.timestamp > query.ttl) {
            delete this.queries[queryHash];
            return null;
        }

        return query.result;
    },

    // Normalize API response into cache
    normalizeResponse(apiResponse) {
        const normalized = {
            clientIds: [],
            fundNames: [],
            accountIds: []
        };

        // Normalize client balances
        if (apiResponse.client_balances) {
            apiResponse.client_balances.forEach(client => {
                this.setClient(client);
                normalized.clientIds.push(client.client_id);
            });
        }

        // Normalize fund balances
        if (apiResponse.fund_balances) {
            apiResponse.fund_balances.forEach(fund => {
                this.setFund(fund);
                normalized.fundNames.push(fund.fund_name);
            });
        }

        // Normalize account details
        if (apiResponse.account_details) {
            apiResponse.account_details.forEach(account => {
                this.setAccount(account);
                normalized.accountIds.push(account.account_id);
            });
        }

        return normalized;
    },

    // Cache invalidation
    invalidateClient(clientId) {
        delete this.entities.clients[clientId];
        this.invalidateQueriesContaining('client', clientId);
    },

    invalidateFund(fundName) {
        delete this.entities.funds[fundName];
        this.invalidateQueriesContaining('fund', fundName);
    },

    invalidateAccount(accountId) {
        delete this.entities.accounts[accountId];
        this.invalidateQueriesContaining('account', accountId);
    },

    invalidateQueriesContaining(type, value) {
        Object.keys(this.queries).forEach(queryHash => {
            const query = this.queries[queryHash];
            if (type === 'client' && query.result.clientIds?.includes(value)) {
                delete this.queries[queryHash];
            } else if (type === 'fund' && query.result.fundNames?.includes(value)) {
                delete this.queries[queryHash];
            } else if (type === 'account' && query.result.accountIds?.includes(value)) {
                delete this.queries[queryHash];
            }
        });
    },

    // Selective invalidation based on selections
    invalidateBySelections(selections) {
        // Invalidate queries that would be affected by these selections
        Object.keys(this.queries).forEach(queryHash => {
            const shouldInvalidate = this.queryAffectedBySelections(queryHash, selections);
            if (shouldInvalidate) {
                delete this.queries[queryHash];
            }
        });
    },

    queryAffectedBySelections(queryHash, selections) {
        // Parse query hash to determine if selections affect it
        // This is a simplified version - enhance based on actual query structure
        if (selections.clients.size > 0 || selections.funds.size > 0 || selections.accounts.size > 0) {
            // For now, invalidate all queries when selections change
            // TODO: Implement more granular invalidation logic
            return true;
        }
        return false;
    },

    // Clear all cache
    clear() {
        this.entities = {
            clients: {},
            funds: {},
            accounts: {}
        };
        this.queries = {};
    },

    // Get denormalized data for UI
    getDenormalizedData(entityIds) {
        return {
            clients: entityIds.clientIds?.map(id => this.getClient(id)).filter(Boolean) || [],
            funds: entityIds.fundNames?.map(name => this.getFund(name)).filter(Boolean) || [],
            accounts: entityIds.accountIds?.map(id => this.getAccount(id)).filter(Boolean) || []
        };
    },

    // Generate cache key for queries
    generateQueryHash(endpoint, params) {
        const sortedParams = Object.keys(params)
            .sort()
            .reduce((acc, key) => {
                if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
                    acc[key] = params[key];
                }
                return acc;
            }, {});
        
        return `${endpoint}:${JSON.stringify(sortedParams)}`;
    },

    // Debug helpers
    getCacheStats() {
        return {
            clients: Object.keys(this.entities.clients).length,
            funds: Object.keys(this.entities.funds).length,
            accounts: Object.keys(this.entities.accounts).length,
            queries: Object.keys(this.queries).length,
            totalSize: JSON.stringify(this).length
        };
    }
};

// Make cache available globally
window.appCache = appCache;