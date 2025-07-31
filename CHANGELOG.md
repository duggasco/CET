# Changelog

## [Latest] - UI Button Consistency Fix

### Fixed
- **Options dropdown button height inconsistency**
  - Added `display: flex`, `align-items: center`, and `justify-content: center` to Apply Filters button
  - Ensures consistent height between Apply Filters and Download CSV buttons
  - Both buttons now use identical flex layout properties

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