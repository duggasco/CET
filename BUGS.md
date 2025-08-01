# BUGS.md - Known Issues and Bug Reports

## ✅ RESOLVED: Docker v2 Deployment Issues

**Status**: RESOLVED - Fixed on 2025-08-01  
**Priority**: High  
**Discovered**: August 2025  
**Reporter**: User during Docker testing  
**Fixed**: August 2025  
**Fix Author**: Claude Code  

### Issue Description
When running with Docker and v2 feature flags enabled, two critical issues occurred:
1. Charts displayed "Invalid Date" at the bottom axis labels
2. KPIs reverted to full AUM ($248M) when selecting multiple clients instead of showing filtered total

### Root Causes
1. Missing `useV2DashboardApi` flag in Docker environment variables - only `useV2Tables` and `useV2Charts` were set
2. TypeError when calling `.toFixed()` on undefined values in KPI calculations
3. apiWrapper not using v2 API despite feature flags being set

### Resolution
1. **Updated run.sh** to include all v2 feature flags:
   ```bash
   -e 'FEATURE_FLAGS={"useV2Tables":true,"useV2Charts":true,"useV2DashboardApi":true}'
   ```
2. **Added safety checks** in updateKPICards function (app.js:415, 422):
   - Check for undefined/null/NaN before calling `.toFixed()`
   - Default to '0.0' if value is invalid
3. **Fixed v2Api.transformToV1Format** to properly extract chart data from nested `v2Data.charts` structure

### Testing Results
- Charts now display dates correctly with v2 API
- KPIs show correct filtered values for multi-selections
- No more TypeError in console
- All v2 features working properly in Docker deployment

## ✅ RESOLVED: KPI/Chart Values Revert to Full AUM During Multi-Selection

**Status**: RESOLVED - Fixed on 2025-08-01
**Priority**: High
**Discovered**: August 2025
**Reporter**: User observation after multi-selection bug fix
**Fixed**: August 2025
**Fix Author**: Claude Code with solution design from Gemini AI collaboration

### Problem Description
When making multiple selections with v2 tables enabled, KPI cards and charts briefly show the correct filtered values before reverting to the full AUM (unfiltered) values. The tables continue to show filtered data correctly, but KPIs and charts revert.

### Reproduction Steps
1. Navigate to overview page with v2 tables enabled
2. Select 2 or more clients in the Client Balances table
3. Observe the Total AUM in KPI cards
4. **BUG**: KPI briefly shows filtered total (e.g., $75M for 2 clients) then reverts to full AUM ($530M+)

### Expected vs Actual Behavior
- **Expected**: KPIs and charts remain showing filtered totals after multi-selection
- **Actual**: 
  - KPIs show correct filtered value for ~0.5-1 second
  - Then revert to showing full unfiltered AUM
  - Tables continue showing filtered data correctly

### Root Cause Analysis
The issue is caused by **double API calls** when v2 tables are enabled:

1. **First API Call** (from `loadFilteredData()`):
   ```javascript
   // Fetches filtered data correctly
   const data = await fetch('/api/v2/dashboard?client_ids=...');
   updateKPICards(data); // Shows correct filtered values
   tableManager.updateClientTable(data.client_balances); // Triggers second call!
   ```

2. **Second API Call** (from `tableManager.updateClientTable()`):
   ```javascript
   // When v2 tables enabled, ignores passed data and fetches again
   if (window.featureFlags?.useV2Tables) {
       const params = getCurrentSelectionParams();
       return await tablesV2.updateTables(params); // Makes another API call!
   }
   ```

### Technical Details
- The v2 table implementation (`tables-v2.js`) always fetches its own data
- `tableManager` methods ignore the data passed to them when v2 tables are enabled
- This creates a race condition where two API responses compete to update the UI
- The second response likely triggers a KPI update with different (unfiltered) data

### Evidence
- KPIs show correct values "for a moment" indicating they're updated twice
- Console logs would show two `/api/v2/dashboard` requests in quick succession
- Tables remain correct because they're updated by the second (v2 tables) call

### Impact
- **User Confusion**: KPIs don't match the visible filtered data in tables
- **Data Integrity**: Misleading totals shown in KPIs and charts
- **Trust**: Users may doubt the accuracy of the application

### Solution Design (Agreed with Gemini AI)

After thorough analysis and collaboration, we've agreed on the following solution:

**Chosen Approach**: Directly call `tablesV2.updateTables()` with pre-fetched data, bypassing the tableManager abstraction layer (since v1 is being deprecated).

