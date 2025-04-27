import logging
import json
import time
import threading
from datetime import datetime

from monitor_controller import MonitorController
import logger as event_logger

logger = logging.getLogger(__name__)

class EventListener:
    """
    Listens for mouse, keyboard, and window activity and logs them
    """
    def __init__(self, settings):
        self.settings = settings
        self.analyzer = None
        self.running = False
        self.window_check_thread = None
        self.monitor_controller = MonitorController()
        self.last_check_time = datetime.now()
        self.check_interval = 5  # seconds
        self.last_event_id = None
        
    def set_analyzer(self, analyzer):
        """Set the context analyzer that will process events"""
        self.analyzer = analyzer
        
    def start(self):
        """Start listening for events"""
        if self.running:
            return
            
        logger.info("Starting event listener")
        self.running = True
        
        # Start window check thread
        self.window_check_thread = threading.Thread(target=self._window_check_loop, daemon=True)
        self.window_check_thread.start()
        
    def stop(self):
        """Stop listening for events"""
        logger.info("Stopping event listener")
        self.running = False
        
    def _fetch_events(self):
        """Fetch events from the automation server"""
        if not self.monitor_controller.is_connected():
            logger.warning("Cannot fetch events: Monitor controller not connected")
            return []
            
        try:
            events = self.monitor_controller.get_events(count=50)
            
            # If we have a last event ID, filter to only new events
            if self.last_event_id is not None:
                new_events = []
                for event in events:
                    if event.get('id', 0) > self.last_event_id:
                        new_events.append(event)
                events = new_events
                
            # Update last event ID if we have events
            if events:
                self.last_event_id = max(event.get('id', 0) for event in events)
                
            return events
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []
        
    def _window_check_loop(self):
        """Thread function to periodically check for new events"""
        while self.running:
            try:
                # Only check every N seconds
                now = datetime.now()
                if (now - self.last_check_time).total_seconds() < self.check_interval:
                    time.sleep(0.5)
                    continue
                    
                self.last_check_time = now
                
                # Fetch events from automation server
                events = self._fetch_events()
                
                if events:
                    logger.info(f"Processing {len(events)} new events")
                    
                # Process each event
                for event_data in events:
                    self._process_event(event_data)
                    
            except Exception as e:
                logger.error(f"Error in event listener loop: {e}")
                
            # Sleep for a short time
            time.sleep(1)
            
    def _process_event(self, event_data):
        """Process and store an event"""
        try:
            # Add timestamp if not present
            if 'timestamp' not in event_data:
                event_data['timestamp'] = datetime.now().isoformat()
                
            # Log event
            event_logger.log_event(event_data)
            
            # Send to analyzer
            if self.analyzer:
                self.analyzer.process_event(event_data)
                
        except Exception as e:
            logger.error(f"Error processing event: {e}")