# KPI Fix Implementation Plan

## Problem Description
After implementing cross-table filtering, the Total AUM KPI card shows incorrect values:
- When clients are selected, Total AUM shows $248M (all clients) instead of the filtered amount
- Charts correctly show filtered data (~$106M for 3 selected clients)
- The "last 30 days" percentage is also calculated on unfiltered data

## Root Cause
The `updateKPICards` function in app.js calculates totalAUM by summing `data.client_balances`:
```javascript
const totalAUM = data.client_balances.reduce((sum, client) => sum + client.total_balance, 0);
```

However, after implementing cross-table filtering, `client_balances` returns ALL clients (using `client_where_clause` which excludes client_ids filter) to keep all clients visible in the table. This causes KPIs to show unfiltered totals.

## Solution Design

### Backend Changes (app.py - /api/data endpoint)

1. **Add KPI metrics query** after existing queries (around line 1787):

```python
# Get KPI metrics (using full filtering)
kpi_query = '''
    WITH current_totals AS (
        SELECT 
            SUM(ab.balance) as total_aum,
            COUNT(DISTINCT cm.client_id) as active_clients,
            COUNT(DISTINCT ab.fund_name) as active_funds,
            COUNT(DISTINCT ab.account_id) as active_accounts
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        {full_where_clause}
    ),
    past_totals AS (
        SELECT 
            SUM(ab.balance) as total_aum_30d_ago
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (
            SELECT MAX(balance_date) FROM account_balances 
            WHERE balance_date <= date((SELECT MAX(balance_date) FROM account_balances), '-30 days')
        )
        {full_where_clause}
    )
    SELECT 
        ct.total_aum,
        ct.active_clients,
        ct.active_funds,
        ct.active_accounts,
        pt.total_aum_30d_ago,
        CASE 
            WHEN pt.total_aum_30d_ago IS NULL OR pt.total_aum_30d_ago = 0 THEN 0
            ELSE ((ct.total_aum - pt.total_aum_30d_ago) / pt.total_aum_30d_ago) * 100
        END as change_30d_pct
    FROM current_totals ct, past_totals pt
'''

# Execute query
cursor.execute(kpi_query.format(full_where_clause=full_where_clause), full_params + full_params)
kpi_metrics = dict(cursor.fetchone())
```

2. **Add to response** (modify around line 1808):
```python
response_data = {
    'filters': {
        'client_ids': client_ids,
        'fund_names': fund_names,
        'account_ids': account_ids,
        'fund_ticker': fund_ticker_filter,
        'client_name': client_name_filter,
        'account_number': account_number_filter
    },
    'recent_history': recent_history,
    'long_term_history': long_term_history,
    'client_balances': client_balances,
    'fund_balances': fund_balances,
    'account_details': account_details,
    'kpi_metrics': kpi_metrics  # Add this line
}
```

### Frontend Changes (app.js - updateKPICards function)

Find the `updateKPICards` function (around line 350) and modify:

1. **Replace totalAUM calculation**:
```javascript
// OLD: const totalAUM = filteredData.client_balances.reduce((sum, client) => sum + client.total_balance, 0);
// NEW:
const totalAUM = filteredData.kpi_metrics ? filteredData.kpi_metrics.total_aum : 
                 filteredData.client_balances.reduce((sum, client) => sum + client.total_balance, 0);
```

2. **Update the change percentage**:
```javascript
// In the AUM card update section
const changePercent = filteredData.kpi_metrics ? filteredData.kpi_metrics.change_30d_pct : 0;
const changeText = changePercent > 0 ? `+${changePercent.toFixed(1)}%` : 
                   changePercent < 0 ? `${changePercent.toFixed(1)}%` : '0.0%';
document.querySelector('#kpi-aum .kpi-change').textContent = `${changeText} last 30 days`;
```

3. **Update other KPI counts**:
```javascript
// Active Clients
const activeClients = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_clients : 
                      filteredData.client_balances.length;

// Active Funds  
const activeFunds = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_funds :
                    filteredData.fund_balances.length;

// Active Accounts
const activeAccounts = filteredData.kpi_metrics ? filteredData.kpi_metrics.active_accounts :
                       filteredData.account_details.length;
```

## Important Context for Next Session

1. **Current State**: 
   - Cross-table filtering is working correctly
   - Client table shows ALL clients when some are selected
   - Fund/Account tables filter correctly
   - Only KPIs show wrong values

2. **Key Files Modified Previously**:
   - `app.py`: Added `exclude_filters` param to `build_filter_clause` function
   - `app.py`: Modified `/api/data` endpoint to use 3 different filter clauses
   - `app.js`: Already correctly passes selections via `buildQueryString(true)`

3. **Testing Steps After Implementation**:
   - Select 2-3 clients
   - Verify Total AUM shows sum of selected clients only
   - Verify percentage change is calculated on filtered data
   - Check all KPI cards update correctly
   - Test with different filter combinations

4. **Docker Commands**:
   - Rebuild: `./run.sh`
   - Test URL: `http://localhost:9095`

5. **Visual Confirmation**: 
   - Selected clients show blue background (#dbeafe)
   - All 10 clients remain visible in table
   - KPIs should match the chart totals