### Implementation (Completed)

1. **Modified `tables-v2.js` `updateTables()` method** ✅:
   ```javascript
   async updateTables(dataOrParams) {
       let data;
       
       // Check if we received data directly
       if (dataOrParams && (dataOrParams.client_balances !== undefined || 
                            dataOrParams.fund_balances !== undefined || 
                            dataOrParams.account_details !== undefined)) {
           console.log('[Tables V2] Using provided data');
           data = dataOrParams;
       } else {
           // Fetch data using params (preserve existing logic)
           console.log('[Tables V2] Fetching data with params:', dataOrParams);
           const params = dataOrParams || {};
           // ... existing fetch logic ...
           data = await apiWrapper.loadData(apiParams);
       }
       
       // Only update tables that have data
       if (data.client_balances !== undefined) {
           this.updateClientTable(data.client_balances);
       }
       if (data.fund_balances !== undefined) {
           this.updateFundTable(data.fund_balances);
       }
       if (data.account_details !== undefined) {
           this.updateAccountTable(data.account_details);
       }
       
       return data;
   }
   ```

2. **Updated all `loadXData()` functions in `app.js`** ✅:
   - Replaced all `tableManager.updateXTable()` calls with direct `await tablesV2.updateTables(data)` calls
   - Maintained `restoreSelectionVisuals()` and `updateDownloadButton()` calls after table updates
   - Updated functions: `loadOverviewData()`, `loadFilteredData()`, `loadClientData()`, `loadFundData()`, `loadAccountData()`, `loadAccountDataForFund()`, and `loadClientFundData()`

### Key Design Decisions
- **No backward compatibility needed**: v1 endpoints are being deprecated
- **Always update all tables**: Simpler and more consistent than partial updates
- **Separation of concerns**: tables-v2 handles only table updates, not selection visuals or download button
- **Direct calls**: Bypass tableManager abstraction since it's no longer needed

### Testing Results
- ✅ **API Behavior Test**: Tableau-like behavior working, KPIs show correct filtered totals
- ✅ **Comprehensive Function Tests**: All loadXData functions tested and working
- ✅ **Double API Call Test**: No double API calls detected
- ✅ **No Regressions**: All existing functionality preserved

### Resolution Summary
- **Double API calls eliminated**: The fix prevents tableManager from making redundant API calls
- **KPIs remain stable**: Values no longer revert to full AUM after multi-selection
- **Performance improved**: Single API call instead of two for each update
- **Architecture simplified**: Direct calls to tablesV2 reduce complexity

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

## ✅ RESOLVED: Table Multi-Selection Limiting Bug

**Status**: RESOLVED - Fixed on 2025-08-01  
**Priority**: High  
**Discovered**: January 2025  
**Reporter**: User observation  
**Solution Designers**: Claude Code + Gemini AI collaboration  

### Problem Description
When users select 2 or more items in any table (clients, funds, or accounts), all other unselected items in that table disappear. This breaks the expected Tableau-like multi-selection behavior where selected items should remain highlighted while all items stay visible.

### Reproduction Steps
1. Navigate to overview page
2. Click on 2 clients in the Client Balances table
3. **BUG**: Only the 2 selected clients remain visible; all other clients disappear
4. Same behavior occurs with Fund Summary and Account Details tables

### Expected vs Actual Behavior
- **Expected (Tableau-like)**:
  - Source table: Shows ALL items with selected ones highlighted
  - Other tables: Show filtered data based on selections
- **Actual**:
  - Source table: Shows ONLY selected items
  - Other tables: Show filtered data (correct)

### Root Cause Analysis
The issue is in the frontend logic in `app.js`:

1. **Single Selection Path**: Calls endpoint like `/api/client/<id>` which returns full client list
2. **Multi-Selection Path**: Calls `/api/data` endpoint with filters, which returns only filtered data
3. **Table Rendering**: Tables faithfully render whatever data they receive

The v2 API implementation (`services/dashboard_service.py`) already uses consistent filtering - there's no `exclude_filters` logic. The bug is purely in how the frontend handles the response data.

### Technical Context
```javascript
// In updateDataBasedOnSelections (app.js)
if (hasClientSelection && !hasFundSelection && !hasAccountSelection) {
    // Single selection - loads full client data
    loadClientData(firstClientId, firstClientName);
} else if (hasClientSelection || hasFundSelection || hasAccountSelection) {
    // Multi-selection - loads filtered data only
    loadFilteredData();
}
```

