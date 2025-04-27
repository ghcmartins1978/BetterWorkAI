import logging
import json
import time
import threading
from datetime import datetime, timedelta

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
        self.running = False
        self.sequence_check_thread = None
        self.current_sequence = []
        self.current_sequence_start = None
        self.current_sequence_windows = set()
        self.current_sequence_metadata = {}
        self.sequence_timeout = 15  # seconds of inactivity to end a sequence
        
    def set_pattern_detector(self, detector):
        """Set the pattern detector that will analyze sequences"""
        self.pattern_detector = detector
        
    def start(self):
        """Start sequence analysis"""
        if self.running:
            return
            
        logger.info("Starting context analyzer")
        self.running = True
        
        # Start sequence check thread
        self.sequence_check_thread = threading.Thread(target=self._sequence_check_loop, daemon=True)
        self.sequence_check_thread.start()
        
    def stop(self):
        """Stop sequence analysis"""
        logger.info("Stopping context analyzer")
        self.running = False
        
        # Save any remaining sequence
        if self.current_sequence:
            self._save_current_sequence("analyzer_stopped")
        
    def process_event(self, event_data):
        """
        Process an incoming event and add it to the current sequence
        """
        if not self.running:
            return
            
        # Initialize sequence if this is the first event
        if not self.current_sequence:
            self.current_sequence_start = datetime.now()
            self.current_sequence_metadata = {
                'start_time': self.current_sequence_start.isoformat(),
                'windows': []
            }
            
        # Add event to sequence
        self.current_sequence.append(event_data)
        
        # Update metadata
        if 'window' in event_data and event_data['window']:
            window = event_data['window']
            
            # Add to unique windows set
            self.current_sequence_windows.add(window)
            
            # Update metadata with time-ordered windows
            if window not in self.current_sequence_metadata['windows']:
                self.current_sequence_metadata['windows'].append(window)
                
        # Check for sequence end conditions
        if len(self.current_sequence) >= 200:  # Max length reached
            self._save_current_sequence("max_length")
        
    def _sequence_check_loop(self):
        """Thread function to check for sequence timeouts"""
        while self.running:
            try:
                # Check if current sequence has timed out
                if self.current_sequence and self.current_sequence_start:
                    elapsed = (datetime.now() - self.current_sequence_start).total_seconds()
                    
                    # Check for inactivity timeout (no events for N seconds)
                    last_event_time = datetime.fromisoformat(self.current_sequence[-1]['timestamp'] 
                                                            if 'timestamp' in self.current_sequence[-1] 
                                                            else datetime.now().isoformat())
                    
                    inactivity = (datetime.now() - last_event_time).total_seconds()
                    
                    if inactivity > self.sequence_timeout:
                        self._save_current_sequence("inactivity_timeout")
            except Exception as e:
                logger.error(f"Error in sequence check loop: {e}")
                
            # Sleep for a short time
            time.sleep(1)
            
    def _save_current_sequence(self, reason):
        """Save the current sequence and send to pattern detector"""
        if not self.current_sequence:
            return
            
        try:
            # Finalize metadata
            self.current_sequence_metadata.update({
                'end_time': datetime.now().isoformat(),
                'event_count': len(self.current_sequence),
                'window_count': len(self.current_sequence_windows),
                'reason': reason,
                'windows_list': list(self.current_sequence_windows)
            })
            
            # Create database entry
            sequence = EventSequence(
                start_time=self.current_sequence_start,
                end_time=datetime.now(),
                event_count=len(self.current_sequence),
                meta_data=json.dumps(self.current_sequence_metadata),
                data=json.dumps(self.current_sequence)
            )
            
            db_session.add(sequence)
            db_session.commit()
            
            # Send to pattern detector
            if self.pattern_detector:
                self.pattern_detector.analyze_sequence(
                    sequence.id, 
                    self.current_sequence,
                    self.current_sequence_metadata
                )
                
            logger.info(f"Saved event sequence {sequence.id} with {len(self.current_sequence)} events")
            
            # Reset current sequence
            self.current_sequence = []
            self.current_sequence_start = None
            self.current_sequence_windows = set()
            self.current_sequence_metadata = {}
            
        except Exception as e:
            logger.error(f"Error saving event sequence: {e}")
            db_session.rollback()
            
            # Reset current sequence
            self.current_sequence = []
            self.current_sequence_start = None
            self.current_sequence_windows = set()