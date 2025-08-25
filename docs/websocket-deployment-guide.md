# WebSocket System Deployment Guide

This guide covers the deployment, monitoring, and rollback procedures for the unified WebSocket system.

## Overview

The WebSocket system deployment uses feature flags to enable gradual rollout from the legacy multi-connection system to the new unified single-connection system. This approach minimizes risk and allows for quick rollback if issues are detected.

## Deployment Phases

### Phase 1: Testing Mode
Deploy to specific test users only.

```bash
cd backend
python deploy_websocket.py testing --test-users user1 user2 user3
```

**Characteristics:**
- Only specified users use the unified system
- All other users continue using legacy system
- Ideal for initial testing and validation

### Phase 2: Gradual Rollout
Gradually increase the percentage of users on the unified system.

```bash
# Start with 5% and increase by 5% every 30 minutes up to 50%
python deploy_websocket.py gradual --initial-percentage 5 --max-percentage 50 --step-size 5 --step-duration 30

# Continue to 100% with larger steps
python deploy_websocket.py gradual --initial-percentage 50 --max-percentage 100 --step-size 10 --step-duration 60
```

**Characteristics:**
- Automatic monitoring during each step
- Automatic rollback if error thresholds exceeded
- Configurable rollout speed and monitoring

### Phase 3: Full Deployment
All users use the unified system.

```bash
python deploy_websocket.py full
```

**Characteristics:**
- 100% of users on unified system
- Legacy system still available as fallback
- Complete migration achieved

## Environment Configuration

### Feature Flag Environment Variables

Add these to your `.env` file:

```bash
# WebSocket Feature Flags for Gradual Rollout
WEBSOCKET_UNIFIED_ENABLED=false
WEBSOCKET_GRADUAL_ROLLOUT_ENABLED=false
WEBSOCKET_ROLLOUT_PERCENTAGE=0
WEBSOCKET_ROLLOUT_USER_LIST=
WEBSOCKET_LEGACY_FALLBACK=true
WEBSOCKET_MIGRATION_MODE=disabled
WEBSOCKET_FORCE_LEGACY_USERS=
```

### Configuration Options

| Variable | Values | Description |
|----------|--------|-------------|
| `WEBSOCKET_MIGRATION_MODE` | `disabled`, `testing`, `gradual`, `full` | Current migration phase |
| `WEBSOCKET_ROLLOUT_PERCENTAGE` | `0-100` | Percentage of users on unified system |
| `WEBSOCKET_ROLLOUT_USER_LIST` | Comma-separated user IDs | Specific users for testing/rollout |
| `WEBSOCKET_FORCE_LEGACY_USERS` | Comma-separated user IDs | Users forced to use legacy system |
| `WEBSOCKET_LEGACY_FALLBACK` | `true`, `false` | Enable fallback to legacy on errors |

## Monitoring

### Automatic Monitoring

The deployment script includes automatic monitoring with configurable thresholds:

```bash
# Monitor deployment with custom thresholds
python monitor_websocket_deployment.py --duration 60 --max-error-rate 3.0 --consecutive-failures 2
```

### Monitoring Thresholds

| Threshold | Default | Description |
|-----------|---------|-------------|
| `max_error_rate` | 5.0% | Maximum error rate before rollback |
| `max_routing_errors` | 50 | Maximum routing errors in window |
| `max_fallback_rate` | 10.0% | Maximum fallback activation rate |
| `min_success_rate` | 95.0% | Minimum connection success rate |
| `consecutive_failures` | 3 | Consecutive failures before rollback |

### Manual Monitoring

Check deployment status at any time:

```bash
python deploy_websocket.py status
```

View detailed WebSocket statistics:

```bash
curl http://localhost:8000/api/websocket/stats
```

## Rollback Procedures

### Automatic Rollback

Automatic rollback is triggered when monitoring thresholds are exceeded during deployment. The system will:

1. Set migration mode to `disabled`
2. Clear user assignment cache
3. Update environment configuration
4. Log the rollback event

### Manual Emergency Rollback

For immediate rollback to legacy system:

```bash
python rollback_websocket.py emergency --reason "Production issue detected"
```

### Gradual Rollback

Reduce rollout percentage gradually:

```bash
# Reduce by 10% steps
python rollback_websocket.py gradual --step 10
```

### Rollback via Admin API

Use the admin API for controlled rollback:

