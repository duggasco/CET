# BUGS.md - Known Issues and Bug Reports

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

## 🔍 ACTIVE: Account QTD/YTD Values Showing as N/A in Client-Fund View

**Status**: Active (Not Fixed)  
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

### Additional Notes
- The SQL query correctly calculates the QTD/YTD values using CTEs
- Other similar endpoints (`/api/overview`, `/api/client/<id>`, `/api/date/<date>`) include these fields correctly
- This appears to be an oversight in the response construction for this specific endpoint