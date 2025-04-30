#!/usr/bin/env python
"""
BettermanAI Helper Emulator
This is a Python implementation of the Helper API to allow the application
to run without requiring the actual Rust implementation.
"""

import argparse
import http.server
import json
import logging
import os
import socketserver
import sys
import threading
import time
import urllib.parse
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('betterman_helper')

# Default port
DEFAULT_PORT = 17400

# Global state
monitoring_enabled = False
last_events = []
connected_clients = 0
started_at = time.time()

# Mock window list
MOCK_WINDOWS = [
    {'id': 1, 'title': 'BettermanAI - Workflow Automation', 'app': 'Electron'},
    {'id': 2, 'title': 'Visual Studio Code - project.py', 'app': 'Code'},
    {'id': 3, 'title': 'Terminal - bash', 'app': 'Terminal'},
    {'id': 4, 'title': 'Google Chrome - Google Search', 'app': 'Chrome'},
    {'id': 5, 'title': 'Microsoft Outlook - Inbox', 'app': 'Outlook'}
]

# Endpoint handlers
class HelperHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
    def _send_json_response(self, data):
        self._set_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self._set_headers()
        
    def do_GET(self):
        # Handle GET requests
        global monitoring_enabled, last_events
        
        path = self.path.split('?')[0]  # Remove query string if present
        
        if path == '/api/status':
            # Status endpoint
            uptime = time.time() - started_at
            self._send_json_response({
                'status': 'running',
                'monitoring': monitoring_enabled,
                'uptime': uptime,
                'connected_clients': connected_clients,
                'version': '1.0.0-python',
                'platform': sys.platform
            })
            
        elif path == '/api/window/list':
            # Window list endpoint
            self._send_json_response({
                'status': 'success',
                'windows': MOCK_WINDOWS
            })
            
        elif path == '/api/events':
            # Events endpoint
            if monitoring_enabled and not last_events:
                last_events = [
                    {'type': 'mouse_move', 'x': 500, 'y': 300, 'timestamp': time.time() - 5},
                    {'type': 'mouse_click', 'x': 500, 'y': 300, 'button': 'left', 'timestamp': time.time() - 4},
                    {'type': 'keyboard_type', 'text': 'Hello world', 'timestamp': time.time() - 3},
                    {'type': 'window_change', 'title': 'Visual Studio Code - project.py', 'timestamp': time.time() - 2}
                ]
                
            self._send_json_response({
                'status': 'success',
                'events': last_events,
                'monitoring': monitoring_enabled
            })
            
        elif path == '/api/screenshot':
            # Screenshot endpoint
            self._send_json_response({
                'status': 'success',
                'message': 'Screenshot feature not available in Python implementation of Helper',
                'screenshot': None
            })
            
        elif path == '/docs':
            # API documentation endpoint
            self._send_json_response({
                'api_version': '1.0.0',
                'description': 'BettermanAI Helper API (Python Implementation)',
                'endpoints': [
                    {'path': '/api/status', 'method': 'GET', 'description': 'Get current status'},
                    {'path': '/api/window/list', 'method': 'GET', 'description': 'Get window list'},
                    {'path': '/api/window/focus', 'method': 'POST', 'description': 'Focus window'},
                    {'path': '/api/mouse/move', 'method': 'POST', 'description': 'Move mouse'},
                    {'path': '/api/mouse/click', 'method': 'POST', 'description': 'Click mouse'},
                    {'path': '/api/keyboard/type', 'method': 'POST', 'description': 'Type text'},
                    {'path': '/api/keyboard/press', 'method': 'POST', 'description': 'Press key'},
                    {'path': '/api/keyboard/hotkey', 'method': 'POST', 'description': 'Press hotkey'},
                    {'path': '/api/monitoring/start', 'method': 'POST', 'description': 'Start monitoring'},
                    {'path': '/api/monitoring/stop', 'method': 'POST', 'description': 'Stop monitoring'},
                    {'path': '/api/events', 'method': 'GET', 'description': 'Get events'},
                    {'path': '/api/screenshot', 'method': 'GET', 'description': 'Get screenshot'},
                    {'path': '/api/execute', 'method': 'POST', 'description': 'Execute macro'}
                ]
            })
            
        else:
            # Unknown endpoint
            self._set_headers(status_code=404)
            self._send_json_response({
                'status': 'error',
                'message': f'Unknown endpoint: {path}'
            })
            
    def do_POST(self):
        # Handle POST requests
        global monitoring_enabled, last_events
        
        content_length = int(self.headers['Content-Length']) if 'Content-Length' in self.headers else 0
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            data = {}
            
        path = self.path.split('?')[0]  # Remove query string if present
        
        if path == '/api/window/focus':
            # Focus window endpoint
            title = data.get('title', '')
            logger.info(f"Python Helper: focusing window: {title}")
            
            self._send_json_response({
                'status': 'success',
                'message': f'Focused window: {title}'
            })
            
        elif path == '/api/mouse/move':
            # Mouse move endpoint
            x = data.get('x', 0)
            y = data.get('y', 0)
            logger.info(f"Python Helper: mouse move to ({x}, {y})")
            
            self._send_json_response({
                'status': 'success',
                'message': f'Mouse moved to ({x}, {y})'
            })
            
        elif path == '/api/mouse/click':
            # Mouse click endpoint
            x = data.get('x', 0)
            y = data.get('y', 0)
            button = data.get('button', 'left')
            clicks = data.get('clicks', 1)
            logger.info(f"Python Helper: mouse click at ({x}, {y}) with {button} button, {clicks} clicks")
            
            self._send_json_response({
                'status': 'success',
                'message': f'Mouse clicked at ({x}, {y})'
            })
            
        elif path == '/api/keyboard/type':
            # Keyboard type endpoint
            text = data.get('text', '')
            logger.info(f"Python Helper: keyboard type: '{text[:20]}...' (truncated)")
            
            self._send_json_response({
                'status': 'success',
                'message': f'Typed text: {text[:20]}... (truncated)'
            })
            
        elif path == '/api/keyboard/press':
            # Keyboard press endpoint
            key = data.get('key', '')
            logger.info(f"Mock keyboard press: {key}")
            
            self._send_json_response({
                'status': 'success',
                'message': f'Pressed key: {key}'
            })
            
        elif path == '/api/keyboard/hotkey':
            # Keyboard hotkey endpoint
            keys = data.get('keys', [])
            key_str = '+'.join(keys)
            logger.info(f"Mock keyboard hotkey: {key_str}")
            
            self._send_json_response({
                'status': 'success',
                'message': f'Pressed hotkey: {key_str}'
            })
            
        elif path == '/api/monitoring/start':
            # Start monitoring endpoint
            monitoring_enabled = True
            logger.info("Mock monitoring started")
            
            self._send_json_response({
                'status': 'success',
                'message': 'Monitoring started'
            })
            
        elif path == '/api/monitoring/stop':
            # Stop monitoring endpoint
            monitoring_enabled = False
            logger.info("Mock monitoring stopped")
            
            self._send_json_response({
                'status': 'success',
                'message': 'Monitoring stopped'
            })
            
        elif path == '/api/execute':
            # Execute macro endpoint
            steps = data.get('steps', [])
            logger.info(f"Mock execute macro with {len(steps)} steps")
            
            # Log each step
            for i, step in enumerate(steps):
                action_type = step.get('type', 'unknown')
                logger.info(f"Step {i+1}: {action_type}")
                
            self._send_json_response({
                'status': 'success',
                'message': f'Executed macro with {len(steps)} steps'
            })
            
        else:
            # Unknown endpoint
            self._set_headers(status_code=404)
            self._send_json_response({
                'status': 'error',
                'message': f'Unknown endpoint: {path}'
            })
            
    def log_message(self, format, *args):
        # Override log_message to use our logger
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='BettermanAI Helper - Python Implementation')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Write the port to a file so the main app can discover it
    port_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'helper_port.txt')
    os.makedirs(os.path.dirname(port_file_path), exist_ok=True)
    with open(port_file_path, 'w') as f:
        f.write(str(args.port))
    
    logger.info(f"BettermanAI Helper (Python Implementation) starting on http://{args.host}:{args.port}")
    logger.info(f"Port written to file: {port_file_path}")
    
    # Start the HTTP server
    with socketserver.ThreadingTCPServer((args.host, args.port), HelperHTTPRequestHandler) as httpd:
        try:
            logger.info(f"Server running at http://{args.host}:{args.port}")
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            httpd.server_close()
            logger.info("Server stopped")


if __name__ == '__main__':
    main()