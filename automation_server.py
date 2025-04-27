from flask import Flask, request, jsonify
from flask_cors import CORS
import pynput
from pynput import mouse, keyboard
import pyautogui
import pygetwindow as gw
import time
import logging
import json
import os
import base64
from io import BytesIO
from datetime import datetime
import threading
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variables to track state
monitoring_active = False
screenshot_enabled = True  # Enable screenshots by default
mouse_listener = None
keyboard_listener = None
window_checker = None
events_log = []  # In-memory event log
max_events = 1000  # Maximum number of events to keep in memory
screenshot_dir = os.path.join(os.getcwd(), 'logs', 'screenshots')

# Initialize controllers
mouse_controller = mouse.Controller()
keyboard_controller = keyboard.Controller()

# Set a small delay between actions to avoid overwhelming the system
ACTION_DELAY = 0.1

class EventLogger:
    """Handles logging events to memory and disk"""
    
    @staticmethod
    def log_event(event_type, **data):
        """Log an event to memory and return the event data"""
        timestamp = datetime.now().isoformat()
        event_data = {
            'timestamp': timestamp,
            'type': event_type,
            **data
        }
        
        # Add to in-memory log (limiting size)
        events_log.append(event_data)
        if len(events_log) > max_events:
            events_log.pop(0)  # Remove oldest event
        
        logger.debug(f"Logged event: {event_type}")
        return event_data

class WindowMonitor:
    """Monitors active window changes"""
    
    def __init__(self, callback):
        self.callback = callback
        self.current_window = None
        self.running = False
        self.thread = None
    
    def start(self):
        """Start monitoring window changes"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Window monitoring started")
    
    def stop(self):
        """Stop monitoring window changes"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        logger.info("Window monitoring stopped")
    
    def _monitor_loop(self):
        """Thread function to check for window changes"""
        while self.running:
            try:
                active_window = gw.getActiveWindow()
                if active_window:
                    window_title = active_window.title
                    if window_title != self.current_window:
                        self.current_window = window_title
                        self.callback('window_change', window=window_title)
            except Exception as e:
                logger.error(f"Error in window monitoring: {e}")
            
            time.sleep(0.5)  # Check every half second

#
# Input Event Listeners
#

def on_mouse_move(x, y):
    """Handle mouse movement"""
    if monitoring_active:
        EventLogger.log_event('mouse_move', x=x, y=y)

def capture_screenshot():
    """Capture a screenshot and return as base64 encoded string"""
    try:
        # Ensure screenshot directory exists
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Take a screenshot using PyAutoGUI
        screenshot = pyautogui.screenshot()
        
        # Convert to base64
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)  # Lower quality to reduce size
        screenshot_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        logger.debug("Screenshot captured")
        return screenshot_base64
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return None

def on_mouse_click(x, y, button, pressed):
    """Handle mouse clicks"""
    if monitoring_active:
        button_name = getattr(button, 'name', str(button))
        event_data = {
            'x': x, 
            'y': y, 
            'button': button_name, 
            'pressed': pressed
        }
        
        # Only capture screenshot on press (not release) to avoid duplicates
        if pressed and screenshot_enabled:
            screenshot_base64 = capture_screenshot()
            if screenshot_base64:
                event_data['screenshot'] = screenshot_base64
        
        EventLogger.log_event('mouse_click', **event_data)

def on_mouse_scroll(x, y, dx, dy):
    """Handle mouse scrolling"""
    if monitoring_active:
        EventLogger.log_event('mouse_scroll', 
                             x=x, y=y, 
                             dx=dx, dy=dy)

def on_key_press(key):
    """Handle key press events"""
    if monitoring_active:
        # Convert key to string representation
        try:
            key_char = key.char  # For regular characters
        except AttributeError:
            key_char = str(key)  # For special keys
        
        EventLogger.log_event('key_press', key=key_char)

