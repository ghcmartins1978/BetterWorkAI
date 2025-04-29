import os
import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MonitorController:
    """
    Controls monitoring on the local helper (Rust or Python implementation)
    """
    
    def __init__(self, server_url=None):
        """Initialize the monitor controller for the helper"""
        # Force using the default URL to avoid the problematic environment variable
        if server_url:
            self.server_url = server_url
        else:
            # Use the mock helper port
            try:
                # Try to read from the port file
                mock_helper_port = '17403'  # Default fallback
                
                possible_paths = [
                    os.path.join(os.path.dirname(__file__), 'data', 'mock_helper_port.txt'),
                    os.path.join(os.path.dirname(__file__), '..', 'data', 'mock_helper_port.txt'),
                    os.path.join('data', 'mock_helper_port.txt'),
                    'mock_helper_port.txt'
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            port = f.read().strip()
                            if port:
                                mock_helper_port = port
                                logger.info(f"Found mock helper port in file: {port} (path: {path})")
                                break
                
                self.server_url = f'http://127.0.0.1:{mock_helper_port}'
            except Exception as e:
                logger.warning(f"Error reading mock helper port file, using default: {e}")
                self.server_url = 'http://127.0.0.1:17403'
        logger.info(f"Monitor controller initialized with helper URL: {self.server_url}")
    
    def is_connected(self):
        """Check if we can connect to the helper's REST API"""
        if not self.server_url:
            return False
            
        try:
            response = requests.get(f"{self.server_url}/api/status", timeout=3)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to helper: {e}")
            return False
    
    def get_status(self):
        """Get the current status of the monitoring"""
        if not self.server_url:
            return {'monitoring': False, 'error': 'No helper URL provided'}
            
        try:
            response = requests.get(f"{self.server_url}/api/status", timeout=3)
            if response.status_code == 200:
                return response.json()
            else:
                return {'monitoring': False, 'error': f'Status code: {response.status_code}'}
        except Exception as e:
            logger.error(f"Failed to get monitoring status: {e}")
            return {'monitoring': False, 'error': str(e)}
    
    def start_monitoring(self):
        """Start monitoring on the Rust helper"""
        if not self.server_url:
            return {'success': False, 'error': 'No Rust helper URL provided'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/monitoring", 
                json={'enable': True},
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                return {'success': data.get('monitoring', False), 'message': data.get('message', '')}
            else:
                return {'success': False, 'error': f'Status code: {response.status_code}'}
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_monitoring(self):
        """Stop monitoring on the Rust helper"""
        if not self.server_url:
            return {'success': False, 'error': 'No Rust helper URL provided'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/monitoring", 
                json={'enable': False},
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                return {'success': not data.get('monitoring', True), 'message': data.get('message', '')}
            else:
                return {'success': False, 'error': f'Status code: {response.status_code}'}
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_events(self, count=100, event_type=None):
        """Get events from the Rust helper"""
        if not self.server_url:
            return []
            
        try:
            params = {'count': count}
            if event_type:
                params['type'] = event_type
                
            response = requests.get(
                f"{self.server_url}/api/events",
                params=params,
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('events', [])
            else:
                logger.error(f"Failed to get events: Status code {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []