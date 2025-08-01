# TODO List for QTD/YTD Consistency Fix

Based on PLAN.md - Track implementation progress by marking items as completed.

## 🚨 PRIORITY 0: Multi-Selection Table Display Bug Fix (URGENT)

### Issue Description
Tables only show selected items instead of all items with selections highlighted. This breaks the Tableau-like behavior and is a regression from v1 functionality.

### ⚠️ CRITICAL: Fix V2 endpoints we're migrating TO, not deprecated ones!

### Backend Implementation - V2 Architecture ✅ COMPLETED

#### `/api/v2/dashboard` endpoint (app.py ~line 1982)
- [x] Add selection_source parameter extraction
  ```python
  selection_source = request.args.get('selection_source')
  ```
- [x] Pass selection_source to dashboard service (~line 2027)
  ```python
  data = service.get_dashboard_data(
      # ... existing params ...
      selection_source=selection_source
  )
  ```

#### DashboardService (dashboard_service.py)
- [x] Update get_dashboard_data method signature
  - [x] Add `selection_source: Optional[str] = None` parameter
- [x] Pass selection_source to table methods (~lines 59-77)
  - [x] Update _get_client_balances_with_metrics call
  - [x] Update _get_fund_balances_with_metrics call
  - [x] Update _get_account_details_with_metrics call
- [x] Update _build_full_where_clause method (~line 432)
  - [x] Add `exclude_source: Optional[str] = None` parameter
  - [x] Skip client_ids filter if exclude_source == 'client'
  - [x] Skip fund_names filter if exclude_source == 'fund'
  - [x] Skip account_ids filter if exclude_source == 'account'
- [x] Update each table method to use selection_source
  - [x] _get_client_balances_with_metrics: Use exclude_source='client' if selection_source=='client'
  - [x] _get_fund_balances_with_metrics: Use exclude_source='fund' if selection_source=='fund'
  - [x] _get_account_details_with_metrics: Use exclude_source='account' if selection_source=='account'
- [x] Update paginated methods to accept selection_source parameter
  - [x] _get_client_balances_with_metrics_paginated
  - [x] _get_fund_balances_with_metrics_paginated
  - [x] _get_account_details_with_metrics_paginated

### Frontend Implementation ✅ PARTIALLY COMPLETED

#### Direct API calls (app.js - loadFilteredData function ~line 1697)
- [x] Add selection source determination logic after try block
- [x] Update URL construction to include selection_source for old /api/data endpoint

#### V2 API Integration (for tables using apiWrapper)
- [x] Update getCurrentSelectionParams to include selectionSource (~line 23)
- [x] Update apiWrapper.loadDataV2 to pass selectionSource through (~line 63)
- [ ] Update v2Api.buildQueryParams to include selection_source parameter
  - [ ] Add selection_source to query params if present in selections object

### Testing
- [ ] Test single client selection - verify all clients visible
- [ ] Test multiple client selections - verify all clients visible
- [ ] Test client + fund selection - verify intersection behavior
- [ ] Test all three table selections - verify intersection behavior
- [ ] Verify performance is not impacted
- [ ] Test with text filters active
- [ ] Test with date selections

### Documentation
- [ ] Update BUGS.md to mark issue as RESOLVED
- [ ] Update CHANGELOG.md with fix details
- [ ] Update API documentation for new parameter

## Phase 1: Critical Fixes (2 weeks) ✅ COMPLETED

### Fix `/api/data` endpoint WHERE clause inconsistencies ✅
- [x] Test current behavior - verify the bug
- [x] Research WHERE clause construction (lines 1650-1700)
- [x] Understand difference between client_where_clause, fund_where_clause, full_where_clause
- [x] Change line 1732: `{client_where_clause}` → `{full_where_clause}`
- [x] Change line 1756: `client_params` → `full_params`
- [x] Change line 1772: `{fund_where_clause}` → `{full_where_clause}`
- [x] Change line 1796: `fund_params` → `full_params`
- [x] Test the fix works correctly

### Fix `/api/client/<id>/fund/<name>` endpoint ✅
- [x] Research current endpoint implementation
- [x] Understand what data it currently returns
- [x] Plan changes to return proper structure:
  - [x] Add client_balances array (single item)
  - [x] Change fund_balance to fund_balances array (single item)
  - [x] Ensure account_details includes qtd_change and ytd_change
- [x] Implement the changes
- [x] Test the endpoint returns correct structure

### Fix JavaScript Frontend ✅
- [x] Update loadClientFundData function to handle array response
- [x] Remove redundant API calls
- [x] Add null checks for array data
- [x] Test CLIENT+FUND selection works without errors
- [x] Verify QTD/YTD consistency across all tables

### Documentation ✅
- [x] Update BUGS.md with JavaScript error resolution
- [x] Update CHANGELOG.md with frontend fix details
- [x] Document the complete fix including both backend and frontend changes

### Add integration tests
- [ ] Create test file for multi-selection scenarios
- [ ] Test CLIENT selection only
- [ ] Test CLIENT+FUND selection
- [ ] Test CLIENT+FUND+ACCOUNT selection
- [ ] Test that QTD/YTD values are consistent across tables
- [ ] Test that balances match when showing intersection data

## Phase 2: v2 Foundation (4 weeks) ✅ COMPLETED

### API Design ✅
- [x] Design `/api/v2/dashboard` endpoint structure
- [x] Implement repository pattern for data access
- [x] Add request validation (UUID and date format validation)
- [x] Skip dot notation field selection (YAGNI - fixed response structure)
- [x] Add RFC 7807 error responses
- [ ] Create OpenAPI/Swagger documentation

