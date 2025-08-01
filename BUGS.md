# BUGS.md - Known Issues and Bug Reports

## ✅ RESOLVED: QTD/YTD Metrics Misalignment Across Tables

**Status**: Fixed  
**Priority**: High  
**Discovered**: January 2025  
**Reporter**: User observation during multi-selection testing  
**Fixed**: January 2025  
**Fix Author**: Claude Code collaboration with Gemini AI  

### Problem Description
When users make selections across multiple tables (clients, funds, accounts), the QTD and YTD percentages show different values in each table, even though they should represent the same time period and filtered dataset.

### Reproduction Steps
1. Navigate to overview page
2. Select "Client A" + "Fund B" + "Account X" combination
3. Observe the QTD/YTD values in each table
4. **BUG**: Each table shows different QTD/YTD percentages

### Expected vs Actual Behavior
- **Expected**: All tables show the SAME QTD/YTD values (e.g., +0.5% QTD, +2.1% YTD) for the intersection
- **Before Fix**: 
  - Client table: Shows QTD/YTD for Client A across ALL funds
  - Fund table: Shows QTD/YTD for Fund B across ALL clients
  - Account table: Shows QTD/YTD for the actual intersection
- **After Fix**: All tables show identical QTD/YTD values calculated from the same intersection

### Root Cause Analysis
The issue stems from intentional design in the `get_filtered_data` function (`app.py`) that calculates QTD/YTD from different data subsets:

```python
# Different WHERE clauses for each table:
client_where_clause  # Excludes client_ids filter
fund_where_clause    # Excludes fund_names filter  
full_where_clause    # Includes all filters (used for accounts)
```

**Key Insight**: When you select specific items, you're looking at a specific pot of money. If the balance is the same across tables, the QTD/YTD percentages MUST be the same because they're calculated from that same balance.

### Solution Implemented
**1. Added Helper Function** (`app.py`):
```python
def generate_qtd_ytd_cte_sql(entity_type, group_by_field, where_clause):
    """Generate QTD/YTD CTE SQL fragment for consistent metric calculation"""
    # Returns standardized QTD/YTD Common Table Expressions
```

**2. Modified All Queries** to use `full_where_clause` for QTD/YTD calculations:
- **Client balances query**: QTD/YTD CTEs now use full intersection
- **Fund balances query**: QTD/YTD CTEs now use full intersection  
- **Account details query**: Updated for consistency with helper function

**3. Enhanced NULL Handling**:
- Changed CASE WHEN logic to return NULL (not 0) for new accounts/funds
- Frontend displays "N/A" for entities without historical data

**4. Added Debug Logging**:
```python
if client_ids or fund_names or account_ids:
    app.logger.debug(f"QTD/YTD calculation using full intersection: {full_where_clause}")
```

### Testing Results
**Test Scenario**: Capital Management + Prime Money Market selection

| Table | Balance | QTD % | YTD % | Result |
|-------|---------|-------|-------|---------|
| **Client Balances** | $14,749,395 | **+0.1%** | **+1.9%** | ✅ Aligned |
| **Fund Summary** | $14,749,395 | **+0.1%** | **+1.9%** | ✅ Aligned |
| **Account Details** | (Individual accounts) | Calculated from intersection | Calculated from intersection | ✅ Consistent |

### Technical Implementation
**Files Modified**:
- `/root/CET/app.py`: Lines 30-74 (helper function), 1720-1836 (updated queries)

**Key Changes**:
- `client_query_params`: Now uses `full_params` for QTD/YTD calculations
- `fund_query_params`: Now uses `full_params` for QTD/YTD calculations
- All QTD/YTD CTEs use standardized helper function with `full_where_clause`

### Impact Resolved
- ✅ **User Confusion**: All tables now show identical percentages for same data
- ✅ **Data Integrity**: Metrics perfectly align with displayed balance
- ✅ **Financial Accuracy**: Critical requirement met for financial dashboard consistency

### Verification
- **Multi-selection support**: ✅ Works with client + fund + account combinations
- **Balance consistency**: ✅ Same balance = same QTD/YTD across all tables
- **NULL handling**: ✅ New entities show "N/A" instead of misleading 0%
- **Performance**: ✅ No degradation observed

## ✅ RESOLVED: JavaScript Error with Client-Fund Endpoint Response Structure

