import os
import sys
import time
import json
import requests
import logging
from datetime import datetime, timedelta
import random

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_pattern(server_url, pattern_name, repeat_count=3):
    """
    Create a test pattern by sending simulated events to the automation server
    
    Args:
        server_url: URL of the automation server
        pattern_name: Name of the pattern to create
        repeat_count: Number of times to repeat the pattern
    """
    if not server_url:
        logger.error("No server URL provided")
        return False
        
    # Make sure server is up and monitoring is enabled
    try:
        response = requests.get(f"{server_url}/api/status", timeout=5)
        status = response.json()
        
        if not status.get('monitoring', False):
            logger.error("Monitoring is not enabled on the server")
            return False
    except Exception as e:
        logger.error(f"Error checking server status: {e}")
        return False
        
    # Now generate simulated patterns
    logger.info(f"Generating '{pattern_name}' pattern {repeat_count} times")
    
    for i in range(repeat_count):
        logger.info(f"Generating pattern instance {i+1}/{repeat_count}")
        
        if pattern_name == "copy_paste":
            simulate_copy_paste_pattern(server_url)
        elif pattern_name == "browser_navigation":
            simulate_browser_navigation_pattern(server_url)
        elif pattern_name == "window_arrange":
            simulate_window_arrange_pattern(server_url)
        else:
            logger.error(f"Unknown pattern name: {pattern_name}")
            return False
            
        # Wait between pattern instances to ensure they're separate sequences
        time.sleep(20)
        
    logger.info(f"Successfully generated {repeat_count} instances of '{pattern_name}' pattern")
    return True

def send_event(server_url, event_type, **params):
    """Send a single event to the automation server"""
    try:
        event_data = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            **params
        }
        
        # For debugging
        logger.info(f"Sending event: {event_type} - {params}")
        
        response = requests.post(
            f"{server_url}/api/events/add", 
            json=event_data,
            timeout=5
        )
        
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Error sending event: Status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error sending event: {e}")
        return False

def simulate_copy_paste_pattern(server_url):
    """Simulate a copy-paste pattern with multiple windows"""
    # Start in first window
    send_event(server_url, 'window_change', window="Document Editor")
    time.sleep(1)
    
    # Select text
    send_event(server_url, 'mouse_click', x=100, y=200, button='left')
    time.sleep(0.5)
    send_event(server_url, 'key_press', key='shift')
    for i in range(5):
        send_event(server_url, 'key_press', key='right')
        time.sleep(0.2)
    send_event(server_url, 'key_release', key='shift')
    time.sleep(0.5)
    
    # Copy
    send_event(server_url, 'key_press', key='ctrl')
    send_event(server_url, 'key_press', key='c')
    send_event(server_url, 'key_release', key='c')
    send_event(server_url, 'key_release', key='ctrl')
    time.sleep(1)
    
    # Switch window
    send_event(server_url, 'window_change', window="Email Client")
    time.sleep(1)
    
    # Click to position cursor
    send_event(server_url, 'mouse_click', x=150, y=300, button='left')
    time.sleep(0.5)
    
    # Paste
    send_event(server_url, 'key_press', key='ctrl')
    send_event(server_url, 'key_press', key='v')
    send_event(server_url, 'key_release', key='v')
    send_event(server_url, 'key_release', key='ctrl')
    time.sleep(0.5)

def simulate_browser_navigation_pattern(server_url):
    """Simulate a web browsing pattern"""
    # Start in browser
    send_event(server_url, 'window_change', window="Web Browser")
    time.sleep(1)
    
    # Click on address bar
    send_event(server_url, 'mouse_click', x=300, y=50, button='left')
    time.sleep(0.5)
    
    # Type URL
    for c in "example.com":
        send_event(server_url, 'key_press', key=c)
        send_event(server_url, 'key_release', key=c)
        time.sleep(0.1)
    
    # Press Enter
    send_event(server_url, 'key_press', key='enter')
    send_event(server_url, 'key_release', key='enter')
    time.sleep(1)
    
    # Scroll down
    for i in range(3):
        send_event(server_url, 'mouse_scroll', x=400, y=300, dy=-1)
        time.sleep(0.5)
    
    # Click a link
    send_event(server_url, 'mouse_click', x=250, y=400, button='left')
    time.sleep(1)
    
    # Go back
    send_event(server_url, 'key_press', key='alt')
    send_event(server_url, 'key_press', key='left')
    send_event(server_url, 'key_release', key='left')
    send_event(server_url, 'key_release', key='alt')
    time.sleep(1)

def simulate_window_arrange_pattern(server_url):
    """Simulate arranging windows pattern"""
    # Start with first window
    send_event(server_url, 'window_change', window="Excel Spreadsheet")
    time.sleep(1)
    
    # Resize window (drag bottom-right corner)
    send_event(server_url, 'mouse_click', x=800, y=600, button='left')
    for i in range(5):
        send_event(server_url, 'mouse_move', x=800+i*10, y=600+i*10)
        time.sleep(0.2)
    send_event(server_url, 'mouse_click', x=850, y=650, button='left')
    time.sleep(1)
    
    # Move window (drag title bar)
    send_event(server_url, 'mouse_click', x=400, y=20, button='left')
    for i in range(5):
        send_event(server_url, 'mouse_move', x=400+i*10, y=20)
        time.sleep(0.2)
    send_event(server_url, 'mouse_click', x=450, y=20, button='left')
    time.sleep(1)
    
    # Switch to second window
    send_event(server_url, 'window_change', window="PowerPoint Presentation")
    time.sleep(1)
    
    # Resize second window
    send_event(server_url, 'mouse_click', x=800, y=600, button='left')
    for i in range(5):
        send_event(server_url, 'mouse_move', x=800-i*10, y=600+i*10)
        time.sleep(0.2)
    send_event(server_url, 'mouse_click', x=750, y=650, button='left')
    time.sleep(1)
    
    # Move second window
    send_event(server_url, 'mouse_click', x=400, y=20, button='left')
    for i in range(5):
        send_event(server_url, 'mouse_move', x=400-i*10, y=20)
        time.sleep(0.2)
    send_event(server_url, 'mouse_click', x=350, y=20, button='left')
    time.sleep(1)

def main():
    server_url = os.environ.get('AUTOMATION_SERVER_URL', '')
    
    if len(sys.argv) < 2:
        print("Usage: python test_pattern_detection.py <pattern_name> [repeat_count]")
        print("Available patterns: copy_paste, browser_navigation, window_arrange")
        return
        
    pattern_name = sys.argv[1]
    repeat_count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    create_pattern(server_url, pattern_name, repeat_count)

if __name__ == "__main__":
    main()