### Infrastructure ✅
- [ ] Set up performance monitoring (DataDog/New Relic) - deferred
- [ ] WebSocket architecture spike - deferred
- [x] Create comprehensive test suite

## Phase 3: Incremental Migration (6-8 weeks) 🚧 PAUSED - Fix multi-selection bug first!

### Frontend Infrastructure ✅ COMPLETED
- [x] Implement normalized cache (vanilla JS instead of RTK Query)
- [x] Create single data fetching function (fetchDataV2)
- [x] Set up feature flag infrastructure
- [x] Add request/response interceptors for monitoring
- [x] Implement v2 to v1 fallback for resilience
- [x] Set up Docker infrastructure for A/B testing

### Component Migration
- [x] Week 1-2: Migrate Charts ✅ COMPLETED
  - [x] Created charts-v2.js with v2 API integration
  - [x] Implemented chartManager dispatcher
  - [x] Added useV2Charts feature flag
  - [x] Tested with Docker setup
  - [x] Verified data accuracy and performance
- [x] Week 3-4: Migrate Client table ✅ COMPLETED
  - [x] Fixed multi-selection 500 error (client_mapping join issue)
  - [x] Created tables-v2.js following charts-v2.js pattern
  - [x] Implemented tableManager dispatcher
  - [x] Added useV2Tables feature flag
  - [x] Tested single and multi-selection scenarios
  - [x] Verified KPI updates and data accuracy
- [ ] Week 5-6: Migrate Fund table 🚧 NEXT
- [ ] Week 7-8: Migrate Account table

### Testing & Rollout
- [ ] Set up A/B testing
- [ ] 10% rollout
- [ ] 50% rollout
- [ ] 100% rollout

## Phase 4: Enhancement (4 weeks)

### Performance Optimizations
- [ ] Implement cursor pagination
- [ ] Add response compression
- [ ] Implement cache warming strategies
- [ ] Consider WebSocket implementation

### Monitoring
- [ ] Verify <100ms p95 response times
- [ ] Measure data transfer reduction
- [ ] Monitor error rates

## Phase 5: Cleanup (2 weeks)

### Code Cleanup
- [ ] Remove feature flags
- [ ] Deprecate v1 endpoints (3-month notice)
- [ ] Archive old code

### Knowledge Transfer
- [ ] Update all documentation
- [ ] Conduct team training sessions
- [ ] Document lessons learned

## Success Metrics Tracking

### Quantitative Metrics
- [ ] Measure QTD/YTD calculation error rate (target: <0.1%)
- [ ] Measure API response time (target: p95 <200ms)
- [ ] Measure data transfer reduction (target: 50%)
- [ ] Track bug report reduction (target: 90%)

### Qualitative Metrics
- [ ] Conduct developer satisfaction survey
- [ ] Hold quarterly feedback session
- [ ] Measure time to implement new features

---

**Last Updated:** 2025-08-01
**Status:** URGENT - Multi-selection bug fix required before continuing Phase 3
**Current:** Phase 3 PAUSED at Week 4 of 8 - Must fix regression first
**Next Steps:** 
1. Fix multi-selection table display bug (Priority 0)
2. Resume Phase 3 Week 5-6: Migrate Fund table to v2 API

## Summary of Phase 1 Accomplishments:
1. ✅ Fixed `/api/data` endpoint WHERE clause inconsistencies
2. ✅ Fixed `/api/client/<id>/fund/<name>` endpoint response structure
3. ✅ Fixed JavaScript frontend to handle new response format
4. ✅ Verified QTD/YTD consistency across all tables for CLIENT+FUND+ACCOUNT selections
5. ✅ Updated documentation (BUGS.md and CHANGELOG.md)

**Key Result:** Multi-selection scenarios now show consistent QTD/YTD values across all tables!

## Summary of Phase 2 Accomplishments:
1. ✅ Created repository pattern with BaseRepository, ClientRepository, FundRepository, AccountRepository
2. ✅ Implemented DashboardService for complex QTD/YTD calculations
3. ✅ Built unified `/api/v2/dashboard` endpoint with consistent response structure
4. ✅ Added RFC 7807 compliant error responses
5. ✅ Implemented validation for dates and UUID formats
6. ✅ Created comprehensive integration test suite (9 tests, all passing)
7. ✅ Maintained <200ms response time target

**Key Results:**
- Single unified endpoint replaces 7+ scattered endpoints
- Clean separation of concerns with repository pattern
- Consistent QTD/YTD calculations using shared service logic
- Production-ready error handling and validation

## Summary of Phase 3 Accomplishments (So Far):
1. ✅ Built complete frontend migration infrastructure
   - Normalized cache with TTL and selective invalidation
   - V2 API client with retry logic and caching
   - API wrapper with feature flag routing and fallback
   - Request/response interceptors for monitoring
2. ✅ Set up Docker A/B testing environment
   - Multi-container setup (main, v1-only, v2-only)
   - Nginx reverse proxy for load balancing
   - Environment-based feature flag configuration
3. ✅ Completed first component migration (Charts)
   - charts-v2.js using v2 API
   - chartManager dispatcher in app.js
   - Feature flag control (useV2Charts)
   - Fully tested and working
4. ✅ Completed client table migration
   - Fixed critical multi-selection 500 error
   - tables-v2.js implementation with v2 API integration
   - tableManager dispatcher for v1/v2 routing
   - Feature flag control (useV2Tables)
   - Thoroughly tested with Docker and Playwright

**Key Results:**
- Infrastructure proven with two successful migrations
- Performance maintained (<200ms responses)
- Multi-selection bug fixed permanently
- Feature flags enable safe, gradual rollout
- 50% of table components now migrated