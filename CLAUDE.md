# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Run
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate sample data
python database.py

# Run application (default port 9095)
./run.sh

# Run with custom port
./run.sh 8080
./run.sh --port 3000

# Run directly with Python
FLASK_PORT=9095 python app.py
```

### Database Management
- Regenerate sample data: `python database.py`
- Database file: `client_exploration.db` (SQLite)

## Architecture Overview

This is a Flask-based web application for exploring money market mutual fund client data with interactive filtering and Tableau-like selection behavior.

### Backend Architecture
- **Flask Application** (`app.py`): RESTful API with the following endpoints
  - `/api/overview`: Aggregated data across all clients/funds with QTD/YTD for all levels
  - `/api/client/<client_id>`: Client-specific filtered data with QTD/YTD for funds and accounts
  - `/api/fund/<fund_name>`: Fund-specific filtered data with QTD/YTD for clients and accounts
  - `/api/account/<account_id>`: Individual account details with fund allocation
  - `/api/account/<account_id>/fund/<fund_name>`: Account details filtered by fund
  - `/api/client/<client_id>/fund/<fund_name>`: Client-fund combination data with QTD/YTD
  - `/api/date/<date_string>`: Data for a specific date with QTD/YTD relative to that date
  - `/api/download_csv`: Streams filtered data as CSV with all daily records
  - `/api/download_csv/count`: Returns count of rows that would be in CSV

- **QTD/YTD Calculations**: 
  - Current data: Calculated from actual quarter/year start dates
  - Historical dates: Calculated relative to the selected date's quarter/year
  - All endpoints return QTD/YTD percentages for clients, funds, and accounts

### Database Schema
Two main tables in SQLite:
- **client_mapping**: Maps account IDs to client names and UUIDs
  - `account_id` (TEXT PRIMARY KEY)
  - `client_name` (TEXT)
  - `client_id` (TEXT) - UUID format
  
- **account_balances**: Daily fund-level balances per account
  - `id` (TEXT PRIMARY KEY) - UUID format
  - `account_id` (TEXT)
  - `fund_name` (TEXT)
  - `balance_date` (DATE)
  - `balance` (DECIMAL)

### Frontend Architecture
- **Interactive Dashboard** (`templates/index.html`, `static/js/app.js`)
  - Monday.com-inspired design with fixed height layout (100vh, no scrolling) on desktop
  - Chart.js for visualizations:
    - 90-day line chart showing daily balance history (blue #0085ff)
    - 3-year line chart showing daily balance history (green #00d647)
  - Layout: 
    - Fixed header with title and filter indicator
    - KPI cards section (4 cards in a row on desktop, single column on mobile)
    - 50/50 split content area on desktop - charts on left, tables on right
    - Stacked layout on mobile - charts above tables
    - Tables scroll independently within their fixed containers
  - Tableau-like multi-selection behavior across all tables
  - Three main data views with consistent columns:
    - Client Balances: Client Name, Total Balance, QTD %, YTD %
    - Fund Summary: Fund Name, Total Balance, QTD %, YTD %
    - Account Details: Account ID, Total Balance, QTD %, YTD %
  - Chart interactivity: Click any data point to filter tables to that specific date
  - Professional desktop-optimized design with automatic mobile detection

### Selection Behavior Implementation (Tableau-like)
- **Multi-selection**: Multiple rows can be selected simultaneously across all tables
- **Visual persistence**: Selected rows show light blue background (#dbeafe) with 3px left border
- **Toggle behavior**: Click to select, click again to deselect any row
- **Selection state management**: Global state tracks selections using Sets for each table
- **Click-outside**: Clicking outside tables clears all selections and returns to overview
- **Data filtering**: Tables automatically update to show related data based on selections:
  - Select client(s) → See their funds and accounts
  - Select fund(s) → See clients and accounts with those funds
  - Select account(s) → See owning client and funds in those accounts
- **Combined selections**: Multiple selections across tables create intersection filters
- **Visual indicators**:
  - Selected rows: Light blue background (#dbeafe) with dark blue text (#1e40af)
  - Hover on selected: Darker blue (#bfdbfe)
  - Left border: 3px solid blue (#2563eb) on first cell of selected rows
- **Persistence**: Selections remain visible when data refreshes

### Table Stability Features
- **Fixed Layout**: Tables use `table-layout: fixed` to prevent column width changes
- **Static Dimensions**:
  - Row height: Fixed at 32px with `box-sizing: border-box`
  - Column widths: Locked with width, min-width, and max-width properties
  - First column: 40% | Balance column: 30% | QTD/YTD columns: 15% each
- **No Layout Shifts**:
  - Font weights remain constant (no bold on selection)
  - Visual emphasis through color changes instead of weight changes
  - Border compensation with padding adjustment
- **Text Handling**:
  - Overflow: hidden with ellipsis for long content
  - No text wrapping to maintain row height
  - Consistent line-height (20px) for vertical alignment
- **Performance**: Fixed dimensions eliminate reflow/repaint on selection changes

### Key Implementation Details
- All IDs use UUIDs (as per global CLAUDE.md instructions)
- Database generation ensures consistent fund allocations per account throughout time
- Charts display daily data points:
  - 90-day chart: 91 data points
  - 3-year chart: 1095 data points  
- Row factory set to sqlite3.Row for dict-like access to query results
- **Selection System**:
  - Global `selectionState` object maintains Sets for clients, funds, and accounts
  - Event delegation on table elements (not individual rows) for performance
  - `initializeTableHandlers()` sets up click handlers once on page load
  - `restoreSelectionVisuals()` reapplies visual selection after data updates
  - `updateDataBasedOnSelections()` handles data filtering based on current selections
- QTD/YTD values:
  - Current data: Calculated from actual quarter/year boundaries
  - Historical dates: Calculated relative to selected date (e.g., June 1 shows QTD since March 31)
  - All tables (clients, funds, accounts) include QTD/YTD calculations
- Filter types maintained for proper navigation:
  - `overview`, `client`, `fund`, `account`
  - `client-fund` (combination selections)
  - `date` (from chart clicks)
- KPI Cards dynamically update based on filter context:
  - Total AUM: Always shows filtered total
  - Active Clients/Accounts: Changes label and count based on view
  - Funds: Shows count relevant to current filter
  - Avg. YTD Growth: Weighted average of visible data

### Design System
- **Color Palette** (Monday.com inspired):
  - Primary: #0085ff (blue)
  - Success: #00d647 (green) 
  - Error: #ff3d57 (red)
  - Text: #323338 (dark gray)
  - Secondary: #676879 (medium gray)
  - Background: #f7f7f7
  - Cards: #ffffff
  - Selection: #dbeafe (light blue background)
  - Selection border: #2563eb (blue)
  - Selection text: #1e40af (dark blue)
- **Typography**: System font stack, compact sizing (10-16px on desktop, slightly larger on mobile)
- **Layout**: 
  - Desktop: Fixed height (100vh) with no page scrolling
  - Mobile: Natural scrolling enabled for better usability
  - Header: 8px vertical padding (12px on mobile)
  - KPI cards: 8px padding, 28px icon size (larger on mobile)
  - Content area: 50/50 split on desktop, stacked on mobile
  - Tables: Independent scrolling within fixed containers
- **Components**: 
  - Clean white cards with subtle shadows (1px 2px rgba(0,0,0,0.05))
  - Thin borders (#e6e9ef)
  - Fixed table layout with static dimensions
  - Consistent column widths across tables (40% identifier, 30% balance, 15% each QTD/YTD)

### Mobile Features
- **Automatic Detection**: Mobile view activates when:
  - User agent matches mobile devices (iPhone, iPad, Android, etc.)
  - Touch support is detected
  - Screen width is ≤ 768px
- **Mobile Optimizations**:
  - Single-column KPI card layout
  - Stacked charts and tables
  - Horizontal scrolling for tables with sticky headers
  - Touch-optimized row heights (44px minimum)
  - Adjusted font sizes and chart tick marks
  - Smooth momentum scrolling (-webkit-overflow-scrolling)
  - Natural page scrolling (no fixed height restriction)
- **Cache Busting**: Query string versioning for CSS/JS files ensures users always get latest updates

## Troubleshooting

### Table Selection Issues
- **Selections not showing**: Check browser console for JavaScript errors, ensure CSS is loading with cache bust parameter
- **Click not working**: Verify event handlers are initialized with `initializeTableHandlers()` on page load
- **Selection not persisting**: Ensure `restoreSelectionVisuals()` is called after data updates
- **Multiple selections not filtering**: Check `updateDataBasedOnSelections()` logic and API endpoints
- **Table width/height changing**: Verify `table-layout: fixed` is applied and column widths are set with min/max-width
- **Text causing layout shifts**: Check that font-weight remains constant and overflow is handled properly

### Common Issues
- **Cache problems**: The app uses query string versioning (`?v={{ cache_bust }}`) to force browser updates
- **Mobile detection**: Based on user agent, touch support, and screen width (≤ 768px)
- **Database regeneration**: Run `python database.py` to create fresh sample data

## Recent Updates

### KPI Fix for Multi-Selection Filtering (January 2025)
- **Problem Resolved**: Fixed Total AUM KPI showing incorrect values during multi-client selections
- **Root Cause**: KPI calculations used unfiltered `client_balances` data while tables showed filtered results
- **Backend Solution**: 
  - Added comprehensive `kpi_metrics` query in `/api/data` endpoint (app.py:1789-1843)
  - Uses `full_where_clause` to ensure KPI calculations respect all active filters
  - Calculates filtered totals for AUM, client count, fund count, account count
  - Includes accurate 30-day percentage change based on filtered data
  - Robust error handling with COALESCE and fallback values for edge cases
- **Frontend Solution**:
  - Updated `updateKPICards` function in app.js to prioritize backend `kpi_metrics`
  - Maintains backward compatibility with fallback calculations
  - All KPI cards now accurately reflect filtered selections
- **Testing Results**: 
  - ✅ Single selection: $42.5M → matches selected client
  - ✅ Multi-selection: $75.5M (2 clients), $106.3M (3 clients) → accurate sums
  - ✅ 30-day change percentage calculated on filtered data only
  - ✅ Chart data remains consistent with KPI values

### CSV Download Feature
- Added comprehensive CSV export functionality for filtered datasets
- Download button in header shows real-time row count
- Exports all daily granular data with complete balance history
- CSV includes: Date, Client Name/ID, Account ID, Fund Name, Balance, QTD%, YTD%, QTD/YTD $Change, As of Date
- Dynamic filename reflects current filters (e.g., `financial_data_3clients_2funds_20250731_150404.csv`)
- Streaming response handles large datasets efficiently (up to 1M rows)
- Pre-fetches historical data for accurate QTD/YTD calculations
- Respects all active filters: multi-selections, text filters, and date selections

### Table Stability Improvements
- Fixed table layout implementation prevents column width changes
- Static row heights (32px) with proper box-sizing
- Visual selection through color changes instead of font-weight
- All columns locked with width, min-width, and max-width properties
- Text overflow handled with ellipsis to maintain dimensions

### Table Selection System (Tableau-like behavior)
- Completely rebuilt selection system with persistent visual state
- Multiple selections supported across all tables simultaneously
- Click to select (blue highlight), click again to deselect
- Tables automatically filter to show related data based on selections
- Selection state managed globally using Sets for performance
- Visual indicators include blue background, left border, and color changes

## Testing Results

### Comprehensive Multi-Selection Testing (Completed)
The multiple table selection functionality has been thoroughly tested with Playwright automation. All tests passed successfully:

#### Test Coverage
1. **Multiple client selections** - Correctly aggregated balances across selected clients
2. **Multiple fund selections** - Correctly filtered and summed balances for selected funds  
3. **Multiple account selections** - Correctly calculated total AUM from selected accounts
4. **Clients + funds combination** - Proper intersection filtering with accurate balance calculations
5. **Clients + accounts combination** - Cross-table filtering worked correctly
6. **Funds + accounts combination** - Intersection of selected funds and accounts calculated properly
7. **All three tables selected** - Correct intersection of all three selections with accurate balance
8. **Fund balances verification** - Fund balances correctly sum to account/client totals
9. **Account balance verification** - Account balances match parent totals
10. **Zero balance edge cases** - System correctly displays $0 balances with appropriate formatting

#### Key Findings
- Multi-selection functionality works correctly across all tables
- Balance calculations are accurate for all selection combinations
- Cross-table filtering creates proper data intersections
- KPI cards update correctly based on selections
- Chart functionality continues to work alongside multi-selections
- Zero balances are handled properly with "$0" display
- QTD/YTD calculations remain accurate with filtered data
- Selection visual persistence maintained during data updates