**Status**: Fixed  
**Priority**: High  
**Discovered**: January 2025  
**Reporter**: User testing during QTD/YTD consistency fix implementation  
**Fixed**: January 2025  
**Fix Author**: Claude Code  

### Problem Description
When selecting CLIENT+FUND combination, JavaScript error occurred: "Cannot read properties of undefined (reading 'client_name')" preventing the dashboard from loading the filtered data properly.

### Reproduction Steps
1. Navigate to overview page
2. Click on any client (e.g., "Capital Management")
3. Click on any fund (e.g., "Prime Money Market")
4. **BUG**: JavaScript error in console, tables don't update properly

### Root Cause Analysis
The `/api/client/<id>/fund/<name>` endpoint was updated to return arrays (`client_balances`, `fund_balances`) instead of single objects (`client_balance`, `fund_balance`) for consistency with other endpoints. However, the frontend JavaScript was still expecting the old singular object structure.

### Solution Implemented
**Frontend Changes (app.js:1628-1637)**:
```javascript
// Before - expecting singular objects:
updateClientTable([{ 
    client_name: data.client_balance.client_name, 
    client_id: data.client_balance.client_id, 
    total_balance: data.client_balance.total_balance,
    qtd_change: data.fund_balance.qtd_change,
    ytd_change: data.fund_balance.ytd_change
}]);

// After - handling arrays:
if (data.client_balances && data.client_balances.length > 0) {
    updateClientTable(data.client_balances);
}
if (data.fund_balances && data.fund_balances.length > 0) {
    updateFundTable(data.fund_balances);
}
```

Also removed redundant fund table update that was fetching from `/api/client/<id>` endpoint.

### Testing Results
- ✅ CLIENT+FUND selection now works without JavaScript errors
- ✅ All tables update correctly with filtered data
- ✅ QTD/YTD values remain consistent across all tables
- ✅ Example: Capital Management + Corporate Bond Fund shows QTD: +0.2%, YTD: +2.0% in all tables

### Impact Resolved
- ✅ **JavaScript Errors**: No more console errors when selecting CLIENT+FUND
- ✅ **Data Display**: Tables properly show intersection data
- ✅ **User Experience**: Smooth navigation between different selection combinations

## 🔍 ACTIVE: Fund Summary Occasionally Shows N/A for QTD/YTD

**Status**: Active - Root cause identified, fix pending  
**Priority**: Medium  
**Discovered**: January 2025  
**Reporter**: User observation  

### Problem Description
The Fund Summary table occasionally displays "N/A" for QTD/YTD values instead of actual percentages, while other tables show values correctly.

### Root Cause Analysis
Two potential causes identified:

1. **Empty Result Sets**: 
   - If a fund has no balance history in QTD/YTD start periods, subqueries return empty results
   - Fund gets excluded from result set entirely rather than showing with 0%
   - Frontend may display cached fund list with N/A for missing data

2. **SQL Edge Cases**:
   - Despite CASE WHEN logic handling NULL/0 cases, SQLite might return NULL in certain scenarios
   - Division operations or JOIN mismatches could produce unexpected NULLs

### Technical Context
```javascript
// Frontend formatPercentage function (app.js)
function formatPercentage(value) {
    if (value === null || value === undefined) return '<span class="neutral">N/A</span>';
    // ... rest of formatting logic
}
```

The backend should always return 0 (not NULL) due to CASE WHEN logic, suggesting either:
- Funds without current balances are excluded from results
- Edge case in SQL calculation returning NULL despite defensive coding

### Solution Required
1. Add COALESCE to all QTD/YTD calculations for extra NULL protection
2. Ensure funds without current balances are included with 0% values
3. Verify frontend receives complete fund list with all QTD/YTD values

## ✅ RESOLVED: Text Filters Lost When Making Table Selections

**Status**: Fixed  
**Priority**: High  
**Discovered**: January 2025  
**Reporter**: User testing after KPI fix implementation  
**Fixed**: January 2025  
**Fix Author**: Claude Code + Gemini AI collaboration  

### Problem Description
Text filters are completely lost/ignored when users make table selections (clicking on fund, client, or account rows). This breaks the expected behavior where text filters should be preserved across all interactions.

### Reproduction Steps
1. Apply text filter (e.g., Client Name: "Acme Corp")
2. Verify filter works correctly (shows only Acme Corporation, $9.89M AUM)
3. Click on any fund in the Fund Summary table (e.g., "Municipal Money Market")
4. **BUG**: Text filter is lost, showing all clients instead of filtered results

