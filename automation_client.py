import os
import requests
import logging
import json

# This module acts as a client to the Rust helper's REST API running on the user's machine
# It translates local automation calls to API requests to the local Rust helper service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The helper URL should be provided as an environment variable
# Default to local Rust helper URL (127.0.0.1:17400) if none provided
RUST_HELPER_URL = os.environ.get('AUTOMATION_SERVER_URL', 'http://127.0.0.1:17400')  # Using AUTOMATION_SERVER_URL for backward compatibility (should rename to RUST_HELPER_URL in future)

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
        self.server_url = server_url or RUST_HELPER_URL
        
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
            
        try:
            # First, try a simple status check
            response = requests.get(f"{self.server_url}/api/status", timeout=3)
            if response.status_code == 200:
                return True
                
            # Fallback to window list check
            response = requests.get(f"{self.server_url}/api/window/list", timeout=3)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to Rust helper: {e}")
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
            
        try:
            response = requests.post(
                f"{self.server_url}/api/mouse/move",
                json={'x': x, 'y': y},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def mouse_click(self, x, y, button='left', clicks=1):
        """Click at the specified position"""
        if not self.server_url:
            logger.warning("Cannot click mouse: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/mouse/click",
                json={'x': x, 'y': y, 'button': button, 'clicks': clicks},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to click mouse: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # Keyboard actions
    def keyboard_type(self, text):
        """Type the specified text"""
        if not self.server_url:
            logger.warning("Cannot type text: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/type",
                json={'text': text},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def keyboard_press(self, key):
        """Press a single key"""
        if not self.server_url:
            logger.warning("Cannot press key: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/press",
                json={'key': key},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def keyboard_hotkey(self, *keys):
        """Press a hotkey combination (multiple keys)"""
        if not self.server_url:
            logger.warning("Cannot press hotkey: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/hotkey",
                json={'keys': list(keys)},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to press hotkey: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # Window actions
    def get_window_list(self):
        """Get a list of all window titles"""
        if not self.server_url:
            logger.warning("Cannot get window list: No Rust helper URL")
            return []
            
        try:
            response = requests.get(
                f"{self.server_url}/api/window/list",
                timeout=3
            )
            result = self._handle_response(response)
            if result.get('status') == 'success' and 'windows' in result:
                return result['windows']
            return []
        except Exception as e:
            logger.error(f"Failed to get window list: {e}")
            return []
    
    def focus_window(self, title):
        """Focus a window by its title"""
        if not self.server_url:
            logger.warning("Cannot focus window: No Rust helper URL")
            return {'status': 'error', 'message': 'No Rust helper URL provided'}
            
        try:
            response = requests.post(
                f"{self.server_url}/api/window/focus",
                json={'title': title},
                timeout=3
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return {'status': 'error', 'message': str(e)}