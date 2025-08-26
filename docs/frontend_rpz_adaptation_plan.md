# Frontend RPZ Adaptation Plan

## Missing Frontend Features for Backend API Compatibility

### 1. **Enhanced API Service Methods**
The frontend API service is missing many endpoints that exist in the backend:

**Missing RPZ Endpoints:**
- `/rpz/statistics` - Comprehensive RPZ statistics
- `/rpz/blocked-queries` - Blocked query reports  
- `/rpz/threat-detection-report` - Threat detection analytics
- `/rpz/category-statistics` - Category-based statistics
- `/rpz/templates/*` - RPZ rule templates management
- `/rpz/rules/bulk-update` - Individual bulk updates
- `/rpz/rules/bulk-categorize` - Bulk categorization

**Missing Threat Feed Endpoints:**
- `/rpz/threat-feeds/{id}/test` - Test feed connectivity
- `/rpz/threat-feeds/{id}/toggle` - Toggle feed status
- `/rpz/threat-feeds/{id}/status` - Detailed feed status
- `/rpz/threat-feeds/{id}/update` - Manual feed update
- `/rpz/threat-feeds/schedule-updates` - Scheduled updates
- `/rpz/threat-feeds/statistics` - Feed statistics
- `/rpz/threat-feeds/custom` - Custom threat lists
- `/rpz/custom-lists/*` - Custom list management
- `/rpz/intelligence/*` - Threat intelligence endpoints

### 2. **Enhanced Type Definitions**
Current types are basic and missing many fields from backend schemas:

**Missing RPZ Rule Fields:**
- `source` - Rule source (manual, threat_feed, etc.)
- `description` - Rule description
- `created_at` / `updated_at` - Timestamps
- Enhanced validation and error handling

**Missing Threat Feed Fields:**
- `feed_type` - Type of threat feed
- `format_type` - Feed format (domains, hosts, etc.)
- `update_frequency` - Update interval in seconds
- `last_update_status` - Status of last update
- `last_update_error` - Error message if failed
- `rules_count` - Number of rules from this feed
- `is_active` - Active status

**Missing New Types:**
- `ThreatFeedStatus` - Detailed feed status
- `ThreatFeedUpdateResult` - Update operation results
- `RPZStatistics` - Comprehensive statistics
- `BlockedQueryReport` - Blocked query analytics
- `ThreatDetectionReport` - Threat detection analytics

### 3. **Enhanced Components Needed**

**RPZ Management:**
- Advanced rule filtering and search
- Category management interface
- Rule templates management
- Bulk operations with individual updates
- Import/export with validation
- Rule effectiveness analytics

**Threat Feed Management:**
- Feed health monitoring dashboard
- Custom threat list management
- Feed update scheduling interface
- Feed performance metrics
- Threat intelligence analytics

**Analytics & Reporting:**
- Comprehensive security dashboard
- Blocked query analytics
- Threat detection reports
- Category-based statistics
- Trend analysis charts
- Security impact reports

### 4. **WebSocket Event Handling**
Enhanced event types for real-time updates:
- `RPZ_RULE_CREATED` / `RPZ_RULE_UPDATED` / `RPZ_RULE_DELETED`
- `THREAT_FEED_UPDATED` / `THREAT_FEED_ERROR`
- `SECURITY_STATISTICS_UPDATED`
- `BLOCKED_QUERY_DETECTED`

## Implementation Priority

### Phase 1: Core API Adaptation (High Priority)
1. Update API service with missing endpoints
2. Enhance type definitions
3. Update existing components to use new fields
4. Add comprehensive error handling

### Phase 2: Enhanced UI Components (Medium Priority)
1. Advanced RPZ rule management
2. Threat feed health monitoring
3. Custom threat list management
4. Enhanced bulk operations

### Phase 3: Analytics & Reporting (Medium Priority)
1. Security analytics dashboard
2. Blocked query reports
3. Threat detection analytics
4. Performance metrics

### Phase 4: Advanced Features (Low Priority)
1. Rule templates system
2. Automated threat intelligence
3. Advanced filtering and search
4. Export/import enhancements

## Specific Files That Need Updates

### API Service (`frontend/src/services/api.ts`)
- Add missing RPZ endpoints
- Add threat feed management endpoints
- Add analytics and reporting endpoints
- Add custom threat list endpoints

### Types (`frontend/src/types/index.ts`)
- Enhance RPZRule interface
- Enhance ThreatFeed interface
- Add new analytics types
- Add bulk operation result types

### Components
- `Security.tsx` - Enhanced filtering and analytics
- `RPZRuleModal.tsx` - Support for new fields and validation
- `ThreatFeedManager.tsx` - Enhanced management features
- New: `ThreatIntelligenceDashboard.tsx`
- New: `SecurityAnalytics.tsx`
- New: `CustomThreatListManager.tsx`

### WebSocket Integration
- Update event types in `config/websocket.ts`
- Enhance event handlers in contexts
- Add real-time security monitoring