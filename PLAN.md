# Long-Term Plan for QTD/YTD Consistency Fix

## Executive Summary
Transform a fragmented API with inconsistent calculations into a unified, performant, and maintainable system over 4-5 months.

## Problem Statement
- Multiple API endpoints with inconsistent behavior
- QTD/YTD calculations show different values across tables when multiple selections are made
- Fund table shows "N/A" for QTD/YTD in certain selection combinations
- Frontend routing logic scattered across different endpoints
- Technical debt: SQL queries embedded in route handlers, no validation, no documentation

## Core Solution Principle
When multiple selections are made (CLIENT + FUND + ACCOUNT), all tables should display the INTERSECTION data with consistent QTD/YTD calculations based on that same intersection.

## Phase 1: Critical Fixes (2 weeks)
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

## Phase 2: v2 Foundation (4 weeks)
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

## Phase 3: Incremental Migration (6-8 weeks)
**Goal:** Migrate safely without breaking production

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
- Week 1-2: Charts (least complex)
- Week 3-4: Client table
- Week 5-6: Fund table
- Week 7-8: Account table

### Rollout Strategy:
- Feature flag infrastructure (LaunchDarkly/custom)
- A/B testing: 10% → 50% → 100% rollout
- Parallel run of v1/v2

### Success Criteria:
- No increase in error rates
- Positive user feedback
- All components migrated

## Phase 4: Enhancement (4 weeks)
**Goal:** Optimize and enhance

### Features:
- Cursor pagination for large datasets
- Response compression (gzip/brotli)
- Cache warming strategies
- Consider WebSocket implementation (if metrics show need)
- Data windowing for time-series (aggregate older data)

### Success Criteria:
- 50% reduction in data transfer
- Sub-100ms p95 response times
- Improved user experience metrics

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
- **Chosen:** Normalized cache with RTK Query or React Query
- **Rationale:** Enables partial updates, optimistic updates, granular invalidation

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
- **Phase 1:** 2 weeks (Critical Fixes)
- **Phase 2:** 4 weeks (v2 Foundation)
- **Phase 3:** 6-8 weeks (Migration)
- **Phase 4:** 4 weeks (Enhancement)
- **Phase 5:** 2 weeks (Cleanup)

## Next Steps
1. Begin Phase 1 implementation immediately
2. Set up project tracking and communication channels
3. Schedule weekly progress reviews
4. Prepare stakeholder communications