import logging
import time
import json
import os
import threading
from datetime import datetime
import sqlite3

from pynput import mouse, keyboard
try:
    import pygetwindow as gw
except ImportError:
    gw = None

from database import db_session
from models import Event
from logger import log_event

logger = logging.getLogger(__name__)

class EventListener:
    """
    Listens for mouse, keyboard, and window activity and logs them
    """
    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.context_analyzer = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.window_check_thread = None
        self.current_window = None
        self.last_window_check = 0
        self.window_check_interval = 0.5  # seconds
        
        # Create event log directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
    def set_analyzer(self, analyzer):
        """Set the context analyzer that will process events"""
        self.context_analyzer = analyzer
    
    def start(self):
        """Start listening for events"""
        if self.running:
            return
            
        logger.info("Starting event listener")
        self.running = True
        
        # Start mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        
        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()
        
        # Start window monitoring thread
        self.window_check_thread = threading.Thread(target=self._window_check_loop, daemon=True)
        self.window_check_thread.start()
        
        logger.info("Event listener started successfully")
    
    def stop(self):
        """Stop listening for events"""
        logger.info("Stopping event listener")
        self.running = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
            
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        # Window check thread will stop automatically because running=False
        logger.info("Event listener stopped")
    
    def _on_mouse_move(self, x, y):
        """Handle mouse move events"""
        if not self.running or not self.settings.get_setting('track_mouse_moves'):
            return
            
        # Only track a subset of moves to avoid overwhelming the database
        if hasattr(self, '_last_move_time'):
            if time.time() - self._last_move_time < 0.2:  # Record at most 5 moves per second
                return
                
        self._last_move_time = time.time()
        
        event_data = {
            'type': 'mouse_move',
            'x': x,
            'y': y,
            'window': self.current_window,
            'timestamp': datetime.now().isoformat()
        }
        
        self._process_event(event_data)
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        if not self.running or not self.settings.get_setting('track_mouse_clicks'):
            return
            
        event_data = {
            'type': 'mouse_click',
            'x': x,
            'y': y,
            'button': str(button),
            'pressed': pressed,
            'window': self.current_window,
            'timestamp': datetime.now().isoformat()
        }
        
        self._process_event(event_data)
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll events"""
        if not self.running or not self.settings.get_setting('track_mouse_scrolls'):
            return
            
        event_data = {
            'type': 'mouse_scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy,
            'window': self.current_window,
            'timestamp': datetime.now().isoformat()
        }
        
        self._process_event(event_data)
    
    def _on_key_press(self, key):
        """Handle key press events"""
        if not self.running or not self.settings.get_setting('track_keyboard'):
            return
            
        # Convert key to string representation safely
        try:
            key_char = key.char
        except (AttributeError, ValueError):
            key_char = str(key)
            
        event_data = {
            'type': 'key_press',
            'key': key_char,
            'window': self.current_window,
            'timestamp': datetime.now().isoformat()
        }
        
        self._process_event(event_data)
    
    def _on_key_release(self, key):
        """Handle key release events"""
        if not self.running or not self.settings.get_setting('track_keyboard'):
            return
            
        # Convert key to string representation safely
        try:
            key_char = key.char
        except (AttributeError, ValueError):
            key_char = str(key)
            
        event_data = {
            'type': 'key_release',
            'key': key_char,
            'window': self.current_window,
            'timestamp': datetime.now().isoformat()
        }
        
        self._process_event(event_data)
    
    def _window_check_loop(self):
        """Thread function to periodically check active window"""
        while self.running:
            if self.settings.get_setting('track_windows') and gw is not None:
                try:
                    active_window = gw.getActiveWindow()
                    if active_window:
                        window_title = active_window.title
                        
                        # Check if window changed
                        if window_title != self.current_window:
                            self.current_window = window_title
                            
                            event_data = {
                                'type': 'window_change',
                                'window': window_title,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            self._process_event(event_data)
                except Exception as e:
                    logger.error(f"Error getting active window: {e}")
                    
            time.sleep(self.window_check_interval)
    
    def _process_event(self, event_data):
        """Process and store an event"""
        # Log to JSON file
        log_event(event_data)
        
        # Store in database
        try:
            event = Event(
                type=event_data['type'],
                data=json.dumps(event_data),
                timestamp=datetime.fromisoformat(event_data['timestamp'])
            )
            db_session.add(event)
            db_session.commit()
        except Exception as e:
            logger.error(f"Error storing event in database: {e}")
            db_session.rollback()
        
        # Send to analyzer if connected
        if self.context_analyzer:
            self.context_analyzer.process_event(event_data)
