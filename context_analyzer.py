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
        
        # Adaptive sequence timeout parameters from settings
        self.min_sequence_timeout = settings.get_setting('sequence_min_timeout', 5)
        self.max_sequence_timeout = settings.get_setting('sequence_max_timeout', 60)
        self.default_sequence_timeout = settings.get_setting('sequence_default_timeout', 15)
        self.sequence_timeout = self.default_sequence_timeout
        self.max_sequence_events = settings.get_setting('sequence_max_events', 200)
        
        # Activity history for adaptive timing
        self.activity_history = []
        self.max_history_size = 20
        self.activity_patterns = {}  # Store activity patterns by application
        self.adaptive_timeout_enabled = settings.get_setting('sequence_adaptive_timeout_enabled', True)
        
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
        current_window = None
        if 'window' in event_data and event_data['window']:
            window = event_data['window']
            current_window = window
            
            # Add to unique windows set
            self.current_sequence_windows.add(window)
            
            # Update metadata with time-ordered windows
            if window not in self.current_sequence_metadata['windows']:
                self.current_sequence_metadata['windows'].append(window)
        
        # Update adaptive timeout based on this event, if enabled
        if self.adaptive_timeout_enabled and current_window:
            self._update_adaptive_timeout(event_data, current_window)
                
        # Check for sequence end conditions
        if len(self.current_sequence) >= self.max_sequence_events:  # Max length reached
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
            
    def _update_adaptive_timeout(self, event_data, current_window):
        """
        Update the adaptive timeout based on user activity patterns
        
        Args:
            event_data: Current event data
            current_window: Current active window
        """
        try:
            # Get event timestamp
            event_time = datetime.fromisoformat(event_data.get('timestamp', datetime.now().isoformat()))
            
            # Add to activity history
            self.activity_history.append({
                'window': current_window,
                'time': event_time,
                'type': event_data.get('type', 'unknown')
            })
            
            # Trim history if needed
            if len(self.activity_history) > self.max_history_size:
                self.activity_history = self.activity_history[-self.max_history_size:]
                
            # Calculate time between events for this window
            if len(self.activity_history) >= 2:
                # Get events for this window
                window_events = [e for e in self.activity_history if e['window'] == current_window]
                
                if len(window_events) >= 2:
                    # Calculate time gaps between events
                    time_gaps = []
                    for i in range(1, len(window_events)):
                        gap = (window_events[i]['time'] - window_events[i-1]['time']).total_seconds()
                        if gap > 0:
                            time_gaps.append(gap)
                    
                    if time_gaps:
                        # Calculate median gap
                        time_gaps.sort()
                        if len(time_gaps) % 2 == 0:
                            median_gap = (time_gaps[len(time_gaps)//2] + time_gaps[len(time_gaps)//2 - 1]) / 2
                        else:
                            median_gap = time_gaps[len(time_gaps)//2]
                            
                        # Update application pattern
                        if current_window not in self.activity_patterns:
                            self.activity_patterns[current_window] = {
                                'median_gap': median_gap,
                                'sample_count': len(time_gaps)
                            }
                        else:
                            # Rolling average for stability
                            current = self.activity_patterns[current_window]
                            sample_weight = 0.8  # Weight for existing samples vs new data
                            total_samples = current['sample_count'] + len(time_gaps)
                            new_median = (current['median_gap'] * current['sample_count'] * sample_weight + 
                                         sum(time_gaps) * (1-sample_weight)) / total_samples
                            
                            self.activity_patterns[current_window] = {
                                'median_gap': new_median,
                                'sample_count': total_samples
                            }
                        
                        # Adjust timeout based on activity pattern
                        self._adjust_timeout()
            
        except Exception as e:
            logger.error(f"Error updating adaptive timeout: {e}")
    
    def _adjust_timeout(self):
        """Adjust the sequence timeout based on activity patterns"""
        try:
            if not self.activity_patterns:
                return
                
            # Get weighted average of all application medians
            total_weight = 0
            weighted_sum = 0
            
            for window, stats in self.activity_patterns.items():
                # More samples = more weight
                weight = min(1.0, stats['sample_count'] / 10)  # Cap at 1.0
                total_weight += weight
                weighted_sum += stats['median_gap'] * weight
            
            if total_weight > 0:
                # Calculate weighted average
                avg_gap = weighted_sum / total_weight
                
                # Set timeout to a multiple of the average gap
                # Use a multiplier between 3-5x typical gap time
                multiplier = 4.0
                new_timeout = avg_gap * multiplier
                
                # Clamp to min/max range
                new_timeout = max(self.min_sequence_timeout, 
                                  min(self.max_sequence_timeout, new_timeout))
                
                # Only update if change is significant (>10%)
                if abs(new_timeout - self.sequence_timeout) / self.sequence_timeout > 0.1:
                    logger.info(f"Adjusting sequence timeout from {self.sequence_timeout:.1f}s to {new_timeout:.1f}s")
                    self.sequence_timeout = new_timeout
                    
                    # Update metadata with timeout info
                    if self.current_sequence_metadata:
                        self.current_sequence_metadata['adaptive_timeout'] = self.sequence_timeout
        
        except Exception as e:
            logger.error(f"Error adjusting timeout: {e}")
            # Fallback to default timeout
            self.sequence_timeout = self.default_sequence_timeout
    
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
                'windows_list': list(self.current_sequence_windows),
                'sequence_timeout': self.sequence_timeout
            })
            
            # Record activity patterns for future reference
            if self.activity_patterns:
                self.current_sequence_metadata['activity_patterns'] = {
                    window: {'median_gap': stats['median_gap']} 
                    for window, stats in self.activity_patterns.items()
                }
            
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
                
            logger.info(f"Saved event sequence {sequence.id} with {len(self.current_sequence)} events (timeout: {self.sequence_timeout:.1f}s)")
            
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