def on_key_release(key):
    """Handle key release events"""
    if monitoring_active:
        # Convert key to string representation
        try:
            key_char = key.char  # For regular characters
        except AttributeError:
            key_char = str(key)  # For special keys
        
        EventLogger.log_event('key_release', key=key_char)

def on_window_change(event_type, **data):
    """Handle window change events"""
    if monitoring_active:
        EventLogger.log_event(event_type, **data)

#
# API Routes
#

@app.route('/')
def home():
    """Home route to check if server is running"""
    return jsonify({
        'status': 'online',
        'monitoring': monitoring_active,
        'message': 'BettermanAI Automation Server is running'
    })

# System status routes
@app.route('/api/status')
def status():
    """Get server status"""
    active_windows = [win.title for win in gw.getAllWindows() if win.title]
    screen_size = pyautogui.size()
    
    return jsonify({
        'status': 'online',
        'monitoring': monitoring_active,
        'screen_size': {
            'width': screen_size[0],
            'height': screen_size[1]
        },
        'current_position': {
            'x': pyautogui.position()[0],
            'y': pyautogui.position()[1]
        },
        'window_count': len(active_windows),
        'events_logged': len(events_log)
    })

@app.route('/api/monitoring', methods=['POST'])
def toggle_monitoring():
    """Start or stop event monitoring"""
    global monitoring_active, mouse_listener, keyboard_listener, window_checker
    
    data = request.json
    should_monitor = data.get('enable', True)
    
    if should_monitor and not monitoring_active:
        # Start monitoring
        mouse_listener = mouse.Listener(
            on_move=on_mouse_move,
            on_click=on_mouse_click,
            on_scroll=on_mouse_scroll
        )
        mouse_listener.start()
        
        keyboard_listener = keyboard.Listener(
            on_press=on_key_press,
            on_release=on_key_release
        )
        keyboard_listener.start()
        
        window_checker = WindowMonitor(on_window_change)
        window_checker.start()
        
        monitoring_active = True
        logger.info("Event monitoring started")
        return jsonify({'monitoring': True, 'message': 'Monitoring started'})
        
    elif not should_monitor and monitoring_active:
        # Stop monitoring
        if mouse_listener:
            mouse_listener.stop()
        if keyboard_listener:
            keyboard_listener.stop()
        if window_checker:
            window_checker.stop()
        
        monitoring_active = False
        logger.info("Event monitoring stopped")
        return jsonify({'monitoring': False, 'message': 'Monitoring stopped'})
    
    return jsonify({'monitoring': monitoring_active, 'message': 'No change'})

# Mouse action routes
@app.route('/api/mouse/position')
def get_mouse_position():
    """Get current mouse position"""
    pos = pyautogui.position()
    return jsonify({'x': pos.x, 'y': pos.y})

