import os
import requests
import logging
import json

# This module acts as a client to a remote automation server running on the user's machine
# It translates local automation calls to API requests to the remote server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The ngrok URL should be provided as an environment variable
AUTOMATION_SERVER_URL = os.environ.get('AUTOMATION_SERVER_URL', '')

class AutomationClient:
    """
    Client for remote automation server. This allows the application to
    control mouse, keyboard, and window actions on the user's computer
    by sending requests to a Flask server running locally with ngrok tunnel.
    """
    
    def __init__(self, server_url=None):
        """
        Initialize the automation client
        
        Args:
            server_url: URL of the automation server (ngrok URL)
        """
        self.server_url = server_url or AUTOMATION_SERVER_URL
        
        if not self.server_url:
            logger.warning("No automation server URL provided. Remote automation will not work.")
        else:
            logger.info(f"Automation client initialized with server URL: {self.server_url}")
    
    def set_server_url(self, url):
        """Update the server URL"""
        self.server_url = url
        logger.info(f"Updated automation server URL to: {self.server_url}")
        return self.is_connected()
    
    def is_connected(self):
        """Check if the remote server is accessible"""
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
            logger.error(f"Failed to connect to automation server: {e}")
            return False
            
    def _handle_response(self, response):
        """Handle a response from the server, with proper error checking"""
        if response.status_code != 200:
            return {'status': 'error', 'message': f'Server returned status code {response.status_code}'}
            
        # Check if response is JSON
        try:
            # Try to parse as JSON first
            return response.json()
        except:
            # If not JSON, return the text with a success status
            return {'status': 'success', 'message': 'Command executed', 'response': response.text}
    
    # Mouse actions
    def mouse_move(self, x, y):
        """Move mouse to absolute position"""
        if not self.server_url:
            logger.warning("Cannot move mouse: No server URL")
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/mouse/move",
                json={'x': x, 'y': y},
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return False
    
    def mouse_click(self, x, y, button='left', clicks=1):
        """Click at the specified position"""
        if not self.server_url:
            logger.warning("Cannot click mouse: No server URL")
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/mouse/click",
                json={'x': x, 'y': y, 'button': button, 'clicks': clicks},
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to click mouse: {e}")
            return False
    
    # Keyboard actions
    def keyboard_type(self, text):
        """Type the specified text"""
        if not self.server_url:
            logger.warning("Cannot type text: No server URL")
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/type",
                json={'text': text},
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def keyboard_press(self, key):
        """Press a single key"""
        if not self.server_url:
            logger.warning("Cannot press key: No server URL")
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/press",
                json={'key': key},
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return False
    
    def keyboard_hotkey(self, *keys):
        """Press a hotkey combination (multiple keys)"""
        if not self.server_url:
            logger.warning("Cannot press hotkey: No server URL")
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/keyboard/hotkey",
                json={'keys': list(keys)},
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to press hotkey: {e}")
            return False
    
    # Window actions
    def get_window_list(self):
        """Get a list of all window titles"""
        if not self.server_url:
            logger.warning("Cannot get window list: No server URL")
            return []
            
        try:
            response = requests.get(
                f"{self.server_url}/api/window/list",
                timeout=3
            )
            if response.status_code == 200:
                return response.json().get('windows', [])
            return []
        except Exception as e:
            logger.error(f"Failed to get window list: {e}")
            return []
    
    def focus_window(self, title):
        """Focus a window by its title"""
        if not self.server_url:
            logger.warning("Cannot focus window: No server URL")
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/window/focus",
                json={'title': title},
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return False