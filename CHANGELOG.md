# Changelog

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