@app.route('/api/mouse/move', methods=['POST'])
def mouse_move():
    """Move mouse to position"""
    data = request.json
    x = data.get('x')
    y = data.get('y')
    
    if x is None or y is None:
        return jsonify({'error': 'Missing x or y coordinates'}), 400
    
    try:
        pyautogui.moveTo(x, y, duration=0.1)
        logger.info(f"Mouse moved to {x}, {y}")
        time.sleep(ACTION_DELAY)
        return jsonify({'success': True, 'x': x, 'y': y})
    except Exception as e:
        logger.error(f"Failed to move mouse: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mouse/click', methods=['POST'])
def mouse_click():
    """Click at the current or specified position"""
    data = request.json
    x = data.get('x')
    y = data.get('y')
    button = data.get('button', 'left')
    clicks = data.get('clicks', 1)
    
    try:
        if x is not None and y is not None:
            pyautogui.moveTo(x, y, duration=0.1)
            
        pyautogui.click(button=button, clicks=clicks)
        logger.info(f"Mouse clicked at current position, button={button}, clicks={clicks}")
        time.sleep(ACTION_DELAY)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to click mouse: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mouse/drag', methods=['POST'])
def mouse_drag():
    """Drag mouse from start to end position"""
    data = request.json
    start_x = data.get('start_x')
    start_y = data.get('start_y')
    end_x = data.get('end_x')
    end_y = data.get('end_y')
    button = data.get('button', 'left')
    
    if any(coord is None for coord in [start_x, start_y, end_x, end_y]):
        return jsonify({'error': 'Missing coordinates'}), 400
    
    try:
        pyautogui.moveTo(start_x, start_y, duration=0.1)
        pyautogui.dragTo(end_x, end_y, duration=0.2, button=button)
        logger.info(f"Mouse dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        time.sleep(ACTION_DELAY)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to drag mouse: {e}")
        return jsonify({'error': str(e)}), 500

# Keyboard action routes
@app.route('/api/keyboard/type', methods=['POST'])
def keyboard_type():
    """Type text"""
    data = request.json
    text = data.get('text')
    
    if not text:
        return jsonify({'error': 'Missing text parameter'}), 400
    
    try:
        pyautogui.typewrite(text)
        logger.info(f"Typed text: {text[:10]}...")  # Log only first 10 chars
        time.sleep(ACTION_DELAY)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to type text: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/keyboard/press', methods=['POST'])
def keyboard_press():
    """Press a single key"""
    data = request.json
    key = data.get('key')
    
    if not key:
        return jsonify({'error': 'Missing key parameter'}), 400
    
    try:
        pyautogui.press(key)
        logger.info(f"Pressed key: {key}")
        time.sleep(ACTION_DELAY)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to press key: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/keyboard/hotkey', methods=['POST'])
def keyboard_hotkey():
    """Press a hotkey combination"""
    data = request.json
    keys = data.get('keys', [])
    
    if not keys:
        return jsonify({'error': 'Missing keys parameter'}), 400
    
    try:
        pyautogui.hotkey(*keys)
        logger.info(f"Pressed hotkey: {'+'.join(keys)}")
        time.sleep(ACTION_DELAY)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to press hotkey: {e}")
        return jsonify({'error': str(e)}), 500

# Window management routes
@app.route('/api/window/list')
def window_list():
    """Get list of all windows"""
    try:
        windows = [{'title': win.title, 'active': win.isActive} 
                for win in gw.getAllWindows() if win.title]
        return jsonify({'windows': windows})
    except Exception as e:
        logger.error(f"Failed to get window list: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/window/focus', methods=['POST'])
def window_focus():
    """Focus a window by title"""
    data = request.json
    title = data.get('title')
    
    if not title:
        return jsonify({'error': 'Missing title parameter'}), 400
    
    try:
        matching_windows = gw.getWindowsWithTitle(title)
        
        if not matching_windows:
            return jsonify({'error': f"No windows found with title '{title}'"}), 404
        
        window = matching_windows[0]
        window.activate()
        logger.info(f"Focused window: {title}")
        time.sleep(ACTION_DELAY)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to focus window: {e}")
        return jsonify({'error': str(e)}), 500

# Event logging routes
@app.route('/api/events')
def get_events():
    """Get logged events"""
    count = request.args.get('count', default=100, type=int)
    event_type = request.args.get('type')
    
    if event_type:
        filtered_events = [e for e in events_log if e['type'] == event_type]
    else:
        filtered_events = events_log.copy()
    
    # Return the most recent events up to count
    return jsonify({'events': filtered_events[-count:]})

@app.route('/api/events/clear', methods=['POST'])
def clear_events():
    """Clear event log"""
    global events_log
    events_log = []
    return jsonify({'success': True, 'message': 'Event log cleared'})

if __name__ == '__main__':
    print("=== BettermanAI Automation Server ===")
    print("Starting server on port 5001...")
    # Start with monitoring disabled by default
    app.run(host='0.0.0.0', port=5001, debug=True)