### Expected vs Actual Behavior
- **Expected**: Acme Corp + Municipal Money Market intersection (~$5.7M)
- **Actual**: ALL clients with Municipal Money Market fund ($54.98M)
- **Text Filter State**: Input field still shows "Acme Corp" but filter not applied

### Evidence from Testing
```
Before fund selection:
- Filter: "Client: Acme Corp"  
- Total AUM: $9,890,014 (correct)
- Active Clients: 1 (correct)
- Client table: Shows only Acme Corporation

After fund selection:
- Filter: "1 Fund | Client: Acme Corp" (misleading!)
- Total AUM: $54,978,536 (wrong - shows all clients)
- Active Clients: 10 (wrong - should be 1)
- Client table: Shows ALL clients, not just Acme Corp
```

### Root Cause Analysis
The issue is in the interaction between text filters and table selections:
1. Text filters work correctly when applied via "Apply Filters" button
2. Table selections (fund/client/account clicks) are not preserving active text filters
3. The `buildQueryString()` function or selection handling logic is clearing text filters during transitions

### Technical Context
- Bug introduced after recent KPI fix implementation (January 2025)
- Related files: `static/js/app.js` (selection handling, buildQueryString function)
- Backend: `app.py` (/api/data endpoint may need to handle text filter preservation)

### Impact
- **Functionality**: Core filtering feature broken for combined text + table selections
- **User Experience**: Confusing behavior - users lose their filters unexpectedly
- **Data Integrity**: Users see wrong data when they think filters are still active

### Additional Testing Evidence
Tested all three text filters individually - they work when used alone:
- ✅ Fund Ticker: "Prime" → correctly filters to Prime Money Market only
- ✅ Client Name: "Capital" → correctly filters to Capital Management only  
- ✅ Account Number: "CAP-006" → correctly filters to CAP-006-xxx accounts only
- ✅ Combined text filters: "Prime" + "Capital" → correctly shows intersection
- ❌ Text filter + table selection: **BROKEN** - text filter lost

### Solution Implemented
The bug was fixed by adding comprehensive text filter support to individual API endpoints that were previously ignoring query parameters:

**Backend Changes (`app.py`):**
1. **Updated `/api/client/<client_id>` endpoint**:
   - Added `get_text_filters()` call to extract query parameters
   - Applied `build_filter_clause()` to all queries (history, fund balances, account details)
   - Implemented conditional JOINs for performance (only join funds table when needed)
   - Excluded redundant client_name filter since client_id already filters

2. **Updated `/api/fund/<fund_name>` endpoint**:
   - Added text filter processing for client_name and account_number filters
   - Applied filters to all queries: 90-day history, 3-year history, client balances, account details
   - Used conditional client_mapping JOINs when client_name or account_number filters are present
   - Excluded redundant fund_ticker filter since fund_name already filters

**Key Implementation Details:**
- **Smart filter exclusion**: Each endpoint excludes filters that are redundant with the URL parameter
- **Conditional JOINs**: Only add table JOINs when required by active filters (performance optimization)
- **Comprehensive coverage**: All SQL queries updated (history, balances, QTD/YTD calculations)
- **Parameter binding**: Proper parameter handling with tuple concatenation for complex queries
- **Debug logging**: Added logging when filters are active for troubleshooting

**Testing Results:**
- ✅ **Original scenario fixed**: "Acme Corp" + Municipal Money Market now shows $5.75M (intersection) instead of $54.98M (all clients)
- ✅ **Filter persistence**: Text filters remain active and visible after table selections
- ✅ **Multi-selection support**: Works with fund + account selections while preserving text filters
- ✅ **KPI accuracy**: KPI calculations reflect filtered data correctly

### Files Modified
- `/root/CET/app.py`: 
  - Lines 527-733: Updated `/api/client/<client_id>` endpoint with full text filter support
  - Lines 735-924: Updated `/api/fund/<fund_name>` endpoint with full text filter support
  - Both endpoints now include conditional JOINs and comprehensive filter application

### Resolution Verification
- **Reproduction test passed**: Acme Corp + fund selection now works correctly
- **All KPIs accurate**: Total AUM, client count, fund count all reflect filtered data
- **Filter indicator correct**: Shows combined selections and text filters properly
- **No regressions**: All existing functionality remains intact

## ✅ RESOLVED: Account QTD/YTD Values Showing as N/A in Client-Fund View

