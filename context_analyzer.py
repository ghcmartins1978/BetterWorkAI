import logging
import json
from datetime import datetime, timedelta
import threading
import time

from database import db_session
from models import EventSequence

logger = logging.getLogger(__name__)

class ContextAnalyzer:
    """
    Analyzes events to classify tasks and sequences
    """
    def __init__(self, settings):
        self.settings = settings
        self.pattern_detector = None
        self.current_sequence = []
        self.sequence_start_time = None
        self.sequence_timeout = 60  # seconds
        self.sequence_check_interval = 5  # seconds
        self.max_sequence_length = 1000  # prevent memory issues
        self.running = False
        self.sequence_checker_thread = None
        
    def set_pattern_detector(self, detector):
        """Set the pattern detector that will analyze sequences"""
        self.pattern_detector = detector
        
    def start(self):
        """Start sequence analysis"""
        if self.running:
            return
        
        logger.info("Starting context analyzer")
        self.running = True
        
        # Start sequence timeout checking thread
        self.sequence_checker_thread = threading.Thread(target=self._sequence_check_loop, daemon=True)
        self.sequence_checker_thread.start()
        
    def stop(self):
        """Stop sequence analysis"""
        logger.info("Stopping context analyzer")
        self.running = False
        
        # Save current sequence before stopping
        if self.current_sequence:
            self._save_current_sequence("stopped")
            
    def process_event(self, event_data):
        """
        Process an incoming event and add it to the current sequence
        """
        if not self.running:
            return
            
        # Start a new sequence if this is the first event
        if not self.current_sequence:
            self.sequence_start_time = datetime.now()
            
        # Add event to current sequence
        self.current_sequence.append(event_data)
        
        # Check if we should complete this sequence due to length
        if len(self.current_sequence) >= self.max_sequence_length:
            self._save_current_sequence("max_length")
            
        # Check if this event is a logical break in context
        if event_data['type'] == 'window_change':
            # Window changes often indicate a task context switch
            self._save_current_sequence("window_change")
            
    def _sequence_check_loop(self):
        """Thread function to check for sequence timeouts"""
        while self.running:
            # Check if current sequence has timed out
            if self.current_sequence and self.sequence_start_time:
                elapsed = (datetime.now() - self.sequence_start_time).total_seconds()
                if elapsed > self.sequence_timeout:
                    self._save_current_sequence("timeout")
                    
            time.sleep(self.sequence_check_interval)
                    
    def _save_current_sequence(self, reason):
        """Save the current sequence and send to pattern detector"""
        if not self.current_sequence:
            return
            
        logger.debug(f"Saving sequence with {len(self.current_sequence)} events (reason: {reason})")
        
        # Get sequence metadata
        start_time = self.sequence_start_time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Extract windows from the sequence
        windows = []
        for event in self.current_sequence:
            if 'window' in event and event['window'] not in windows:
                windows.append(event['window'])
                
        # Count event types
        event_types = {}
        for event in self.current_sequence:
            event_type = event['type']
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
        # Create metadata
        metadata = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': duration,
            'event_count': len(self.current_sequence),
            'windows': windows,
            'event_types': event_types,
            'reason': reason
        }
        
        # Store sequence in database
        try:
            sequence = EventSequence(
                start_time=start_time,
                end_time=end_time,
                event_count=len(self.current_sequence),
                metadata=json.dumps(metadata),
                data=json.dumps(self.current_sequence)
            )
            db_session.add(sequence)
            db_session.commit()
            
            # Send to pattern detector if connected
            if self.pattern_detector:
                self.pattern_detector.analyze_sequence(sequence.id, self.current_sequence, metadata)
                
        except Exception as e:
            logger.error(f"Error storing sequence in database: {e}")
            db_session.rollback()
            
        # Reset the current sequence
        self.current_sequence = []
        self.sequence_start_time = None
