# Changelog

## [Latest] - Phase 2: v2 API Foundation

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