### Solution Design
Add a `selection_source` parameter to identify which table is the source of selections:

**Backend Changes**:
1. Add `selection_source` parameter to `/api/v2/dashboard` endpoint
2. Modify `_build_full_where_clause` to exclude filters for the source table
3. Update table methods to use modified where clause based on selection_source

**Frontend Changes**:
```javascript
// Determine selection source (only for single-table selections)
let selectionSource = null;
const selectionCounts = [
    selectionState.clients.size > 0 ? 1 : 0,
    selectionState.funds.size > 0 ? 1 : 0,
    selectionState.accounts.size > 0 ? 1 : 0
].reduce((a, b) => a + b, 0);

if (selectionCounts === 1) {
    if (selectionState.clients.size > 0) selectionSource = 'client';
    else if (selectionState.funds.size > 0) selectionSource = 'fund';
    else if (selectionState.accounts.size > 0) selectionSource = 'account';
}
```

### Implementation Plan
1. **app.py**: Add selection_source parameter extraction and pass to service
2. **dashboard_service.py**: 
   - Add selection_source parameter to get_dashboard_data
   - Update _build_full_where_clause to accept exclude_source parameter
   - Modify table methods to conditionally exclude filters
3. **app.js**: Update loadFilteredData to determine and send selection_source

### Key Benefits
- Implements proper Tableau-like behavior
- Minimal code changes required
- Single API call (efficient)
- Maintains backward compatibility
- Clear, simple logic

### Resolution Summary

**Root Cause**: The frontend was still using the v1 API endpoint (`/api/data`) for multi-selection scenarios instead of the v2 endpoint (`/api/v2/dashboard`) that supports the `selection_source` parameter.

**Key Fix**: Updated `loadFilteredData()` in app.js to use the v2 API endpoint and handle the different response format.

**Implementation Details**:
1. ✅ Backend v2 API correctly implemented with selection_source support
2. ✅ Frontend updated to calculate and send selection_source parameter
3. ✅ Critical fix: `loadFilteredData()` now uses `/api/v2/dashboard` instead of `/api/data`
4. ✅ Added compatibility handling for v2 API response format (nested charts structure)

**Testing Results**:
- ✅ Single client selection: Shows all clients with selected one highlighted
- ✅ Multi-client selection: Shows ALL clients (not just selected ones)
- ✅ Fund and account tables filter correctly based on selections
- ✅ KPI metrics update appropriately
- ✅ Charts continue to work with filtered data
- ✅ Selection persistence maintained across data updates

**Files Modified**:
- `/root/CET/app.py`: Added selection_source parameter to v2 endpoint
- `/root/CET/services/dashboard_service.py`: Implemented conditional filter exclusion
- `/root/CET/static/js/app.js`: Updated to use v2 API and send selection_source
- `/root/CET/static/js/api-wrapper.js`: Pass selection_source through to v2Api
- `/root/CET/static/js/v2-api.js`: Include selection_source in query params

### Verification
The fix was verified through:
1. API testing showing correct behavior with selection_source parameter
2. Browser testing confirming Tableau-like behavior works as expected
3. Console logs showing v2 API being called with proper parameters
4. Visual confirmation that all items remain visible with selections highlighted

## ✅ RESOLVED: Balance Tables Not Sorted by Total Balance

**Status**: RESOLVED - Fixed on 2025-08-01  
**Priority**: High  
**Discovered**: August 2025  
**Reporter**: User requirement  
**Fixed**: August 2025  
**Fix Author**: Claude Code  

### Problem Description
All balance tables (Client Balances, Fund Summary, Account Details) were displaying data in alphabetical order by name/ID instead of being sorted by total balance from largest to smallest. This made it difficult for users to quickly identify the largest clients, funds, or accounts.

### Reproduction Steps
1. Navigate to overview page
2. Observe the Client Balances table
3. **BUG**: Clients are sorted alphabetically (e.g., "Acme Corporation" first)
4. Same issue with Fund Summary (sorted by fund name) and Account Details (sorted by account ID)

### Expected vs Actual Behavior
- **Expected**: All tables sorted by total balance descending (largest first)
- **Actual**: 
  - Client Balances: Sorted by client_name alphabetically
  - Fund Summary: Sorted by fund_name alphabetically  
  - Account Details: Sorted by account_id alphabetically

### Root Cause Analysis
The issue was found in two places:

