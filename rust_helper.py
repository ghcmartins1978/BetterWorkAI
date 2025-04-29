#!/usr/bin/env python
"""
BettermanAI Rust Helper Emulator
This is a Python implementation of the Rust helper API to allow the application
to run without requiring the actual Rust binary.
"""

import argparse
import json
import logging
import os
import sys
import threading
import time
from typing import Dict, List, Optional

from flask import Flask, jsonify, request

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

# Create Flask app
app = Flask(__name__)

# Global state
monitoring_enabled = False
last_events = []
last_screenshot = None
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

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get the current status of the helper"""
    uptime = time.time() - started_at
    return jsonify({
        'status': 'running',
        'monitoring': monitoring_enabled,
        'uptime': uptime,
        'connected_clients': connected_clients,
        'version': '1.0.0-python',
        'platform': sys.platform
    })

@app.route('/api/window/list', methods=['GET'])
def get_window_list():
    """Get a list of all window titles"""
    return jsonify({
        'status': 'success',
        'windows': MOCK_WINDOWS
    })

@app.route('/api/window/focus', methods=['POST'])
def focus_window():
    """Focus a window by its title"""
    data = request.json
    title = data.get('title', '')
    logger.info(f"Mock focusing window: {title}")
    
    # Pretend we focused on a window
    return jsonify({
        'status': 'success',
        'message': f'Focused window: {title}'
    })

@app.route('/api/mouse/move', methods=['POST'])
def mouse_move():
    """Move mouse to absolute position"""
    data = request.json
    x = data.get('x', 0)
    y = data.get('y', 0)
    logger.info(f"Mock mouse move to ({x}, {y})")
    
    # Pretend we moved the mouse
    return jsonify({
        'status': 'success',
        'message': f'Mouse moved to ({x}, {y})'
    })

@app.route('/api/mouse/click', methods=['POST'])
def mouse_click():
    """Click at the specified position"""
    data = request.json
    x = data.get('x', 0)
    y = data.get('y', 0)
    button = data.get('button', 'left')
    clicks = data.get('clicks', 1)
    logger.info(f"Mock mouse click at ({x}, {y}) with {button} button, {clicks} clicks")
    
    # Pretend we clicked the mouse
    return jsonify({
        'status': 'success',
        'message': f'Mouse clicked at ({x}, {y})'
    })

@app.route('/api/keyboard/type', methods=['POST'])
def keyboard_type():
    """Type the specified text"""
    data = request.json
    text = data.get('text', '')
    logger.info(f"Mock keyboard type: '{text[:20]}...' (truncated)")
    
    # Pretend we typed the text
    return jsonify({
        'status': 'success',
        'message': f'Typed text: {text[:20]}... (truncated)'
    })

@app.route('/api/keyboard/press', methods=['POST'])
def keyboard_press():
    """Press a single key"""
    data = request.json
    key = data.get('key', '')
    logger.info(f"Mock keyboard press: {key}")
    
    # Pretend we pressed the key
    return jsonify({
        'status': 'success',
        'message': f'Pressed key: {key}'
    })

@app.route('/api/keyboard/hotkey', methods=['POST'])
def keyboard_hotkey():
    """Press a hotkey combination (multiple keys)"""
    data = request.json
    keys = data.get('keys', [])
    key_str = '+'.join(keys)
    logger.info(f"Mock keyboard hotkey: {key_str}")
    
    # Pretend we pressed the hotkey
    return jsonify({
        'status': 'success',
        'message': f'Pressed hotkey: {key_str}'
    })

@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """Start monitoring system events"""
    global monitoring_enabled
    monitoring_enabled = True
    logger.info("Mock monitoring started")
    
    return jsonify({
        'status': 'success',
        'message': 'Monitoring started'
    })

@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop monitoring system events"""
    global monitoring_enabled
    monitoring_enabled = False
    logger.info("Mock monitoring stopped")
    
    return jsonify({
        'status': 'success',
        'message': 'Monitoring stopped'
    })

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get recent system events"""
    # Generate some mock events if monitoring is enabled
    global last_events
    if monitoring_enabled and not last_events:
        last_events = [
            {'type': 'mouse_move', 'x': 500, 'y': 300, 'timestamp': time.time() - 5},
            {'type': 'mouse_click', 'x': 500, 'y': 300, 'button': 'left', 'timestamp': time.time() - 4},
            {'type': 'keyboard_type', 'text': 'Hello world', 'timestamp': time.time() - 3},
            {'type': 'window_change', 'title': 'Visual Studio Code - project.py', 'timestamp': time.time() - 2}
        ]
    
    return jsonify({
        'status': 'success',
        'events': last_events,
        'monitoring': monitoring_enabled
    })

@app.route('/api/screenshot', methods=['GET'])
def get_screenshot():
    """Get a screenshot of the current desktop"""
    # In a real implementation, this would capture and return a screenshot
    # For this mock, we'll just return a success message
    return jsonify({
        'status': 'success',
        'message': 'Screenshot feature not available in mock helper',
        'screenshot': None
    })

@app.route('/api/execute', methods=['POST'])
def execute_macro():
    """Execute a macro (sequence of actions)"""
    data = request.json
    steps = data.get('steps', [])
    logger.info(f"Mock execute macro with {len(steps)} steps")
    
    # Log each step
    for i, step in enumerate(steps):
        action_type = step.get('type', 'unknown')
        logger.info(f"Step {i+1}: {action_type}")
    
    # Pretend we executed the macro
    return jsonify({
        'status': 'success',
        'message': f'Executed macro with {len(steps)} steps'
    })

@app.route('/docs', methods=['GET'])
def get_docs():
    """Return API documentation"""
    return jsonify({
        'api_version': '1.0.0',
        'description': 'BettermanAI Helper API',
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

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='BettermanAI Helper Emulator')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Write the port to a file so the main app can discover it
    port_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'rust_helper_port.txt')
    os.makedirs(os.path.dirname(port_file_path), exist_ok=True)
    with open(port_file_path, 'w') as f:
        f.write(str(args.port))
    
    logger.info(f"BettermanAI Helper Emulator starting on http://{args.host}:{args.port}")
    logger.info(f"Port written to file: {port_file_path}")
    
    # Start the Flask app
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)

if __name__ == '__main__':
    main()