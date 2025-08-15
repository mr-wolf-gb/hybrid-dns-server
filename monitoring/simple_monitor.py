#!/usr/bin/env python3
"""
Simple DNS Query Monitoring Service
Basic monitoring without external dependencies
"""

import os
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDNSMonitor:
    def __init__(self):
        self.log_file = Path('/var/log/bind/queries.log')
        self.security_log = Path('/var/log/bind/security.log')
        self.monitoring_enabled = os.getenv('MONITORING_ENABLED', 'true').lower() == 'true'
        self.monitoring_interval = int(os.getenv('MONITORING_INTERVAL', '60'))
        
    def check_log_files(self):
        """Check if log files exist and are readable"""
        files_status = {}
        
        for log_file in [self.log_file, self.security_log]:
            if log_file.exists():
                try:
                    # Try to read the last few lines
                    with open(log_file, 'r') as f:
                        f.seek(0, 2)  # Go to end
                        size = f.tell()
                        files_status[str(log_file)] = {
                            'exists': True,
                            'readable': True,
                            'size': size
                        }
                except Exception as e:
                    files_status[str(log_file)] = {
                        'exists': True,
                        'readable': False,
                        'error': str(e)
                    }
            else:
                files_status[str(log_file)] = {
                    'exists': False,
                    'readable': False
                }
        
        return files_status
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting simple DNS monitoring service...")
        
        if not self.monitoring_enabled:
            logger.info("Monitoring is disabled, exiting...")
            return
        
        while True:
            try:
                # Check log files status
                status = self.check_log_files()
                
                for file_path, file_status in status.items():
                    if file_status['exists'] and file_status['readable']:
                        logger.info(f"Log file {file_path}: OK (size: {file_status['size']} bytes)")
                    elif file_status['exists']:
                        logger.warning(f"Log file {file_path}: exists but not readable - {file_status.get('error', 'unknown error')}")
                    else:
                        logger.warning(f"Log file {file_path}: does not exist")
                
                # Sleep for monitoring interval
                time.sleep(self.monitoring_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down DNS monitoring service...")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait before retrying

def main():
    """Main entry point"""
    monitor = SimpleDNSMonitor()
    monitor.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("DNS monitoring service stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)