1. **DashboardService** (`services/dashboard_service.py`):
   - Line 206: `ORDER BY cb.client_name` 
   - Line 279: `ORDER BY cb.fund_name`
   - Line 350: `ORDER BY cb.account_id`
   - Paginated methods also had similar sorting issues

2. **CacheRepository** (`repositories/cache_repository.py`):
   - Line 29: `ORDER BY client_name`
   - Line 39: `ORDER BY fund_name`
   - Line 49: `ORDER BY account_id`

The v2 API endpoint (`/api/v2/dashboard`) uses DashboardService, which retrieves data either from cache (when no filters/pagination) or generates it fresh. Both paths had incorrect sorting.

### Solution Implemented

**1. Updated DashboardService sorting** (`services/dashboard_service.py`):
```python
# Client balances query
- ORDER BY cb.client_name
+ ORDER BY cb.total_balance DESC

# Fund balances query  
- ORDER BY cb.fund_name
+ ORDER BY cb.total_balance DESC

# Account details query
- ORDER BY cb.account_id  
+ ORDER BY cb.balance DESC

# Also updated paginated queries to maintain consistent sorting
- ORDER BY cb.client_name, cb.client_id
+ ORDER BY cb.total_balance DESC, cb.client_id
```

**2. Updated CacheRepository sorting** (`repositories/cache_repository.py`):
```python
# get_cached_client_balances
- ORDER BY client_name
+ ORDER BY total_balance DESC

# get_cached_fund_balances
- ORDER BY fund_name  
+ ORDER BY total_balance DESC

# get_cached_account_details
- ORDER BY account_id
+ ORDER BY balance DESC
```

### Technical Details
- The v2 API implementation already had correct sorting in the deprecated `/api/data` endpoint
- The issue only affected the new v2 dashboard endpoint which uses DashboardService
- Cache warming process (`warm_cache.py`) populates cache tables that are then queried by CacheRepository
- Both cached and fresh data paths needed to be fixed for consistent behavior

### Testing Results
**Before Fix**:
```
First 5 clients:
1. Acme Corporation: $25,544,801.04
2. Capital Management: $18,630,245.92  
3. Financial Solutions Ltd: $14,665,660.10
4. Global Trade Inc: $30,748,183.53
5. Growth Ventures Inc: $28,212,876.04
```

**After Fix**:
```
First 5 clients:
1. Tech Innovations LLC: $26,798,165.40
2. Investment Partners Corp: $26,354,773.18
3. Acme Corporation: $25,702,436.46
4. Global Trade Inc: $23,787,647.72
5. Growth Ventures Inc: $21,306,361.60
```

### Impact Resolved
- ✅ **User Experience**: Tables now show largest balances first for easy identification
- ✅ **Consistency**: Sorting behavior consistent across all views and filters
- ✅ **Performance**: No performance impact as sorting is done at SQL level
- ✅ **Cache Behavior**: Both cached and fresh data properly sorted

### Verification
- Tested overview page: All three tables sorted by balance descending
- Tested with single client selection: Fund and account tables sorted correctly
- Tested with fund selection: Client and account tables sorted correctly  
- Tested with multiple selections: All tables maintain proper sorting
- Tested with text filters: Sorting preserved with filtered results
- Docker deployment tested and verified working

## ✅ RESOLVED: V2 Multi-Selection Table Persistence Bug

**Status**: Fixed  
**Priority**: High  
**Discovered**: 2025-08-01  
**Reporter**: User observation during Docker testing  
**Analysis**: Claude Code + Gemini AI collaborative investigation
**Fixed**: 2025-08-01  
**Fix Author**: Claude Code (implementation based on Claude + Gemini consensus)

### Problem Description
When using v2 charts with multi-table selections (e.g., selecting items from both client and fund tables), the source tables incorrectly show only the filtered intersection instead of maintaining Tableau-like behavior where all items are shown with selections highlighted.

### Reproduction Steps
1. Navigate to overview page with v2 features enabled
2. Select 2 clients (e.g., "Capital Management" and "Growth Ventures Inc")
3. **WORKS**: Client table shows ALL 10 clients with 2 highlighted ✓
4. Now also select a fund (e.g., "Prime Money Market")
5. **BUG**: Client table now shows ONLY the 2 clients that have that fund (intersection)
6. **BUG**: Fund table shows ONLY the 1 selected fund instead of all 6 funds

### Expected vs Actual Behavior
- **Expected** (Tableau-like behavior):
  - When selections exist in a table: That table shows ALL items with selections highlighted
  - Other tables show filtered intersection data
  - Example: 2 clients + 1 fund selected → Client table shows all 10 clients (2 highlighted), Fund table shows all 6 funds (1 highlighted), Account table shows only intersection
