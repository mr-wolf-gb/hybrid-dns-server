# Installation Fix: SECRET_KEY Environment Variable Issue

## Problem
The installation was failing during the database initialization step with the error:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
SECRET_KEY
  Field required [type=missing, input_value={}, input_type=dict]
```

## Root Cause
The issue was caused by several Python modules importing and initializing settings at module import time, before the `.env` file was properly created during installation. This created a circular dependency where:

1. The installation script tries to initialize the database
2. Database initialization imports configuration modules
3. Configuration modules try to load settings immediately on import
4. Settings validation fails because SECRET_KEY is not yet available

## Solution
Modified the codebase to use **lazy loading** of settings and loggers instead of loading them at module import time.

### Files Modified

#### 1. `backend/app/core/logging_config.py`
- Removed module-level `settings = get_settings()`
- Modified `setup_logging()` to call `get_settings()` when needed

#### 2. `backend/app/core/database.py`
- Removed module-level settings and engine initialization
- Added `_initialize_database_engine()` function for lazy initialization
- Modified all database functions to initialize engine when first needed

#### 3. `backend/app/core/security.py`
- Removed module-level `settings = get_settings()` and `logger = get_security_logger()`
- Modified all functions to get settings and logger when needed

#### 4. `backend/app/services/monitoring_service.py`
- Removed module-level settings and logger initialization
- Modified all methods to get settings and logger when needed

#### 5. `backend/app/services/health_service.py`
- Removed module-level settings and logger initialization
- Modified all methods to get settings and logger when needed

#### 6. `backend/app/services/bind_service.py`
- Removed module-level settings and logger initialization
- Modified constructor and all methods to get settings and logger when needed

#### 7. `backend/app/api/endpoints/auth.py`
- Removed module-level settings and logger initialization

#### 8. `backend/main.py`
- Modified FastAPI app creation to use lazy loading
- Created `create_app()` and `setup_middleware()` functions

#### 9. `backend/init_db.py` (New File)
- Created standalone database initialization script
- Can be run independently without loading all application modules

#### 10. `install.sh`
- Modified database initialization step to use the new `init_db.py` script

## Benefits of This Fix

1. **Eliminates Import-Time Dependencies**: Settings are only loaded when actually needed
2. **Improves Installation Reliability**: Database initialization no longer fails due to missing environment variables
3. **Better Error Handling**: More granular control over when and how settings are loaded
4. **Maintains Functionality**: All existing functionality remains intact
5. **Performance**: Minimal impact on runtime performance

## Testing
Created `backend/test_config.py` to verify the fix works correctly without requiring full dependency installation.

## Installation Process
The installation should now complete successfully:
1. Environment file is created with proper SECRET_KEY
2. Database initialization runs without import errors
3. All services start normally

This fix ensures that the Hybrid DNS Server can be installed reliably on fresh systems without configuration-related import errors.