```bash
# Emergency rollback
curl -X POST http://localhost:8000/api/websocket-admin/emergency-rollback \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Configure rollback
curl -X POST http://localhost:8000/api/websocket-admin/configure \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "migration_mode": "disabled",
    "rollout_percentage": 0,
    "legacy_fallback": true
  }'
```

## Troubleshooting

### Common Issues

#### High Error Rates
**Symptoms:** Routing errors, connection failures
**Solutions:**
1. Check server logs for specific errors
2. Verify WebSocket endpoint configuration
3. Test with small user group first
4. Consider gradual rollback

#### Memory Issues
**Symptoms:** High memory usage, connection drops
**Solutions:**
1. Monitor system resources
2. Check for connection leaks
3. Adjust connection limits
4. Consider immediate rollback

#### Authentication Problems
**Symptoms:** Authentication failures, token errors
**Solutions:**
1. Verify JWT configuration
2. Check token expiration settings
3. Test authentication flow
4. Review security logs

### Diagnostic Commands

```bash
# Check system status
python rollback_websocket.py status

# View connection statistics
curl http://localhost:8000/api/websocket/stats

# Get user-specific info
curl http://localhost:8000/api/websocket-admin/user/USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Check system health
curl http://localhost:8000/api/websocket-admin/health \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Best Practices

### Pre-Deployment

1. **Test thoroughly** in development environment
2. **Backup configuration** files
3. **Verify monitoring** systems are working
4. **Prepare rollback plan** and test procedures
5. **Communicate** with team about deployment window

### During Deployment

1. **Monitor continuously** during rollout
2. **Start with small percentages** (5-10%)
3. **Allow sufficient time** between steps
4. **Watch for error patterns** in logs
5. **Be prepared** to rollback quickly

### Post-Deployment

1. **Monitor for 24-48 hours** after full deployment
2. **Review performance metrics** and compare to baseline
3. **Collect user feedback** on WebSocket functionality
4. **Document lessons learned** for future deployments
5. **Plan legacy system removal** after stable period

## Deployment Checklist

### Pre-Deployment
- [ ] Development testing completed
- [ ] Staging environment validated
- [ ] Monitoring systems configured
- [ ] Rollback procedures tested
- [ ] Team notified of deployment window
- [ ] Backup of current configuration created

### Testing Phase
- [ ] Deploy to test users
- [ ] Verify unified WebSocket functionality
- [ ] Test subscription management
- [ ] Validate event filtering
- [ ] Check performance metrics
- [ ] Confirm fallback mechanisms work

### Gradual Rollout
- [ ] Start with low percentage (5-10%)
- [ ] Monitor for 30+ minutes per step
- [ ] Check error rates and performance
- [ ] Verify user experience
- [ ] Increase percentage gradually
- [ ] Document any issues encountered

### Full Deployment
- [ ] Complete rollout to 100%
- [ ] Monitor system stability
- [ ] Verify all features working
- [ ] Check resource utilization
- [ ] Confirm legacy fallback available
- [ ] Update documentation

### Post-Deployment
- [ ] Monitor for 24-48 hours
- [ ] Review performance metrics
- [ ] Collect user feedback
- [ ] Document lessons learned
- [ ] Plan legacy system deprecation
- [ ] Update operational procedures

## Emergency Contacts

During deployment, ensure these contacts are available:

- **System Administrator:** Primary contact for infrastructure issues
- **Development Team Lead:** Contact for application-level issues
- **Database Administrator:** Contact for database-related problems
- **Network Administrator:** Contact for network connectivity issues

## Monitoring Dashboard

Key metrics to monitor during deployment:

### Connection Metrics
- Total active connections
- Legacy vs unified connection distribution
- Connection establishment success rate
- Connection duration and stability

### Error Metrics
- Routing error count and rate
- Authentication failure rate
- Message delivery failure rate
- Fallback activation frequency

### Performance Metrics
- Message latency
- Memory usage per connection
- CPU utilization
- Network bandwidth usage

### Business Metrics
- User adoption rate
- Feature usage statistics
- User satisfaction indicators
- Support ticket volume

## Conclusion

The gradual rollout approach with comprehensive monitoring and automatic rollback capabilities provides a safe path to deploy the unified WebSocket system. Follow this guide carefully, monitor continuously, and be prepared to rollback if issues arise.

For additional support or questions, consult the development team or refer to the WebSocket system documentation.