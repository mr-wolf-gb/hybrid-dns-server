# Forwarders Components

This directory contains all the components related to DNS forwarder management in the Hybrid DNS Server frontend.

## Components

### ForwarderModal
The main modal for creating and editing DNS forwarders. Supports:
- Creating new forwarders with validation
- Editing existing forwarders
- Multiple DNS server configuration
- Type-specific domain suggestions and validation

### ForwarderTestModal
Advanced testing interface for DNS forwarders. Features:
- Configurable test parameters (domain, record type, timeout)
- Individual server testing results
- Response time monitoring
- Detailed error reporting
- Real-time test execution

### ForwarderHealthIndicator
Visual health status component that displays:
- Health status with appropriate icons and colors
- Response time information
- Last health check timestamp
- Active/inactive status
- Compact and detailed view modes

### ForwarderStatistics
Comprehensive statistics dashboard showing:
- Overview statistics (total, active, healthy forwarders)
- Performance metrics (average response time)
- Health status distribution with visual progress bars
- Forwarder type breakdown
- Last health check information

### ForwarderGrouping
Advanced grouping and viewing component that provides:
- Multiple grouping options (by type, status, health)
- Grid and list view modes
- Expandable/collapsible groups
- Interactive forwarder cards
- Bulk selection support

## Features Implemented

### Enhanced Health Indicators
- Real-time health status monitoring
- Color-coded status indicators
- Response time tracking
- Last check timestamps

### Comprehensive Testing UI
- Detailed forwarder testing with configurable parameters
- Individual server response monitoring
- Quick test and detailed test options
- Bulk testing capabilities

### Advanced Statistics Display
- Visual health distribution charts
- Performance metrics tracking
- Type-based categorization
- Real-time statistics updates

### Flexible Grouping System
- Multiple grouping criteria
- Grid and list view modes
- Interactive group management
- Bulk operations support

## Usage

```tsx
import {
  ForwarderModal,
  ForwarderTestModal,
  ForwarderHealthIndicator,
  ForwarderStatistics,
  ForwarderGrouping,
} from '@/components/forwarders'

// Use in your components
<ForwarderHealthIndicator forwarder={forwarder} showDetails />
<ForwarderStatistics forwarders={forwarders} />
<ForwarderGrouping 
  forwarders={forwarders}
  onForwarderSelect={handleSelect}
  onForwarderTest={handleTest}
/>
```

## API Integration

The components integrate with the enhanced forwarders API service that provides:
- Bulk testing operations
- Health status refresh
- Individual forwarder statistics
- Real-time health monitoring

## Styling

All components use Tailwind CSS with dark mode support and follow the application's design system for consistent styling and user experience.