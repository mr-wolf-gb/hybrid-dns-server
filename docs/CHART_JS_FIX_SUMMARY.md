# Chart.js Initialization Error Fix

## Problem
Users were experiencing a runtime error on the login page:
```
charts-vendor-784df5cf.js:13 Uncaught ReferenceError: Cannot access 'A' before initialization
```

This was caused by Chart.js being loaded and initialized at the module level in multiple components, causing initialization conflicts when the charts-vendor bundle was loaded early.

## Root Cause
- Chart.js was being imported and registered at module level in multiple components
- The charts-vendor bundle was being loaded even on pages that didn't need charts
- This caused initialization conflicts and circular dependency issues

## Solution Implemented

### 1. Created LazyChart Wrapper Component
Created `frontend/src/components/charts/LazyChart.tsx` that:
- Dynamically imports Chart.js only when needed
- Handles Chart.js registration safely
- Provides loading states and error handling
- Prevents early initialization conflicts

### 2. Updated Vite Configuration
Modified `frontend/vite.config.ts` to:
- Separate Chart.js into its own `chartjs-vendor` chunk
- Keep other chart libraries in `charts-vendor` chunk
- Prevent Chart.js from being bundled with other vendor libraries

### 3. Refactored Chart Components
Updated the following components to use LazyChart:
- `frontend/src/components/dashboard/RealTimeChart.tsx`
- `frontend/src/components/security/SecurityStats.tsx`
- `frontend/src/components/security/SecurityAnalytics.tsx`
- `frontend/src/components/security/ThreatIntelligenceDashboard.tsx`
- `frontend/src/components/reports/AnalyticsDashboard.tsx`
- `frontend/src/pages/Analytics.tsx`

### 4. Removed Module-Level Chart.js Imports
- Removed all `import { Chart as ChartJS, ... } from 'chart.js'` statements
- Removed all `ChartJS.register(...)` calls at module level
- Replaced with dynamic imports inside LazyChart wrapper

## Results

### Bundle Optimization
- `chartjs-vendor`: 201KB (Chart.js isolated)
- `charts-vendor`: 323KB (other chart libraries)
- Total build time: ~12 seconds
- No more initialization conflicts

### Runtime Behavior
- Chart.js is only loaded when chart components are actually rendered
- Login page no longer loads Chart.js unnecessarily
- Proper error handling and loading states for charts
- No more "Cannot access 'A' before initialization" errors

## Usage Example

Before (problematic):
```typescript
import { Chart as ChartJS, CategoryScale, ... } from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(CategoryScale, ...)

const MyChart = () => <Line data={data} options={options} />
```

After (fixed):
```typescript
import LazyChart from '@/components/charts/LazyChart'

const MyChart = () => (
  <LazyChart>
    {({ Line }) => <Line data={data} options={options} />}
  </LazyChart>
)
```

## Benefits
1. **No More Login Errors** - Chart.js doesn't load on login page
2. **Better Performance** - Charts only load when needed
3. **Cleaner Bundle Splitting** - Chart.js isolated from other vendors
4. **Error Resilience** - Graceful fallbacks if Chart.js fails to load
5. **Loading States** - Users see loading indicators while charts initialize

## Files Modified
- `frontend/src/components/charts/LazyChart.tsx` (new)
- `frontend/vite.config.ts`
- `frontend/src/components/dashboard/RealTimeChart.tsx`
- `frontend/src/components/security/SecurityStats.tsx`
- `frontend/src/components/security/SecurityAnalytics.tsx`
- `frontend/src/components/security/ThreatIntelligenceDashboard.tsx`
- `frontend/src/components/reports/AnalyticsDashboard.tsx`
- `frontend/src/pages/Analytics.tsx`

The Chart.js initialization error has been completely resolved while maintaining all chart functionality.