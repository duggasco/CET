# Changelog

## [Latest] - V2 Charts Trend Lines Restored (2025-08-01)

### 🎨 Feature Restoration
- **Added min/max/average trend lines to v2 charts**: Restored the dashed trend lines from v1 implementation
- **Visual design matches v1**: Thin dashed lines for average (gray), maximum (blue), and minimum (red)
- **Smart tooltip filtering**: Tooltips only show main balance line, not trend lines

### 🔧 Technical Implementation
- **static/js/charts-v2.js Updates**:
  - Added three additional datasets to chart data for avg/max/min trend lines
  - Trend lines use `borderDash: [5, 5]` for dashed appearance
  - Very thin borders (0.5px) with no hover interaction (`pointRadius: 0`)
  - Colors: Gray (rgba(107,114,128,0.95)), Blue (rgba(59,130,246,0.95)), Red (rgba(239,68,68,0.95))
  - Order property ensures trend lines render behind main data
  - Updated tooltip filter to exclude trend line datasets
  - Fixed clearCharts() method to handle multiple datasets

### ✅ Result
- Both 90-day and 3-year charts now display horizontal dashed trend lines
- Statistics continue to show in chart headers (Max/Avg/Min values)
- Charts maintain all existing functionality (click to filter by date, etc.)
- Visual parity with v1 implementation achieved

## [Previous] - V2 Multi-Selection Table Persistence Bug Fixed (2025-08-01)

### 🐛 Critical Bug Fix
- **Fixed v2 multi-selection breaking Tableau-like behavior**: Tables now correctly show all items with selections highlighted
- **Root cause**: `loadFilteredData()` only set `selection_source` for single-table selections, causing all tables to show filtered data
- **Solution**: Implemented parallel API calls for multi-table selections to maintain proper source table behavior

### 🔧 Technical Implementation
- **static/js/app.js Updates**:
  - Added `appendSelectionSource()` helper function for proper URL parameter construction
  - Modified `loadFilteredData()` to make parallel API calls when multiple tables have selections
  - First call gets intersection data for charts/KPIs
  - Additional calls get "all items" data for each table with selections using `selection_source`
  - Uses `Promise.allSettled()` for robust error handling
  - Smart data combination: Tables with selections use their "all items" data, others use intersection

### ✅ Testing Results
- Multi-selection (2 clients + 1 fund) correctly shows all 10 clients and all 6 funds
- All permutations of table selections tested and working
- Tableau-like behavior fully restored
- No regressions in single-table selections
- Error handling verified with graceful fallback
- Performance maintained with parallel execution

### 📊 Example
- Select: Capital Management + Growth Ventures (clients) + Prime Money Market (fund)
- Result: Client table shows ALL 10 clients (2 highlighted), Fund table shows ALL 6 funds (1 highlighted)
- Account table shows only intersection (5 accounts)
- Total AUM shows $21.8M (intersection amount)

## [Previous] - V2 Charts Updated to Match V1 Functionality (2025-08-01)

### 🎨 Enhancement
- **V2 charts now have identical functionality to V1 charts**: All visual features, statistics, and interactions match exactly
- **Added chart statistics display**: Max/Avg/Min values now shown above both 90-day and 3-year charts
- **Fixed data field compatibility**: Charts handle both v1 (`total_balance`) and v2 (`balance`) response formats
- **Matched exact v1 styling**: Border width (2.5px), point hover effects, grid appearance, and animations

### 🔧 Technical Changes
- **static/js/charts-v2.js Updates**:
  - Added statistics calculation and display using `#recentChartStats` and `#longTermChartStats` elements
  - Updated `updateChart()` to support both data field formats (total_balance/balance, balance_date/date)
  - Applied v1 chart styling: borderWidth 2.5, pointRadius 0, hover effects with white border
  - Uses v1 date formatters (`formatDate()` and `formatDateLong()`) for consistent display
  - Improved chart click handling by storing original data for accurate date extraction
  - Added animation settings: 750ms duration with easeInOutQuart easing
  - Hide legend and configure grid to match v1 appearance