- **Actual**:
  - All tables show filtered intersection when multi-table selections are made
  - Single-table selections work correctly, multi-table selections do not

### Root Cause Analysis
**Primary Issue**: `loadFilteredData()` function only sets `selection_source` for single-table selections:

```javascript
// Current buggy logic
const selectionCount = (hasClients ? 1 : 0) + (hasFunds ? 1 : 0) + (hasAccounts ? 1 : 0);
if (selectionCount === 1) {
    // Only sets selection_source for single table
    if (hasClients) selectionSource = 'client';
    else if (hasFunds) selectionSource = 'fund';
    else if (hasAccounts) selectionSource = 'account';
}
// For multi-table selections, selectionSource remains null
```

**Working Pattern**: `loadClientData()` correctly implements the pattern:
1. Fetches filtered intersection data
2. Makes separate call with `selection_source=client` to get ALL clients
3. Combines results appropriately

**Backend**: The backend correctly handles `selection_source` by excluding filters for the source table via `_build_full_where_clause(filters, exclude_source='client')`. No backend changes needed.

### Technical Context
Console logs showing the issue:
```
// Multi-selection: 2 clients + 1 fund
[API Request] GET /api/v2/dashboard?client_id=xxx&client_id=yyy&fund_name=Prime%20Money%20Market
// Missing the additional calls with selection_source for each table
```

### Impact
- **User Experience**: Confusing behavior where tables don't maintain Tableau-like selection visibility
- **Data Integrity**: Tables show inconsistent states during multi-selections
- **Feature Parity**: Multi-selections don't work like single selections

### Agreed Solution (Claude + Gemini Consensus)
Modify `loadFilteredData()` to handle multi-table selections by making parallel API calls:

```javascript
async function loadFilteredData() {
    // 1. Get filtered intersection data (for charts, KPIs, non-selected tables)
    const response = await fetch(`/api/v2/dashboard${queryString}`);
    const data = await response.json();
    
    // 2. Parallel fetch all items for tables with selections
    const promises = [];
    if (selectionState.clients.size > 0) {
        promises.push(fetch(`/api/v2/dashboard?selection_source=client${queryString}`));
    }
    if (selectionState.funds.size > 0) {
        promises.push(fetch(`/api/v2/dashboard?selection_source=fund${queryString}`));
    }
    if (selectionState.accounts.size > 0) {
        promises.push(fetch(`/api/v2/dashboard?selection_source=account${queryString}`));
    }
    
    const results = await Promise.allSettled(promises);
    
    // 3. Combine results with error handling
    // Use "all items" data for tables with selections
    // Fall back to intersection data on error
}
```

### Key Implementation Details
- Use `Promise.allSettled()` for graceful error handling
- Correct URL construction to avoid `?selection_source=client?other_params` issue
- Fall back to intersection data if individual calls fail
- Update charts/KPIs with intersection data, tables with appropriate "all" data

### Solution Implemented
Successfully fixed by modifying `loadFilteredData()` in app.js:

1. **Added helper function** for proper URL parameter handling:
   ```javascript
   function appendSelectionSource(queryString, source) {
       const separator = queryString ? '&' : '?';
       return `${queryString}${separator}selection_source=${source}`;
   }
   ```

2. **Implemented parallel API calls** for multi-table selections:
   - First call gets intersection data for charts/KPIs
   - Additional calls get "all items" data for each table with selections
   - Uses `Promise.allSettled()` for robust error handling

3. **Smart data combination**:
   - Charts and KPIs use intersection data
   - Tables with selections use their "all items" data
   - Other tables use intersection data
   - Graceful fallback on API failures

### Testing Results
✅ **Multi-selection verified**: 2 clients + 1 fund correctly shows all 10 clients and all 6 funds
✅ **All combinations tested**: Every permutation of table selections works correctly
✅ **Tableau-like behavior restored**: Source tables maintain all items with selections highlighted
✅ **No regressions**: Single-table selections continue to work as before
✅ **Error handling tested**: Graceful fallback when individual API calls fail
✅ **Performance maintained**: Parallel calls execute efficiently

### Resolution Summary
The fix successfully restores Tableau-like multi-selection behavior. Source tables now properly show all items with selections highlighted while other tables show filtered intersection data. The implementation follows the agreed-upon solution from both Claude and Gemini's analysis.