"""
Browser context enrichment module for BettermanAI.
Captures the current browser URL, tab title, and domain via Chrome DevTools Protocol.
"""
import json
import logging
import os
import platform
import socket
import subprocess
import time
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class BrowserContextEnricher:
    """
    Class to capture browser context information.
    Uses Chrome DevTools Protocol (CDP) to retrieve information from Chromium-based browsers.
    """
    
    def __init__(self):
        """Initialize the browser context enricher."""
        self.system = platform.system()
        self.ws_connection = None
        self.connected = False
        
    def _find_chrome_debugging_port(self) -> Optional[int]:
        """
        Find a Chrome instance running with remote debugging enabled.
        
        Returns:
            Port number if found, None otherwise
        """
        # Default debugging ports to check
        ports_to_check = [9222, 9223, 9224, 9225]
        
        for port in ports_to_check:
            try:
                # Try to connect to the debugging port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result == 0:
                    # Port is open, check if it's actually Chrome DevTools
                    try:
                        # HTTP request to the API
                        import requests
                        response = requests.get(f'http://localhost:{port}/json/version', timeout=1)
                        if response.status_code == 200 and 'Chrome' in response.text:
                            logger.info(f"Found Chrome debugging on port {port}")
                            return port
                    except Exception as e:
                        logger.debug(f"Error checking Chrome on port {port}: {e}")
            except Exception as e:
                logger.debug(f"Error checking port {port}: {e}")
                
        return None
    
    def _get_tab_list(self, port: int) -> List[Dict]:
        """
        Get the list of tabs from Chrome's DevTools API.
        
        Args:
            port: The debugging port number
            
        Returns:
            List of tab data dictionaries
        """
        try:
            import requests
            response = requests.get(f'http://localhost:{port}/json/list', timeout=1)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get tab list: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting tab list: {e}")
            return []
    
    def _connect_to_active_tab(self, port: int) -> bool:
        """
        Connect to the active tab in Chrome via DevTools Protocol.
        
        Args:
            port: The debugging port number
            
        Returns:
            True if connection was successful, False otherwise
        """
        import websocket
        
        tabs = self._get_tab_list(port)
        if not tabs:
            return False
            
        # Find the active tab
        active_tab = None
        for tab in tabs:
            if tab.get('type') == 'page' and tab.get('webSocketDebuggerUrl'):
                active_tab = tab
                break
                
        if not active_tab:
            logger.warning("No suitable active tab found")
            return False
            
        # Connect to the WebSocket
        try:
            ws_url = active_tab['webSocketDebuggerUrl']
            self.ws_connection = websocket.create_connection(ws_url)
            self.connected = True
            logger.info(f"Connected to tab: {active_tab.get('title', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            self.connected = False
            return False
    
    def _send_command(self, method: str, params: Dict = None) -> Optional[Dict]:
        """
        Send a command to Chrome via the DevTools Protocol.
        
        Args:
            method: The CDP method to call
            params: Method parameters (optional)
            
        Returns:
            Response data or None if failed
        """
        if not self.connected or not self.ws_connection:
            logger.warning("Not connected to Chrome DevTools")
            return None
            
        command = {
            'id': 1,
            'method': method
        }
        
        if params:
            command['params'] = params
            
        try:
            self.ws_connection.send(json.dumps(command))
            response = json.loads(self.ws_connection.recv())
            return response.get('result')
        except Exception as e:
            logger.error(f"Error sending command to Chrome: {e}")
            self.connected = False
            return None
    
    def get_browser_context(self) -> Dict[str, str]:
        """
        Get the current browser context (URL, title, domain).
        
        Returns:
            Dictionary containing browser context information
        """
        context = {
            'browser_url': '',
            'browser_title': '',
            'browser_domain': ''
        }
        
        # Try to find Chrome with debugging enabled
        port = self._find_chrome_debugging_port()
        if not port:
            logger.info("No Chrome instance with debugging found")
            return context
            
        # Connect to the active tab
        if not self._connect_to_active_tab(port):
            return context
            
        # Get the current URL and title
        try:
            result = self._send_command('Page.getNavigationHistory')
            if result and 'entries' in result:
                current_entry = result['entries'][result.get('currentIndex', 0)]
                url = current_entry.get('url', '')
                title = current_entry.get('title', '')
                
                # Extract domain from URL
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                context['browser_url'] = url
                context['browser_title'] = title
                context['browser_domain'] = domain
                
                logger.info(f"Retrieved browser context: {domain} - {title}")
        except Exception as e:
            logger.error(f"Error getting navigation history: {e}")
            
        # Close the connection
        try:
            if self.ws_connection:
                self.ws_connection.close()
                self.connected = False
        except Exception as e:
            logger.error(f"Error closing WebSocket connection: {e}")
            
        return context
    
    def get_context_via_applescript(self) -> Dict[str, str]:
        """
        Get browser context using AppleScript (macOS only).
        
        Returns:
            Dictionary containing browser context information
        """
        context = {
            'browser_url': '',
            'browser_title': '',
            'browser_domain': ''
        }
        
        if self.system != 'Darwin':
            logger.debug("AppleScript is only available on macOS")
            return context
            
        try:
            # Try Chrome first
            chrome_script = """
            tell application "Google Chrome"
                if it is running then
                    set activeTab to active tab of front window
                    set theURL to URL of activeTab
                    set theTitle to title of activeTab
                    return theURL & "|" & theTitle
                end if
            end tell
            """
            
            process = subprocess.Popen(
                ['osascript', '-e', chrome_script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout:
                parts = stdout.decode('utf-8').strip().split('|')
                if len(parts) == 2:
                    url, title = parts
                    
                    # Extract domain from URL
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc
                    
                    context['browser_url'] = url
                    context['browser_title'] = title
                    context['browser_domain'] = domain
                    return context
            
            # Fall back to Safari if Chrome failed
            safari_script = """
            tell application "Safari"
                if it is running then
                    set theURL to URL of current tab of front window
                    set theTitle to name of current tab of front window
                    return theURL & "|" & theTitle
                end if
            end tell
            """
            
            process = subprocess.Popen(
                ['osascript', '-e', safari_script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout:
                parts = stdout.decode('utf-8').strip().split('|')
                if len(parts) == 2:
                    url, title = parts
                    
                    # Extract domain from URL
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc
                    
                    context['browser_url'] = url
                    context['browser_title'] = title
                    context['browser_domain'] = domain
        except Exception as e:
            logger.error(f"Error using AppleScript: {e}")
            
        return context
    
    def get_browser_context_data(self) -> Dict[str, str]:
        """
        Get browser context using the best available method.
        
        Returns:
            Dictionary containing browser context information
        """
        # Try CDP method first
        context = self.get_browser_context()
        
        # Fall back to AppleScript on macOS if CDP failed
        if not context['browser_url'] and self.system == 'Darwin':
            context = self.get_context_via_applescript()
            
        return context

# Standalone test function
def test_browser_context():
    """Test the browser context enricher."""
    logging.basicConfig(level=logging.INFO)
    enricher = BrowserContextEnricher()
    context = enricher.get_browser_context_data()
    print("Browser Context:")
    print(f"URL: {context['browser_url']}")
    print(f"Title: {context['browser_title']}")
    print(f"Domain: {context['browser_domain']}")

if __name__ == "__main__":
    test_browser_context()