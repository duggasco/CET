# Long-Term Plan for QTD/YTD Consistency Fix

## 🚨 CRITICAL BUG FIX REQUIRED (Priority 0)
**Multi-Selection Table Display Bug**: Tables only show selected items instead of all items with selections highlighted (Tableau-like behavior broken since v1)

### Immediate Action Required
- **Issue**: Selecting 2+ items in any table causes all other items to disappear
- **Impact**: Core functionality regression - breaks expected Tableau-like behavior
- **Root Cause**: Frontend logic difference between single vs multi-selection paths
- **Solution**: Implement selection_source parameter to maintain proper table display
- **Timeline**: Must fix before continuing Phase 3 migration

## Executive Summary
Transform a fragmented API with inconsistent calculations into a unified, performant, and maintainable system over 4-5 months.

## Problem Statement
- Multiple API endpoints with inconsistent behavior
- QTD/YTD calculations show different values across tables when multiple selections are made
- Fund table shows "N/A" for QTD/YTD in certain selection combinations
- Frontend routing logic scattered across different endpoints
- Technical debt: SQL queries embedded in route handlers, no validation, no documentation
- **NEW**: Multi-selection breaks table display (items disappear instead of staying visible)

## Core Solution Principle
When multiple selections are made (CLIENT + FUND + ACCOUNT), all tables should display the INTERSECTION data with consistent QTD/YTD calculations based on that same intersection. Tables should maintain Tableau-like behavior where selected items are highlighted but all items remain visible.

## Phase 1: Critical Fixes (2 weeks) ✅ COMPLETED
**Goal:** Stop the bleeding

### Tasks:
1. Fix `/api/data` endpoint:
   - Change line 1732: `{client_where_clause}` → `{full_where_clause}`
   - Change line 1756: `client_params` → `full_params`
   - Change line 1772: `{fund_where_clause}` → `{full_where_clause}`
   - Change line 1796: `fund_params` → `full_params`

2. Fix `/api/client/<id>/fund/<name>` endpoint to return:
   ```json
   {
     "recent_history": [...],
     "long_term_history": [...],
     "client_balances": [{
       "client_name": "...",
       "client_id": "...",
       "total_balance": ...,
       "qtd_change": ...,
       "ytd_change": ...
     }],
     "fund_balances": [{
       "fund_name": "...",
       "fund_ticker": "...",
       "total_balance": ...,
       "qtd_change": ...,
       "ytd_change": ...
     }],
     "account_details": [{
       "account_id": "...",
       "client_name": "...",
       "fund_name": "...",
       "balance": ...,
       "qtd_change": ...,
       "ytd_change": ...
     }]
   }
   ```

3. Add integration tests for multi-selection scenarios
4. Create minimal API behavior documentation (marked as "v1 - deprecated")

### Success Criteria:
- QTD/YTD values consistent across all tables
- No "N/A" values when data exists
- All tests passing

## Phase 2: v2 Foundation (4 weeks) ✅ COMPLETED
**Goal:** Build it right from the start

### New API Design:
```
GET /api/v2/dashboard?client_id=123&fund_name=Prime&fields=client_balances.name,client_balances.balance
```

### Features:
- Repository pattern for clean data access
- Request validation (Joi/Yup/Zod)
- Dot notation field selection with performance limits
- RFC 7807 error responses:
  ```json
  {
    "type": "/errors/insufficient-data",
    "title": "Insufficient data for QTD calculation",
    "status": 422,
    "detail": "Account CAP-006-000 has less than 90 days of history",
    "instance": "/api/v2/dashboard?account_id=CAP-006-000"
  }
  ```
- OpenAPI/Swagger documentation
- Performance monitoring setup (DataDog/New Relic)
- WebSocket architecture spike (document approach, defer implementation)

### Success Criteria:
- v2 endpoint handles all use cases with <200ms response time
- Complete test coverage
- API documentation available

## Phase 2.5: Multi-Selection Display Bug Fix (1 week) 🔴 URGENT
**Goal:** Fix table display regression before continuing migration

### Implementation Plan:
1. **Backend Changes (app.py & dashboard_service.py)**:
   - Add `selection_source` parameter to `/api/v2/dashboard`
   - Modify `_build_full_where_clause` to accept `exclude_source` parameter
   - Update table methods to conditionally exclude filters based on selection_source

2. **Frontend Changes (app.js)**:
   - Update `loadFilteredData` to determine selection_source
   - Pass selection_source parameter when single table has selections
   - Maintain intersection behavior for multi-table selections

### Success Criteria:
- Single table selections show ALL items with selections highlighted
- Multi-table selections show proper intersections
- No performance regression
- Maintains backward compatibility

## Phase 3: Incremental Migration (6-8 weeks) 🚧 PAUSED
**Goal:** Migrate safely without breaking production

### Progress Update (2025-08-01):
- ✅ Infrastructure setup complete (Week 0-1)
- ✅ Charts migrated to v2 API (Week 1-2)
- ✅ Client table migrated to v2 API (Week 3-4)
- 🛑 PAUSED: Must fix multi-selection bug before continuing
- 🔄 Fund table migration postponed (Week 5-6)

### Frontend Changes:
1. Implement normalized cache:
   ```javascript
   {
     clients: { [id]: {...} },
     funds: { [name]: {...} },
     accounts: { [id]: {...} },
     queries: { [queryKey]: {data, timestamp} }
   }
   ```

