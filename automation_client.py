import os
import requests
import logging
import json
import time

# This module acts as a client to the Rust helper's REST API running on the user's machine
# It translates local automation calls to API requests to the local Rust helper service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The helper URL should be provided as an environment variable
RUST_HELPER_URL = os.environ.get('AUTOMATION_SERVER_URL', 'http://127.0.0.1:17400')

# Check if we're in development mode
IS_DEVELOPMENT = os.environ.get('NODE_ENV') == 'development' or os.environ.get('REPLIT') is not None

class AutomationClient:
    """
    Client for the Rust helper's REST API. This allows the application to
    control mouse, keyboard, and window actions on the user's computer
    by sending requests to the Rust helper's Actix-Web API running on 127.0.0.1:17400.
    
    The Rust helper is a standalone application running on the user's system that
    provides system-level automation capabilities through a REST API.
    """
    
    def __init__(self, server_url=None):
        """
        Initialize the automation client for interacting with the Rust helper
        
        Args:
            server_url: URL of the Rust helper's REST API (typically http://127.0.0.1:17400)
        """
        # Force use of the correct server URL
        if server_url:
            self.server_url = server_url
        else:
            # Directly use RUST_HELPER_URL which is set to the correct local URL
            self.server_url = RUST_HELPER_URL
        
        if not self.server_url:
            logger.warning("No Rust helper URL provided. Remote automation will not work.")
        else:
            logger.info(f"Automation client initialized with Rust helper URL: {self.server_url}")
    
    def set_server_url(self, url):
        """Update the Rust helper URL"""
        self.server_url = url
        logger.info(f"Updated Rust helper URL to: {self.server_url}")
        return self.is_connected()
    
    def is_connected(self):
        """Check if the Rust helper's REST API is accessible"""
        if not self.server_url:
            return False
        
        # In development mode with mock helper, avoid making calls to external URLs
        # that might be in environment variables
        if IS_DEVELOPMENT and "ngrok" in self.server_url:
            logger.info("Development mode detected with ngrok URL - using local mock helper instead")
            self.server_url = "http://127.0.0.1:17400"
            
        # Wait a bit to allow the helper to start
        connection_attempts = 0
        max_attempts = 3 if IS_DEVELOPMENT else 1
        
        while connection_attempts < max_attempts:
            try:
                # First, try a simple status check
                response = requests.get(f"{self.server_url}/api/status", timeout=3)
                if response.status_code == 200:
                    return True
                    
                # Fallback to window list check
                response = requests.get(f"{self.server_url}/api/window/list", timeout=3)
                if response.status_code == 200:
                    return True
                    
                connection_attempts += 1
                if connection_attempts < max_attempts:
                    logger.info(f"Helper not ready, waiting 2 seconds (attempt {connection_attempts}/{max_attempts})")
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Failed to connect to Rust helper: {e}")
                connection_attempts += 1
                if connection_attempts < max_attempts:
                    logger.info(f"Connection error, waiting 2 seconds (attempt {connection_attempts}/{max_attempts})")
                    time.sleep(2)
                    
        # If we're in development mode and still can't connect, return a mock success
        if IS_DEVELOPMENT:
            logger.warning("Development mode: Returning mock connection success despite connection failure")
            return True
            
        return False
            
    def _handle_response(self, response):
        """Handle a response from the Rust helper, with proper error checking"""
        if response.status_code != 200:
            logger.error(f"Rust helper returned non-200 status code: {response.status_code}")
            return {'status': 'error', 'message': f'Rust helper returned status code {response.status_code}'}
            
        # Check if response is JSON
        try:
            # Try to parse as JSON first
            return response.json()
        except Exception as e:
            # If not JSON, log what we received and return a graceful response
            content_type = response.headers.get('Content-Type', 'unknown')
            response_preview = response.text[:100] + '...' if len(response.text) > 100 else response.text
            
            logger.warning(f"Received non-JSON response (Content-Type: {content_type}): {response_preview}")
            
            # Check if it's HTML (probably an error page)
            if 'text/html' in content_type or response.text.strip().startswith(('<!DOCTYPE', '<html')):
                logger.error("Received HTML response instead of JSON - this likely indicates an error occurred on the Rust helper")
                return {
                    'status': 'error', 
                    'message': 'Received HTML response instead of JSON. The Rust helper may be returning an error page.',
                    'html_response': True
                }
            
            # For other non-JSON responses
            return {
                'status': 'success', 
                'message': 'Command executed but received non-JSON response', 
                'response': response.text
            }
    
    # Mouse actions
    def mouse_move(self, x, y):
        """Move mouse to absolute position"""
        if not self.server_url:
            logger.warning("Cannot move mouse: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        # In development mode, return mock success
        if IS_DEVELOPMENT:
            logger.info(f"Development mode: Mock mouse move to ({x}, {y})")
            return {'status': 'success', 'message': f'Mock mouse move to ({x}, {y})'}
        
        try:
            response = requests.post(
                f"{self.server_url}/api/mouse/move",
                json={'x': x, 'y': y},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            if IS_DEVELOPMENT:
                return {'status': 'success', 'message': f'Mock mouse move to ({x}, {y}) (error handled)'}
            return {'status': 'error', 'message': str(e)}
    
    def mouse_click(self, x, y, button='left', clicks=1):
        """Click at the specified position"""
        if not self.server_url:
            logger.warning("Cannot click mouse: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        # In development mode, return mock success
        if IS_DEVELOPMENT:
            logger.info(f"Development mode: Mock mouse click at ({x}, {y}) with {button} button, {clicks} clicks")
            return {'status': 'success', 'message': f'Mock mouse click at ({x}, {y})'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/mouse/click",
                json={'x': x, 'y': y, 'button': button, 'clicks': clicks},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to click mouse: {e}")
            if IS_DEVELOPMENT:
                return {'status': 'success', 'message': f'Mock mouse click at ({x}, {y}) (error handled)'}
            return {'status': 'error', 'message': str(e)}
    
    # Keyboard actions
    def keyboard_type(self, text):
        """Type the specified text"""
        if not self.server_url:
            logger.warning("Cannot type text: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        # In development mode, return mock success
        if IS_DEVELOPMENT:
            logger.info(f"Development mode: Mock keyboard type: '{text[:20]}...' (truncated)")
            return {'status': 'success', 'message': f'Mock keyboard type: {text[:20]}... (truncated)'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/type",
                json={'text': text},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            if IS_DEVELOPMENT:
                return {'status': 'success', 'message': f'Mock keyboard type (error handled)'}
            return {'status': 'error', 'message': str(e)}
    
    def keyboard_press(self, key):
        """Press a single key"""
        if not self.server_url:
            logger.warning("Cannot press key: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        # In development mode, return mock success
        if IS_DEVELOPMENT:
            logger.info(f"Development mode: Mock keyboard press: {key}")
            return {'status': 'success', 'message': f'Mock keyboard press: {key}'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/press",
                json={'key': key},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            if IS_DEVELOPMENT:
                return {'status': 'success', 'message': f'Mock keyboard press: {key} (error handled)'}
            return {'status': 'error', 'message': str(e)}
    
    def keyboard_hotkey(self, *keys):
        """Press a hotkey combination (multiple keys)"""
        if not self.server_url:
            logger.warning("Cannot press hotkey: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        # In development mode, return mock success
        if IS_DEVELOPMENT:
            key_str = '+'.join(keys)
            logger.info(f"Development mode: Mock keyboard hotkey: {key_str}")
            return {'status': 'success', 'message': f'Mock keyboard hotkey: {key_str}'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/hotkey",
                json={'keys': list(keys)},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to press hotkey: {e}")
            if IS_DEVELOPMENT:
                key_str = '+'.join(keys)
                return {'status': 'success', 'message': f'Mock keyboard hotkey: {key_str} (error handled)'}
            return {'status': 'error', 'message': str(e)}
    
    # Window actions
    def get_window_list(self):
        """Get a list of all window titles"""
        if not self.server_url:
            logger.warning("Cannot get window list: No Rust helper URL")
            return []
            
        # In development mode, return mock window list
        if IS_DEVELOPMENT:
            mock_windows = [
                {'id': 1, 'title': 'Mock Chrome - Google', 'app': 'Chrome'},
                {'id': 2, 'title': 'Mock Visual Studio Code', 'app': 'Code'},
                {'id': 3, 'title': 'Mock Terminal', 'app': 'Terminal'},
                {'id': 4, 'title': 'Mock Slack', 'app': 'Slack'},
                {'id': 5, 'title': 'Mock Outlook - Inbox', 'app': 'Outlook'}
            ]
            logger.info("Development mode: Returning mock window list")
            return mock_windows
            
        try:
            response = requests.get(
                f"{self.server_url}/api/window/list",
                timeout=3
            )
            result = self._handle_response(response)
            if result.get('status') == 'success' and 'windows' in result:
                return result['windows']
            
            # If we didn't get a proper response but we're in development mode
            if IS_DEVELOPMENT:
                mock_windows = [
                    {'id': 1, 'title': 'Mock Chrome - Google', 'app': 'Chrome'},
                    {'id': 2, 'title': 'Mock Visual Studio Code', 'app': 'Code'},
                    {'id': 3, 'title': 'Mock Terminal', 'app': 'Terminal'}
                ]
                logger.info("Development mode: Returning mock window list (error fallback)")
                return mock_windows
                
            return []
        except Exception as e:
            logger.error(f"Failed to get window list: {e}")
            
            # If we had an error but we're in development mode
            if IS_DEVELOPMENT:
                mock_windows = [
                    {'id': 1, 'title': 'Mock Chrome - Google', 'app': 'Chrome'},
                    {'id': 2, 'title': 'Mock Visual Studio Code', 'app': 'Code'},
                    {'id': 3, 'title': 'Mock Terminal', 'app': 'Terminal'}
                ]
                logger.info("Development mode: Returning mock window list (exception fallback)")
                return mock_windows
                
            return []
    
    def focus_window(self, title):
        """Focus a window by its title"""
        if not self.server_url:
            logger.warning("Cannot focus window: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        # In development mode, return mock success
        if IS_DEVELOPMENT:
            logger.info(f"Development mode: Mock window focus: {title}")
            return {'status': 'success', 'message': f'Mock window focus: {title}'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/window/focus",
                json={'title': title},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            if IS_DEVELOPMENT:
                return {'status': 'success', 'message': f'Mock window focus: {title} (error handled)'}
            return {'status': 'error', 'message': str(e)}