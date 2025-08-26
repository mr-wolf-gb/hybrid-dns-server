# Notification Filtering System

## Overview

The notification filtering system allows users to control which notifications they see based on severity levels and event categories. This helps reduce notification fatigue by filtering out less important events like routine health updates.

## Features

### Severity Filtering
Users can choose which severity levels to show:
- **Debug**: Detailed debugging information
- **Info**: General information messages  
- **Warning**: Warning conditions that need attention
- **Error**: Error conditions that require action
- **Critical**: Critical conditions requiring immediate attention

### Category Filtering
Users can filter by event categories:
- **Health Updates**: System health checks and forwarder status (often disabled by default)
- **DNS Events**: Zone and record changes
- **Security Events**: Security alerts and threat detection
- **System Events**: System configuration and service changes

### Advanced Settings
- **Throttle Duration**: Minimum time between similar notifications (1-60 seconds)
- **Max Notifications Per Minute**: Rate limiting to prevent notification spam (1-50 per minute)

## Usage

### Accessing Settings
1. Click the notification bell icon in the top navigation
2. Click the settings gear icon in the notification panel
3. Or navigate to Settings → Notifications tab

### Configuring Filters
1. **Severity Levels**: Click on severity cards to enable/disable them
2. **Event Categories**: Toggle categories on/off based on your needs
3. **Advanced Settings**: Use sliders to adjust throttling and rate limits
4. Click "Save Preferences" to apply changes

### Real-time Updates
- Changes apply immediately to new notifications
- Existing notifications in the panel are filtered based on new preferences
- Notification badge count updates to reflect filtered count
- WebSocket notifications respect the new settings

## Default Settings

By default, the system is configured to:
- Show Warning, Error, and Critical severity levels
- Show DNS, Security, and System events
- Hide routine Health Updates
- Use 5-second throttling
- Allow up to 10 notifications per minute

## Technical Implementation

### Frontend
- `NotificationSettings.tsx`: Settings UI component
- `useNotificationPreferences.ts`: React hook for preference management
- `RealTimeNotifications.tsx`: Updated to respect filtering preferences
- WebSocket contexts updated to filter toast notifications

### Backend
- `users.py`: API endpoints for preference storage
- User model extended with metadata JSON column
- Preferences stored in user.metadata.notification_preferences

### Storage
User preferences are stored in the database as JSON in the user's metadata field:

```json
{
  "notification_preferences": {
    "enabled_severities": ["warning", "error", "critical"],
    "enabled_categories": ["dns", "security", "system"],
    "show_health_updates": false,
    "show_system_events": true,
    "show_dns_events": true,
    "show_security_events": true,
    "throttle_duration": 5000,
    "max_notifications_per_minute": 10
  }
}
```

## Benefits

1. **Reduced Noise**: Filter out routine health updates and debug messages
2. **Focus on Important Events**: Prioritize warnings, errors, and critical alerts
3. **Customizable**: Each user can set their own preferences
4. **Real-time**: Changes apply immediately without page refresh
5. **Persistent**: Settings are saved per user and persist across sessions

## Example Use Cases

### System Administrator
- Enable all severity levels and categories
- Lower throttle duration for faster notifications
- Higher notification rate limit

### Regular User
- Disable debug and info levels
- Hide health updates
- Focus on DNS and security events only

### Security Team
- Enable all severity levels
- Focus on security and system events
- Disable routine DNS events