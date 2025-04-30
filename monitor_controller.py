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
            # Use the Rust helper only
            try:
                # Default helper port (Rust helper)
                helper_port = '17400'  
                
                # Check for Rust helper port file first
                rust_helper_possible_paths = [
                    os.path.expanduser('~/AppData/Roaming/bettermanai/helper_port.txt'),
                    os.path.join(os.path.dirname(__file__), 'data', 'helper_port.txt'),
                    os.path.join('data', 'helper_port.txt'),
                    'helper_port.txt'
                ]
                
                # Try Rust helper paths
                for path in rust_helper_possible_paths:
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            port = f.read().strip()
                            if port:
                                helper_port = port
                                logger.info(f"Found Rust helper port in file: {port} (path: {path})")
                                break
                
                # Always use Rust helper port - no fallback to Python mock helper
                logger.info(f"Using helper port: {helper_port} (Rust helper)")
                
                self.server_url = f'http://127.0.0.1:{helper_port}'
            except Exception as e:
                logger.warning(f"Error reading helper port file, using default Rust helper port: {e}")
                self.server_url = 'http://127.0.0.1:17400'
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
            error_msg = str(e)
            if "Connection refused" in error_msg:
                logger.error(f"Failed to get monitoring status - Connection refused: Rust helper is not running or port {self.server_url.split(':')[-1]} is not accessible")
                return {'monitoring': False, 'connected': False, 'error': 'Helper connection refused'}
            elif "ConnectTimeout" in error_msg or "ReadTimeout" in error_msg:
                logger.error(f"Failed to get monitoring status - Connection timeout: Rust helper not responding in time")
                return {'monitoring': False, 'connected': False, 'error': 'Helper connection timeout'}
            else:
                logger.error(f"Failed to get monitoring status: {error_msg}")
                return {'monitoring': False, 'connected': False, 'error': error_msg}
    
    def start_monitoring(self):
        """Start monitoring on the helper"""
        if not self.server_url:
            return {'success': False, 'error': 'No helper URL provided'}
            
        try:
            # First try the most specific endpoint - Rust helper has both
            # Try with action parameter for general endpoint
            try:
                response = requests.post(
                    f"{self.server_url}/api/monitoring", 
                    json={'action': 'start'},
                    timeout=3
                )
                if response.status_code == 200:
                    data = response.json()
                    return {'success': True, 'message': data.get('message', 'Monitoring started')}
            except Exception as e:
                logger.warning(f"Failed with general endpoint, trying specific endpoint: {e}")
                
            # If that fails, try the specific endpoint
            response = requests.post(
                f"{self.server_url}/api/monitoring/start",
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'message': data.get('message', 'Monitoring started')}
            else:
                return {'success': False, 'error': f'Status code: {response.status_code}'}
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                logger.error(f"Failed to start monitoring - Connection refused: Rust helper is not running or port {self.server_url.split(':')[-1]} is not accessible")
                return {'success': False, 'error': 'Helper connection refused. Please check if the Rust helper is running.'}
            elif "ConnectTimeout" in error_msg or "ReadTimeout" in error_msg:
                logger.error(f"Failed to start monitoring - Connection timeout: Rust helper not responding in time")
                return {'success': False, 'error': 'Helper connection timeout. The helper may be busy or unresponsive.'}
            else:
                logger.error(f"Failed to start monitoring: {error_msg}")
                return {'success': False, 'error': error_msg}
    
    def stop_monitoring(self):
        """Stop monitoring on the helper"""
        if not self.server_url:
            return {'success': False, 'error': 'No helper URL provided'}
            
        try:
            # First try the most specific endpoint - Rust helper has both
            # Try with action parameter for general endpoint
            try:
                response = requests.post(
                    f"{self.server_url}/api/monitoring", 
                    json={'action': 'stop'},
                    timeout=3
                )
                if response.status_code == 200:
                    data = response.json()
                    return {'success': True, 'message': data.get('message', 'Monitoring stopped')}
            except Exception as e:
                logger.warning(f"Failed with general endpoint, trying specific endpoint: {e}")
                
            # If that fails, try the specific endpoint
            response = requests.post(
                f"{self.server_url}/api/monitoring/stop",
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'message': data.get('message', 'Monitoring stopped')}
            else:
                return {'success': False, 'error': f'Status code: {response.status_code}'}
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                logger.error(f"Failed to stop monitoring - Connection refused: Rust helper is not running or port {self.server_url.split(':')[-1]} is not accessible")
                return {'success': False, 'error': 'Helper connection refused. Please check if the Rust helper is running.'}
            elif "ConnectTimeout" in error_msg or "ReadTimeout" in error_msg:
                logger.error(f"Failed to stop monitoring - Connection timeout: Rust helper not responding in time")
                return {'success': False, 'error': 'Helper connection timeout. The helper may be busy or unresponsive.'}
            else:
                logger.error(f"Failed to stop monitoring: {error_msg}")
                return {'success': False, 'error': error_msg}
    
    def get_events(self, count=100, event_type=None):
        """Get events from the helper"""
        if not self.server_url:
            return []
            
        try:
            params = {'count': count}
            if event_type:
                params['type'] = event_type
                
            # Debug: Log full details about the request
            logger.info(f"Requesting events from: {self.server_url}/api/events with params: {params}")
                
            response = requests.get(
                f"{self.server_url}/api/events",
                params=params,
                timeout=3
            )
            
            # Debug: Log full response details
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Debug: Log raw response data
                logger.info(f"Response data: {data}")
                
                events = data.get('events', [])
                
                # Log the number of events retrieved
                logger.info(f"Retrieved {len(events)} events from helper")
                
                # If we got a response but no events, check if monitoring is active
                if len(events) == 0:
                    status = self.get_status()
                    logger.info(f"Helper status: {status}")
                    
                    if status.get('monitoring', False):
                        logger.info("Monitoring is active but no events received yet. This is normal if monitoring just started.")
                        # Debug: Check helper privacy settings
                        logger.info(f"Checking helper privacy settings - Mouse tracking: {status.get('mouse_tracking', 'unknown')}, Keyboard tracking: {status.get('keyboard_tracking', 'unknown')}, Window tracking: {status.get('window_tracking', 'unknown')}")
                    else:
                        logger.warning("No events received and monitoring is not active. Try starting monitoring.")
                        
                return events
            else:
                # Debug: Try to get error message from response body
                try:
                    error_body = response.json()
                    logger.error(f"Failed to get events: Status code {response.status_code}, details: {error_body}")
                except:
                    logger.error(f"Failed to get events: Status code {response.status_code}")
                return []
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                logger.error(f"Failed to get events - Connection refused: Rust helper is not running or port {self.server_url.split(':')[-1]} is not accessible")
            elif "ConnectTimeout" in error_msg or "ReadTimeout" in error_msg:
                logger.error(f"Failed to get events - Connection timeout: Rust helper not responding in time")
            else:
                logger.error(f"Failed to get events: {error_msg}")
            return []
            
    def get_privacy_settings(self):
        """Get the privacy settings from the helper"""
        if not self.server_url:
            return {}
            
        try:
            # Try to get privacy settings endpoint if it exists
            response = requests.get(
                f"{self.server_url}/api/settings/privacy",
                timeout=3
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to status if privacy endpoint doesn't exist
                status_response = requests.get(
                    f"{self.server_url}/api/status",
                    timeout=3
                )
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    # Extract privacy-related fields if they exist
                    privacy_settings = {
                        'mouse_tracking': status_data.get('mouse_tracking', True),
                        'keyboard_tracking': status_data.get('keyboard_tracking', True),
                        'window_tracking': status_data.get('window_tracking', True)
                    }
                    return privacy_settings
                else:
                    logger.error(f"Failed to get privacy settings or status: Status code {status_response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"Failed to get privacy settings: {e}")
            return {}
            
    def test_event_generation(self):
        """Test event generation through the helper API if supported"""
        if not self.server_url:
            return {'success': False, 'error': 'No helper URL provided'}
            
        try:
            # Try to use test event generation endpoint if available
            response = requests.post(
                f"{self.server_url}/api/test/event",
                json={
                    'type': 'mouse_move', 
                    'x': 100, 
                    'y': 100
                },
                timeout=3
            )
            
            if response.status_code == 200:
                logger.info("Successfully generated test event")
                return {'success': True, 'message': 'Test event generated'}
            else:
                logger.warning(f"Helper does not support test event generation: Status code {response.status_code}")
                return {
                    'success': False, 
                    'error': 'Test event generation not supported by this helper'
                }
        except Exception as e:
            logger.error(f"Failed to generate test event: {e}")
            return {'success': False, 'error': str(e)}