**Status**: Fixed  
**Priority**: Medium  
**Discovered**: January 2025  
**Reporter**: User testing  

### Problem Description
QTD and YTD percentage values display as "N/A" for accounts when viewing a specific client-fund combination. The values display correctly in other views (overview, single client, single fund).

### Reproduction Steps
1. Navigate to overview page (http://localhost:9095)
2. Click on any client in the Client Balances table (e.g., "Capital Management")
3. Click on any fund in the Fund Summary table (e.g., "Prime Money Market")
4. **BUG**: Account Details table shows "N/A" for all QTD % and YTD % values

### Expected vs Actual Behavior
- **Expected**: Account details should show calculated QTD/YTD percentages (e.g., +0.1%, +1.5%)
- **Actual**: All accounts show "N/A" for both QTD % and YTD % columns
- **Other fields**: Account ID and Total Balance display correctly

### Evidence from Testing
```
API Response for /api/client/811e66af-0899-4b4f-b061-2057527514f7/fund/Prime%20Money%20Market:
{
  "account_details": [
    {
      "account_id": "CAP-006-000",
      "balance": 5346194.99,
      "client_name": "Capital Management",
      "fund_name": "Prime Money Market"
      // Missing: qtd_change, ytd_change
    },
    {
      "account_id": "CAP-006-001",
      "balance": 4609074.25,
      "client_name": "Capital Management", 
      "fund_name": "Prime Money Market"
      // Missing: qtd_change, ytd_change
    }
  ]
}
```

### Root Cause Analysis
The issue is in `/api/client/<client_id>/fund/<fund_name>` endpoint (app.py:1207-1211):

```python
'account_details': [{'account_id': acc['account_id'], 
                   'client_name': client_name,
                   'fund_name': fund_name,
                   'balance': acc['balance']} for acc in account_details]
```

The SQL query calculates `qtd_change` and `ytd_change` (lines 1172-1179), but these fields are not included when building the response.

### Technical Context
- **Frontend handling**: `formatPercentage()` function correctly displays "N/A" for null/undefined values
- **SQL query**: Properly calculates QTD/YTD values with CTEs and LEFT JOINs
- **API response**: Missing fields in the list comprehension
- **Other endpoints**: Work correctly (e.g., `/api/overview`, `/api/client/<id>`, `/api/date/<date>`)

### Impact
- **Functionality**: Users cannot see QTD/YTD performance for individual accounts in client-fund view
- **User Experience**: Inconsistent display - values show in other views but not this one
- **Data Completeness**: The data is calculated but not returned to frontend

### Fix Required
Update the account_details list comprehension to include all calculated fields:

```python
'account_details': [{'account_id': acc['account_id'], 
                   'client_name': client_name,
                   'fund_name': fund_name,
                   'balance': acc['balance'],
                   'qtd_change': acc['qtd_change'],
                   'ytd_change': acc['ytd_change']} for acc in account_details]
```

### Resolution Details
**Fixed**: January 2025  
**Fix Author**: Claude Code collaboration  

**Solution Implemented**: Updated the `account_details` list comprehension in the `/api/client/<client_id>/fund/<fund_name>` endpoint to include the calculated `qtd_change` and `ytd_change` fields.

**Code Change** (app.py:1207-1212):
```python
# Before (missing QTD/YTD fields):
'account_details': [{'account_id': acc['account_id'], 
                   'client_name': client_name,
                   'fund_name': fund_name,
                   'balance': acc['balance']} for acc in account_details]

# After (includes QTD/YTD fields):
'account_details': [{'account_id': acc['account_id'],
                   'client_name': client_name,
                   'fund_name': fund_name,
                   'balance': acc['balance'],
                   'qtd_change': acc.get('qtd_change'),
                   'ytd_change': acc.get('ytd_change')} for acc in account_details]
```

**Testing Verification**:
- API now returns QTD/YTD values (e.g., 0.24%, 2.10%)  
- Frontend displays formatted percentages (+0.2%, +2.1%) instead of "N/A"
- Tested Capital Management + Prime Money Market scenario successfully
- No regressions in other views (overview, single client, single fund)

### Additional Notes
- Used `.get()` method for safe field access to prevent KeyError
- SQL query was already calculating the values correctly using CTEs
- Frontend `formatPercentage()` function handles the values properly
- Fix maintains consistency with other similar endpoints