### ✅ Testing Results
- Chart statistics update correctly with all filter types
- Visual appearance identical between v1 and v2
- Chart click functionality works for date filtering
- Multi-selection updates charts with correct aggregated data
- Both API response formats handled seamlessly

### 📊 Example
- 90-day chart shows: "Max: $106.3M | Avg: $104.2M | Min: $102.1M"
- Charts display with same blue (#0085ff) and green (#00d647) color scheme
- Hover shows formatted balance tooltips
- Click functionality filters tables to selected date

## [Previous] - Balance Tables Sorted by Total Balance (2025-08-01)

### 🐛 Bug Fix
- **Fixed balance tables sorting alphabetically instead of by balance**: All tables now display data from largest to smallest total balance
- **Root cause**: Both DashboardService and CacheRepository were using alphabetical sorting (ORDER BY name/id)
- **Solution**: Updated all SQL queries to use ORDER BY total_balance DESC (or balance DESC for accounts)

### 🔧 Technical Changes
- **services/dashboard_service.py Updates**:
  - Changed client queries from `ORDER BY cb.client_name` to `ORDER BY cb.total_balance DESC`
  - Changed fund queries from `ORDER BY cb.fund_name` to `ORDER BY cb.total_balance DESC`
  - Changed account queries from `ORDER BY cb.account_id` to `ORDER BY cb.balance DESC`
  - Updated both regular and paginated query methods
  - Maintained secondary sort key for paginated queries (e.g., ORDER BY cb.total_balance DESC, cb.client_id)

- **repositories/cache_repository.py Updates**:
  - Updated `get_cached_client_balances()` to sort by total_balance DESC
  - Updated `get_cached_fund_balances()` to sort by total_balance DESC
  - Updated `get_cached_account_details()` to sort by balance DESC
  - Ensures cached data maintains same sort order as fresh queries

### ✅ Testing Results
- Overview page shows largest clients/funds/accounts first
- Sorting maintained across all filter combinations
- Multi-selection preserves sort order
- Text filters show filtered results sorted by balance
- Both cached and fresh data properly sorted
- Docker deployment verified with correct sorting

### 📊 Example
Before: Acme Corporation (alphabetically first) shown at top with $25.5M
After: Tech Innovations LLC (largest balance) shown at top with $26.8M

## [Previous] - Multi-Selection Tableau-like Behavior Restored (2025-08-01)

### 🐛 Bug Fix
- **Fixed multi-selection behavior broken by v2 API changes**: When selecting a single client, all clients now remain visible with the selected one highlighted
- **Root cause**: `loadClientData()` was using filtered data from v2 API which only returned the selected client
- **Solution**: Added additional API call to fetch all clients when using v2 API for single selection

### 🔧 Technical Changes
- **app.js loadClientData() Enhancement**:
  - Added call to `/api/v2/dashboard?selection_source=client` to get all clients
  - Preserves Tableau-like behavior where source table shows all items with selections highlighted
  - Maintains filtered data for funds and accounts tables
  - Only makes additional call when v2 API is enabled

### ✅ Testing Results
- Single client selection shows all 10 clients with selected one highlighted
- Fund and account tables properly show filtered data for selected client
- Multi-selection behavior works correctly
- Performance remains good with minimal overhead from additional API call

## [Previous] - Charts Fixed for All Selection States (2025-08-01)

### 🐛 Bug Fix
- **Fixed charts showing blank in overview and single-client states**: Charts now display properly in all selection states, not just multi-client
- **Root cause**: `loadOverviewData()` and `loadClientData()` were using v1 API endpoints directly instead of checking for v2 flag
- **Solution**: Updated both functions to use v2 API when `useV2DashboardApi` flag is set

### 🔧 Technical Changes
- **app.js Updates**:
  - Modified `loadOverviewData()` to check for v2 flag and use `/api/v2/dashboard` when enabled
  - Modified `loadClientData()` to check for v2 flag and use v2 API with client filter
  - Both functions now properly extract chart data from `data.charts` structure when using v2
  - Added fallback to v1 API if v2 request fails
  - Consistent chart data handling across all selection states

### ✅ Testing Results
- Charts display correctly in overview (all clients/funds)
- Charts display correctly for single client selection
- Charts display correctly for multi-client selection
- All chart interactions (click to filter by date) working properly

## [Previous] - Docker v2 Deployment Issues Fixed (2025-08-01)

### 🐛 Bug Fixes
- **Fixed "Invalid Date" in charts**: Charts now properly display dates when v2 features are enabled in Docker
- **Fixed KPI reversion on multi-selection**: KPIs now correctly show filtered totals instead of reverting to full AUM
- **Fixed TypeError in KPI calculations**: Added safety checks for undefined values in `.toFixed()` calls

### 🔧 Technical Changes
- **run.sh Enhancement**:
  - Added missing `useV2DashboardApi` flag to Docker environment
  - Full flag set: `{"useV2Tables":true,"useV2Charts":true,"useV2DashboardApi":true}`
  - Ensures all v2 features work properly in Docker deployments

- **app.js Safety Improvements**:
  - Added null/undefined/NaN checks before `.toFixed()` calls (lines 415, 422)
  - Prevents TypeError when KPI data is missing or malformed
  - Defaults to '0.0' for invalid values

- **v2-api.js Chart Data Fix**:
  - Already fixed `transformToV1Format` to extract chart data from `v2Data.charts`
  - Ensures chart data is properly passed to chart components

### ✅ Testing Results
- Docker deployment now works correctly with all v2 features enabled
- Charts display proper date labels instead of "Invalid Date"
- KPIs show correct filtered values for multi-selections
- No console errors when selecting multiple clients
- Performance maintained with v2 API optimizations

## [Latest] - Docker Deployment Updated with V2 Tables Enabled (2025-08-01)

### 🚀 Deployment Update
- **Modified run.sh**: Added FEATURE_FLAGS environment variable to enable v2 tables and charts by default in Docker deployments
- **Rationale**: The KPI/Chart reversion bug fix is implemented in v2 tables, but Docker was running with v1 by default
- **Change**: Added `-e 'FEATURE_FLAGS={"useV2Tables":true,"useV2Charts":true}'` to docker run command
- **Impact**: All Docker deployments now benefit from the double API call fix and improved performance

## KPI/Chart Reversion Bug Fix: Double API Calls Eliminated (2025-08-01)

### 🐛 Bug Fix
- **Fixed critical issue**: KPIs and charts no longer revert to full AUM after showing correct filtered values
- **Root cause**: Double API calls occurring when v2 tables enabled - tableManager making redundant API calls
- **Solution**: Modified tables-v2.js to accept pre-fetched data and bypass tableManager abstraction

### 🔧 Technical Changes
- **tables-v2.js Enhancement**:
  - Modified `updateTables()` to accept either data object or params
  - Checks for data properties (client_balances, fund_balances, account_details)
  - Uses provided data directly without making API calls
  - Maintains backward compatibility with param-based calls
  - Only updates tables that have data (prevents clearing with undefined)

- **app.js Refactoring**:
  - Replaced all `tableManager.updateXTable()` calls with direct `await tablesV2.updateTables(data)`
  - Updated functions: loadOverviewData, loadFilteredData, loadClientData, loadFundData, loadAccountData, loadAccountDataForFund, loadClientFundData
  - Maintained restoreSelectionVisuals() and updateDownloadButton() calls
  - Eliminated dependency on tableManager for v2 tables (since v1 is deprecated)

### ✅ Testing Results
- API Behavior Test: Shows correct filtered KPI values without reversion
- Comprehensive Function Tests: All loadXData functions working correctly
- Double API Call Test: No double calls detected - single API request per action
- Performance: Improved due to elimination of redundant API calls
- No regressions: All existing functionality preserved

### 📚 Key Design Decisions
- Direct calls to tablesV2 since v1 endpoints are deprecated
- No backward compatibility needed as v1 is being phased out
- Always update all tables for consistency
- Separation of concerns: tables-v2 handles only table updates

### 📝 Documentation
- Updated BUGS.md: Marked "KPI/Chart Values Revert to Full AUM" as RESOLVED
- Updated TODO.md: All Priority 0 implementation tasks marked complete
- Created test scripts: test_double_api_call.py, test_all_functions.py, test_api_behavior.py

## [Previous] - Multi-Selection Bug Fix: Tableau-like Behavior Restored (2025-08-01)

### 🐛 Bug Fix
- **Fixed critical regression**: Tables now show ALL items when 2+ items are selected, with selected items highlighted
- **Root cause**: Frontend was using v1 API endpoint (`/api/data`) instead of v2 (`/api/v2/dashboard`) for multi-selections
- **Solution**: Updated `loadFilteredData()` to use v2 API which supports the `selection_source` parameter

### 🔧 Technical Changes
- **Backend (v2 API)**:
  - Added `selection_source` parameter to `/api/v2/dashboard` endpoint
  - Updated `DashboardService` to conditionally exclude filters based on selection source
  - Modified `_build_full_where_clause()` to accept `exclude_source` parameter
  - All table methods now respect selection source for Tableau-like behavior

- **Frontend**:
  - Updated `loadFilteredData()` to use v2 API endpoint instead of v1
  - Added compatibility handling for v2 API response format (nested charts structure)
  - Calculate `selectionSource` when only one table has selections
  - Pass `selection_source` through entire API call chain (app.js → apiWrapper → v2Api)

### ✅ Testing Results
- Single client selection: Shows all 10 clients with selected one highlighted
- Multi-client selection: Shows all 10 clients (not just the 2 selected)
- Cross-table filtering: Other tables filter correctly based on selections
- KPI metrics: Update appropriately based on filtered context
- Performance: No regression, responses remain <200ms

### 📝 Documentation
- Updated BUGS.md: Marked "Table Multi-Selection Limiting Bug" as RESOLVED
- Updated PLAN.md: Phase 2.5 marked as COMPLETED
- Updated TODO.md: All Priority 0 tasks marked as complete

## [Latest] - Phase 4 Complete: Performance Enhancements (2025-08-01)

### Summary
Phase 4 completed successfully! All performance enhancements have been implemented, achieving significant improvements in response size, speed, and scalability.

### Added - Performance Enhancements
- **Response Compression (nginx gzip)**
  - Configured gzip compression at nginx level
  - Achieved 87% reduction in response size (111KB → 15KB)
  - Automatic content negotiation based on Accept-Encoding header
  - Added proxy buffering and timeout optimizations

- **Cursor-Based Pagination**
  - Implemented for all data tables (clients, funds, accounts)
  - Base64-encoded cursors for URL safety and tamper resistance
  - Independent pagination per table with has_more indicators
  - Charts automatically excluded when paginating (96% size reduction)
  - Complex cursor support for multi-field ordering (e.g., client_name + client_id)

- **Cache Warming (SQLite-based)**
  - Created cache tables for pre-computed dashboard data
  - Implemented warm_cache.py script for nightly refresh
  - Added CacheRepository for clean data access
  - Cache hits marked with from_cache metadata
  - Shared cache across all Flask processes via SQLite

### Performance Results
- Response compression: 87% reduction (exceeded 50% target)
- Paginated responses: 4.4KB vs 111KB full response
- Cache performance: 14ms cached vs 5ms filtered queries
- All p95 response times under 100ms target

### Technical Decisions
- Chose SQLite cache over Redis for operational simplicity
- Implemented compression at nginx level vs Flask-Compress
- Deferred WebSocket implementation (current performance sufficient)
- Deferred data windowing (pagination handles large datasets effectively)

## [Previous] - Phase 3 Complete: All Tables Migrated to v2 API (2025-08-01)

### Summary
Phase 3 completed successfully! All frontend components (charts, client table, fund table, and account table) have been migrated to the v2 API. The migration was completed ahead of schedule (4 weeks instead of 6-8 weeks).

### Added - Fund & Account Table Migration
- **Fund Table v2 Integration**
  - Fully integrated with tables-v2.js alongside client table
  - QTD/YTD values now display correctly (no more "N/A" issues)
  - Multi-selection works seamlessly with other tables
  - Maintains selection state with visual feedback
  
- **Account Table v2 Integration**  
  - Implemented with flexible balance field handling (`total_balance || balance || 0`)
  - Supports all selection combinations (client, fund, account)
  - Proper QTD/YTD calculations for all scenarios
  - Edge case handling for accounts with insufficient data

- **Comprehensive Test Suites**
  - test_fund_table_v2.js - Full Playwright test coverage for fund table
  - test_account_table_v2.js - Complete account table test scenarios
  - All tests passing with v2 API enabled

### Fixed in This Release
- Fund table QTD/YTD "N/A" values resolved through v2 API
- Account selection now properly filters related data
- Balance field flexibility handles different API response formats

### Performance Metrics
- Average response time: 75-120ms (well below 200ms target)
- Zero error rate increase during migration
- All multi-selection scenarios performing optimally

## [Previous] - Phase 3: Client Table Migration to v2 API (2025-08-01)

### Added
- **tables-v2.js Implementation**
  - New file implementing v2 table management following charts-v2.js pattern
  - Implements updateClientTable, updateFundTable, updateAccountTable methods
  - Uses apiWrapper.loadData for v1 compatibility
  - Properly maintains selection state and visual feedback
  - Console logging for debugging table updates

- **tableManager Dispatcher in app.js**
  - Routes between v1/v2 table implementations based on feature flags
  - Methods: update(), init(), clear(), updateClientTable(), updateFundTable(), updateAccountTable()
  - Maintains backwards compatibility with existing code
  - Seamless integration with existing selection system

### Fixed
- **Multi-Selection 500 Error**
  - Issue: `/api/data` endpoint failing with "no such column: cm.client_id" for multiple selections
  - Root cause: `generate_qtd_ytd_cte_sql` wasn't joining client_mapping table for fund queries
  - Solution: Updated function to include client_mapping join for all entity types
  - Result: Multi-selection now works flawlessly without errors

### Changed
- **Table Update Function Calls**
  - Replaced all direct updateXTable calls with tableManager.updateXTable throughout app.js
  - Ensures proper routing based on feature flags
  - No changes to external behavior, only internal routing

### Testing
- Single client selection: ✅ Works perfectly
- Multi-client selection: ✅ Aggregates balances correctly ($71.5M for 2 clients)
- KPI updates: ✅ Reflect filtered data accurately
- Feature flag routing: ✅ Properly switches between v1/v2
- Console logs: ✅ Show v2 tables being used when flag enabled
- Docker deployment: ✅ Runs with FEATURE_FLAGS='{"useV2Tables":true}'

### Technical Details
- Fixed account table $NaN issue by checking both account.total_balance and account.balance fields
- Added tables-v2.js to index.html script imports
- Maintained consistent error handling with graceful fallback to overview
- All functionality tested with Docker infrastructure and Playwright browser automation

## [Previous] - Phase 3: Frontend Migration Infrastructure (2025-08-01)

### Added
- **Normalized Cache System** (`static/js/cache.js`)
  - Entity-based storage for clients, funds, and accounts
  - TTL-based query caching (5 min for entities, 2 min for queries)
  - Selective cache invalidation based on user selections
  - Cache statistics and debugging helpers

- **V2 API Client** (`static/js/v2-api.js`)
  - Unified `fetchDataV2` function for v2 endpoint calls
  - Automatic cache integration
  - Response normalization and transformation
  - Retry logic with configurable attempts

- **API Wrapper** (`static/js/api-wrapper.js`)
  - Feature flag-based routing between v1 and v2 APIs
  - Automatic v2 to v1 fallback on errors
  - A/B testing support with stable user assignment
  - Metrics collection and buffering

- **Request/Response Interceptors** (`static/js/interceptors.js`)
  - Global fetch interception for monitoring
  - Performance tracking and aggregation
  - Error tracking and reporting
  - Configurable request/response logging

- **Docker Infrastructure**
  - Multi-container setup with docker-compose
  - Three instances: main (with flags), v1-only, v2-only
  - Nginx reverse proxy for A/B testing
  - Environment-based feature flag configuration

- **Feature Flag System**
  - Backend injection via Flask templates
  - Frontend checking in apiWrapper
  - Support for gradual rollout percentages
  - Per-user stable assignment for A/B testing

### Technical Decisions
- Chose vanilla JS over React/Redux to maintain gradual migration
- Implemented in-memory cache instead of persistent storage
- Used localStorage for A/B test user assignment stability
- Created compatibility layer to transform v2 responses to v1 format

### Infrastructure
- Docker Compose configuration for isolated testing
- Nginx configuration for load balancing and A/B routing
- Test script (`test-docker.sh`) for validation

### Next Steps
- Begin component migration starting with charts (simplest)
- Implement Playwright tests for migration validation
- Set up monitoring dashboard for A/B test metrics

## [Previous] - Phase 2: v2 API Foundation

### Added
- **Repository Pattern Architecture**
  - `BaseRepository` class with common database operations and connection management
  - `ClientRepository` for client-specific data access
  - `FundRepository` for fund-specific data access
  - `AccountRepository` for account-specific data access
  - Clean separation of data access from business logic

- **DashboardService Layer**
  - Centralized business logic for dashboard data aggregation
  - Consistent QTD/YTD calculation methodology across all tables
  - Efficient chart data generation (90-day and 3-year views)
  - KPI metrics calculation with 30-day change tracking
  - Smart JOIN optimization based on active filters

- **Unified /api/v2/dashboard Endpoint**
  - Single endpoint replaces 7+ scattered endpoints
  - Consistent response structure with metadata
  - Support for multiple filter types:
    - List filters: client_id, fund_name, account_id (repeatable)
    - Text filters: client_name, fund_ticker, account_number
    - Date filter: reference date for historical views
  - Fixed response structure (no field selection needed)

- **Request Validation**
  - UUID format validation for client_ids
  - Date format validation (YYYY-MM-DD)
  - Parameterized queries prevent SQL injection

- **RFC 7807 Error Responses**
  - Standardized error format for better debugging
  - Machine-readable error types
  - Detailed error messages with context
  - HTTP status codes properly mapped

- **Comprehensive Test Suite**
  - Integration tests for v2 endpoint (`test_v2_api.py`)
  - 9 test cases covering all major functionality
  - Tests for filters, validation, consistency, and error handling
  - All tests passing with <200ms response times

### Technical Details
- Repository pattern uses raw SQL for performance (no ORM overhead)
- Smart WHERE clause building with conditional JOINs
- Consistent use of CTEs for QTD/YTD calculations
- Docker configuration updated to include new directories

## [Latest] - Frontend JavaScript Fix for Client-Fund Endpoint

### Fixed
- **JavaScript error when selecting CLIENT+FUND combination**
  - Updated `loadClientFundData` function to handle new array response structure
  - Frontend was expecting singular objects (`client_balance`, `fund_balance`) but endpoint now returns arrays
  - Solution: Modified JavaScript to properly handle `client_balances` and `fund_balances` arrays
  - Removed redundant API call to `/api/client/<id>` that was overwriting fund table data

### Changed
- **app.js client-fund data handling**
  - Lines 1628-1637: Updated to check for arrays and handle them appropriately
  - Removed lines that made duplicate API call for fund data
  - Added null checks before accessing array data

### Testing Results
- CLIENT+FUND selections now work without JavaScript errors
- All three tables show consistent QTD/YTD values for intersection data
- Example: Capital Management + Corporate Bond Fund shows +0.2% QTD, +2.0% YTD across all tables

## [Previous] - QTD/YTD Metrics Alignment Fix

### Fixed
- **QTD/YTD metrics misalignment across tables during multi-selection**
  - All tables now show identical QTD/YTD percentages when filtering by client + fund combinations
  - Root cause: Different tables calculated metrics from different data subsets instead of unified intersection
  - Solution: Modified all queries to use `full_where_clause` for QTD/YTD calculations while maintaining display logic

### Added
- **Helper function for consistent QTD/YTD calculations**
  - `generate_qtd_ytd_cte_sql()` function eliminates code duplication across client/fund/account queries
  - Standardized Common Table Expression generation for quarter-to-date and year-to-date metrics
  - Enhanced NULL handling: Returns NULL (displays "N/A") for new entities instead of misleading 0%

### Changed
- **QTD/YTD calculation methodology**
  - Client balances: QTD/YTD now calculated from full intersection (not client-only subset)
  - Fund balances: QTD/YTD now calculated from full intersection (not fund-only subset)  
  - Account details: Updated for consistency with new helper function
  - Parameter handling: All QTD/YTD queries use `full_params` for proper filtering

### Technical Details
- Added debug logging when full intersection filtering is applied
- Modified `/api/data` endpoint queries in `get_filtered_data` function
- Ensured same balance = same QTD/YTD percentages across all tables
- Verified multi-selection support with Capital Management + Prime Money Market test case

## [Previous] - Options Dropdown Layout Improvements

### Fixed
- **Button alignment issues in options dropdown**
  - Right-aligned Download CSV button using `margin-left: auto` to separate from Apply Filters button
  - Prevents dynamic text size changes in download button from affecting Apply Filters button alignment
  - Added consistent flex layout properties to both buttons for uniform height

## [Previous] - Table Stability Improvements

### Fixed
- **Table width changes during selection/deselection**
  - Implemented `table-layout: fixed` to prevent automatic column adjustments
  - Added explicit width, min-width, and max-width to all columns
  - Removed font-weight changes that caused layout shifts
  
- **Row height inconsistencies**
  - Set fixed height (32px) on all table cells and headers
  - Added `box-sizing: border-box` for consistent dimensions
  - Implemented `vertical-align: middle` for proper content centering

### Changed
- **Visual selection indicators**
  - Replaced bold text with color change (#1e40af) to prevent width changes
  - Moved selection border to first cell instead of row
  - Added padding compensation for border to prevent content shift
  - Removed font-weight changes from percentage values

### Added
- **Table dimension constraints**
  - Fixed column widths: 40% (name), 30% (balance), 15% (QTD), 15% (YTD)
  - Consistent line-height (20px) across all cells
  - Text overflow handling with ellipsis
  - Horizontal scroll support in table wrapper

## [Previous] - Table Selection System Overhaul

### Changed
- **Complete rewrite of table selection functionality**
  - Replaced previous active/selected class system with persistent selection state
  - Implemented Tableau-like behavior: click to select, click again to deselect
  - Multiple selections now supported across all tables simultaneously
  
### Added
- **Global selection state management**
  - `selectionState` object tracks selections using Sets for each table type
  - Event delegation for better performance (handlers on tables, not rows)
  - Automatic data filtering based on current selections
  
- **Enhanced visual indicators**
  - Selected rows: Light blue background (#dbeafe)
  - 3px blue left border on selected rows
  - Bold text in first column of selected rows
  - Darker blue on hover (#bfdbfe)
  
- **Improved user interactions**
  - Click outside tables to clear all selections
  - Header click clears selections and returns to overview
  - Selections persist when data refreshes
  
### Fixed
- Selection formatting not showing (blue highlighting)
- Click-to-deselect functionality not working
- Event handler duplication issues
- Selection state not persisting across data updates

### Technical Details
- Removed `addTableClickHandlers()` repetitive calls
- Replaced with `initializeTableHandlers()` called once on page load
- Added `restoreSelectionVisuals()` to maintain visual state
- Simplified data loading functions to work with new selection system