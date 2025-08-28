# Development Workflow & Remote Server Operations

## Direct Codebase Modifications

**CRITICAL**: When making changes to fix issues or implement features:

- **DO NOT create separate fix files** or temporary files
- **ALWAYS modify the existing codebase directly** using the appropriate file modification tools
- Make changes directly to the actual source files in their proper locations
- Use `strReplace` for targeted edits, `fsWrite` for new files, and `fsAppend` for additions
- Ensure all changes are made to the production codebase, not examples or temporary files

## Remote Server Testing

**IMPORTANT**: All Linux commands and server operations are executed on a remote server:

- **DO NOT attempt to run Linux commands directly** - they will fail on this Windows environment
- **ALWAYS provide the exact commands** you want to run and ask the user to execute them on the remote server
- **Wait for the user to provide the results** before proceeding with next steps
- **Format commands clearly** with proper syntax for copy-paste execution

### Command Request Format

When you need to run commands on the remote server, format them like this:

```bash
# Please run these commands on your remote server:
cd /path/to/project
sudo systemctl status service-name
tail -f /var/log/application.log
```

Then wait for the user to provide the output before continuing.

### Common Remote Operations

- **Service Management**: `systemctl start/stop/restart/status service-name`
- **Log Checking**: `tail -f /var/log/path/to/log`, `journalctl -u service-name -f`
- **File Operations**: `ls -la`, `cat filename`, `chmod +x script.sh`
- **Process Monitoring**: `ps aux | grep process-name`, `htop`, `netstat -tlnp`
- **Docker Operations**: `docker ps`, `docker logs container-name`, `docker-compose up -d`

## Testing Workflow

1. **Make code changes** directly to the codebase files
2. **Provide specific commands** for the user to run on remote server
3. **Wait for results** and analyze output
4. **Iterate based on feedback** from remote server execution
5. **Continue until issue is resolved** or feature is working

## File Modification Priorities

1. **Direct source file editing** - Always modify the actual files
2. **Configuration updates** - Update real config files, not examples
3. **Service file changes** - Modify actual systemd services, scripts, etc.
4. **Database migrations** - Create real migration files when needed
5. **Template updates** - Modify actual Jinja2 templates in use

## Error Handling Approach

- **Analyze error output** provided by user from remote server
- **Make targeted fixes** to the actual codebase
- **Provide specific diagnostic commands** for the user to run
- **Iterate quickly** based on real server feedback
- **Document solutions** in code comments when appropriate

## Communication Pattern

1. **Analyze the issue** based on current codebase
2. **Make necessary code changes** directly to source files
3. **Provide clear commands** for remote server execution
4. **Request specific output** or confirmation from user
5. **Continue troubleshooting** based on real server results

This workflow ensures efficient development with real server feedback while maintaining direct codebase modifications.