2. Single data fetching function:
   ```javascript
   fetchData(selections) {
     const params = new URLSearchParams();
     if (selections.client) params.append('client_id', selections.client);
     if (selections.fund) params.append('fund_name', selections.fund);
     if (selections.account) params.append('account_id', selections.account);
     return fetch(`/api/v2/dashboard?${params}`);
   }
   ```

### Migration Schedule:
- Week 1-2: Charts (least complex) ✅ COMPLETED
- Week 3-4: Client table ✅ COMPLETED
- Week 5-6: Fund table 🔄 IN PROGRESS
- Week 7-8: Account table

### Rollout Strategy:
- Feature flag infrastructure (LaunchDarkly/custom)
- A/B testing: 10% → 50% → 100% rollout
- Parallel run of v1/v2

### Success Criteria:
- No increase in error rates
- Positive user feedback
- All components migrated

## Phase 4: Enhancement (4 weeks) 🚧 IN PROGRESS
**Goal:** Optimize and enhance

### Features:
- ✅ Cursor pagination for large datasets
- ✅ Response compression (gzip/brotli) 
- ✅ Cache warming strategies
- ⏸️ Consider WebSocket implementation (deferred - current performance sufficient)
- ⏸️ Data windowing for time-series (deferred - pagination handles large datasets)

### Implementation Details:
1. **Response Compression (nginx gzip)**
   - Achieved 87% reduction in response size (111KB → 15KB)
   - Configured at nginx level for all proxied responses
   - Automatic content negotiation based on Accept-Encoding

2. **Cursor Pagination**
   - Base64-encoded cursors for URL safety
   - Independent pagination for clients, funds, and accounts
   - Charts automatically excluded when paginating (96% size reduction)
   - Supports complex multi-field cursors for stable ordering

3. **Cache Warming (SQLite-based)**
   - Pre-computed tables for overview data (no filters)
   - Refreshed nightly after data updates
   - Shared across all Flask processes
   - Cache hit provides instant response for dashboard overview

### Success Criteria:
- ✅ 87% reduction in data transfer (exceeded 50% target)
- ✅ Sub-100ms p95 response times (14ms cached, 5ms filtered)
- ✅ Improved user experience metrics

## Phase 5: Cleanup (2 weeks)
**Goal:** Remove technical debt

### Tasks:
- Remove feature flags
- Deprecate v1 endpoints with 3-month sunset notice
- Archive old code
- Complete documentation
- Team knowledge transfer sessions

### Success Criteria:
- v1 traffic < 1%
- Complete documentation
- Team trained on new system

## Technical Decisions Summary

### API Architecture:
- **Chosen:** REST + field selection over GraphQL
- **Rationale:** Simpler for team, meets current needs without paradigm shift

### Query Parameter Format:
- **Chosen:** Dot notation (`fields=client_balances.name,client_balances.balance`)
- **Rationale:** Balance between flexibility and simplicity

### Frontend State Management:
- **Chosen:** Vanilla JS normalized cache (changed from RTK Query)
- **Rationale:** Simpler migration path without framework overhead, team familiarity

### Error Handling:
- **Chosen:** RFC 7807 (Problem Details)
- **Rationale:** Standardized, machine-readable, debugging-friendly

## Success Metrics

### Quantitative:
- QTD/YTD calculation errors: < 0.1% (from current ~10%)
- API response time: p95 < 200ms
- Data transfer: 50% reduction
- Bug reports: 90% reduction in data-related issues

### Qualitative:
- Developer survey: 80% satisfaction with new API
- Quarterly feedback sessions
- Time to implement new features: 50% reduction

## Risk Mitigation
- Automated regression test suite
- Rollback capability at component level
- Daily standup during migration phase
- Comprehensive logging and monitoring
- Gradual rollout with feature flags

## Implementation Notes

### Cache Key Strategy:
```javascript
cacheKey = hash({
  endpoint: '/api/v2/dashboard',
  filters: { client_id: '123', date_range: '90d' },
  fields: ['client_balances.name', 'client_balances.balance']
})
```

### API Response Format:
```json
{
  "result": {
    "client_balances": [...],
    "fund_balances": [...],
    "charts": {...}
  },
  "metadata": {
    "timestamp": "2025-01-31T12:00:00Z",
    "filters_applied": {...},
    "calculations": {"qtd": true, "ytd": true}
  },
  "pagination": {
    "cursor": "...",
    "has_more": false
  }
}
```

## Timeline Summary
- **Total Duration:** 4-5 months
- **Phase 1:** 2 weeks (Critical Fixes) ✅ COMPLETED
- **Phase 2:** 4 weeks (v2 Foundation) ✅ COMPLETED
- **Phase 3:** 6-8 weeks (Migration) 🚧 Week 4 of 8 complete
- **Phase 4:** 4 weeks (Enhancement)
- **Phase 5:** 2 weeks (Cleanup)

## Current Status (2025-08-01)
- Phase 1 & 2 complete
- Phase 3 infrastructure built and tested
- Charts successfully migrated to v2 API
- Client table successfully migrated to v2 API
- Multi-selection 500 error fixed
- On track for fund and account table migrations

## Next Steps
1. Begin Phase 1 implementation immediately
2. Set up project tracking and communication channels
3. Schedule weekly progress reviews
4. Prepare stakeholder communications