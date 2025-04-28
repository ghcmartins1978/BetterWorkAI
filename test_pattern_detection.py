import os
import sys
import time
import json
import requests
import logging
from datetime import datetime, timedelta
import random
from database import db_session
from models import Event, EventSequence
from sqlalchemy import func, desc

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestPatternGenerator:
    """
    Test pattern generator that simulates user activity patterns
    """
    def __init__(self, server_url=None):
        self.server_url = server_url or os.environ.get('AUTOMATION_SERVER_URL', 'http://127.0.0.1:17400')
        if not self.server_url:
            logger.warning("No Rust helper URL provided.")
    
    def is_connected(self):
        """Check if we can connect to the Rust helper"""
        if not self.server_url:
            return False
            
        try:
            response = requests.get(f"{self.server_url}/api/status", timeout=3)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to Rust helper: {e}")
            return False
            
    def start_monitoring(self):
        """Start monitoring on the Rust helper"""
        if not self.server_url:
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/monitoring", 
                json={'enable': True},
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return False
            
    def create_direct_events(self, pattern_name, repeat_count=3):
        """
        Create test patterns by directly inserting events into the database
        
        Args:
            pattern_name: Name of the pattern to create
            repeat_count: Number of times to repeat the pattern
        """
        logger.info(f"Generating '{pattern_name}' pattern {repeat_count} times by direct database insertion")
        
        for i in range(repeat_count):
            logger.info(f"Generating pattern instance {i+1}/{repeat_count}")
            
            if pattern_name == "copy_paste":
                events = self._generate_copy_paste_events()
            elif pattern_name == "browser_navigation":
                events = self._generate_browser_navigation_events()
            elif pattern_name == "window_arrange":
                events = self._generate_window_arrange_events()
            else:
                logger.error(f"Unknown pattern name: {pattern_name}")
                return False
                
            # Insert events directly into database
            self._create_event_sequence(events)
            
            # Wait between pattern instances
            time.sleep(5)
            
        logger.info(f"Successfully generated {repeat_count} instances of '{pattern_name}' pattern")
        return True
        
    def _create_event_sequence(self, events):
        """Create an event sequence with the given events"""
        try:
            # First create events in the events table
            for event_data in events:
                timestamp = datetime.fromisoformat(event_data['timestamp'])
                event = Event(
                    type=event_data['type'],
                    data=json.dumps(event_data),
                    timestamp=timestamp
                )
                db_session.add(event)
            
            # Then create a sequence
            start_time = datetime.fromisoformat(events[0]['timestamp'])
            end_time = datetime.fromisoformat(events[-1]['timestamp'])
            
            # Extract windows from events
            windows = set()
            for event in events:
                if 'window' in event:
                    windows.add(event['window'])
            
            metadata = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'event_count': len(events),
                'window_count': len(windows),
                'windows': list(windows),
                'reason': 'test_pattern'
            }
            
            sequence = EventSequence(
                start_time=start_time,
                end_time=end_time,
                event_count=len(events),
                meta_data=json.dumps(metadata),
                data=json.dumps(events)
            )
            
            db_session.add(sequence)
            db_session.commit()
            
            logger.info(f"Created event sequence with {len(events)} events")
            return True
        except Exception as e:
            logger.error(f"Error creating event sequence: {e}")
            db_session.rollback()
            return False
    
    def _generate_timestamp(self, offset_seconds=0):
        """Generate a timestamp with an offset from now"""
        return (datetime.now() + timedelta(seconds=offset_seconds)).isoformat()
    
    def _generate_copy_paste_events(self):
        """Generate events for a copy-paste pattern"""
        events = []
        base_time = 0
        
        # Start in first window
        events.append({
            'type': 'window_change',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Select text
        events.append({
            'type': 'mouse_click',
            'x': 100,
            'y': 200,
            'button': 'left',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.5
        
        # Key presses for selection
        events.append({
            'type': 'key_press',
            'key': 'shift',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        for i in range(5):
            events.append({
                'type': 'key_press',
                'key': 'right',
                'window': "Document Editor",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.2
            
        events.append({
            'type': 'key_release',
            'key': 'shift',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.5
        
        # Copy
        events.append({
            'type': 'key_press',
            'key': 'ctrl',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_press',
            'key': 'c',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_release',
            'key': 'c',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_release',
            'key': 'ctrl',
            'window': "Document Editor",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Switch window
        events.append({
            'type': 'window_change',
            'window': "Email Client",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Click to position cursor
        events.append({
            'type': 'mouse_click',
            'x': 150,
            'y': 300,
            'button': 'left',
            'window': "Email Client",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.5
        
        # Paste
        events.append({
            'type': 'key_press',
            'key': 'ctrl',
            'window': "Email Client",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_press',
            'key': 'v',
            'window': "Email Client",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_release',
            'key': 'v',
            'window': "Email Client",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_release',
            'key': 'ctrl',
            'window': "Email Client",
            'timestamp': self._generate_timestamp(base_time)
        })
        
        return events
        
    def _generate_browser_navigation_events(self):
        """Generate events for a browser navigation pattern"""
        events = []
        base_time = 0
        
        # Start in browser
        events.append({
            'type': 'window_change',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Click address bar
        events.append({
            'type': 'mouse_click',
            'x': 300,
            'y': 50,
            'button': 'left',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.5
        
        # Type URL
        for c in "example.com":
            events.append({
                'type': 'key_press',
                'key': c,
                'window': "Web Browser",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.1
            
            events.append({
                'type': 'key_release',
                'key': c,
                'window': "Web Browser",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.1
        
        # Press Enter
        events.append({
            'type': 'key_press',
            'key': 'enter',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_release',
            'key': 'enter',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Scroll down
        for i in range(3):
            events.append({
                'type': 'mouse_scroll',
                'x': 400,
                'y': 300,
                'dx': 0,
                'dy': -1,
                'window': "Web Browser",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.5
        
        # Click a link
        events.append({
            'type': 'mouse_click',
            'x': 250,
            'y': 400,
            'button': 'left',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Go back (Alt+Left)
        events.append({
            'type': 'key_press',
            'key': 'alt',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_press',
            'key': 'left',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_release',
            'key': 'left',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        events.append({
            'type': 'key_release',
            'key': 'alt',
            'window': "Web Browser",
            'timestamp': self._generate_timestamp(base_time)
        })
        
        return events
        
    def _generate_window_arrange_events(self):
        """Generate events for a window arrangement pattern"""
        events = []
        base_time = 0
        
        # Start with first window
        events.append({
            'type': 'window_change',
            'window': "Excel Spreadsheet",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Resize first window
        events.append({
            'type': 'mouse_click',
            'x': 800,
            'y': 600,
            'button': 'left',
            'window': "Excel Spreadsheet",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        for i in range(5):
            events.append({
                'type': 'mouse_move',
                'x': 800+i*10,
                'y': 600+i*10,
                'window': "Excel Spreadsheet",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.2
            
        events.append({
            'type': 'mouse_click',
            'x': 850,
            'y': 650,
            'button': 'left',
            'window': "Excel Spreadsheet",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Move first window
        events.append({
            'type': 'mouse_click',
            'x': 400,
            'y': 20,
            'button': 'left',
            'window': "Excel Spreadsheet",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        for i in range(5):
            events.append({
                'type': 'mouse_move',
                'x': 400+i*10,
                'y': 20,
                'window': "Excel Spreadsheet",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.2
            
        events.append({
            'type': 'mouse_click',
            'x': 450,
            'y': 20,
            'button': 'left',
            'window': "Excel Spreadsheet",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Switch to second window
        events.append({
            'type': 'window_change',
            'window': "PowerPoint Presentation",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Resize second window
        events.append({
            'type': 'mouse_click',
            'x': 800,
            'y': 600,
            'button': 'left',
            'window': "PowerPoint Presentation",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        for i in range(5):
            events.append({
                'type': 'mouse_move',
                'x': 800-i*10,
                'y': 600+i*10,
                'window': "PowerPoint Presentation",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.2
            
        events.append({
            'type': 'mouse_click',
            'x': 750,
            'y': 650,
            'button': 'left',
            'window': "PowerPoint Presentation",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 1
        
        # Move second window
        events.append({
            'type': 'mouse_click',
            'x': 400,
            'y': 20,
            'button': 'left',
            'window': "PowerPoint Presentation",
            'timestamp': self._generate_timestamp(base_time)
        })
        base_time += 0.2
        
        for i in range(5):
            events.append({
                'type': 'mouse_move',
                'x': 400-i*10,
                'y': 20,
                'window': "PowerPoint Presentation",
                'timestamp': self._generate_timestamp(base_time)
            })
            base_time += 0.2
            
        events.append({
            'type': 'mouse_click',
            'x': 350,
            'y': 20,
            'button': 'left',
            'window': "PowerPoint Presentation",
            'timestamp': self._generate_timestamp(base_time)
        })
        
        return events
        
    def check_patterns(self):
        """Check for detected patterns in the database"""
        from models import Pattern
        
        try:
            patterns = db_session.query(Pattern).order_by(desc(Pattern.detection_time)).all()
            
            if not patterns:
                logger.info("No patterns detected yet")
                return []
                
            logger.info(f"Found {len(patterns)} patterns:")
            for pattern in patterns:
                logger.info(f"  Pattern {pattern.id}: {pattern.name}")
                logger.info(f"    Status: {pattern.status}")
                logger.info(f"    Score: {pattern.score}")
                logger.info(f"    Detected: {pattern.detection_time}")
                
                # Get number of sequences
                sequence_ids = json.loads(pattern.sequence_ids)
                logger.info(f"    Sequences: {len(sequence_ids)}")
                
            return patterns
        except Exception as e:
            logger.error(f"Error checking patterns: {e}")
            return []
            
    def check_suggestions(self):
        """Check for automation suggestions in the database"""
        from models import Suggestion
        
        try:
            suggestions = db_session.query(Suggestion).order_by(desc(Suggestion.creation_time)).all()
            
            if not suggestions:
                logger.info("No suggestions available yet")
                return []
                
            logger.info(f"Found {len(suggestions)} suggestions:")
            for suggestion in suggestions:
                logger.info(f"  Suggestion {suggestion.id}: {suggestion.title}")
                logger.info(f"    Status: {suggestion.status}")
                logger.info(f"    Created: {suggestion.creation_time}")
                
                # Get pattern info
                if suggestion.pattern:
                    logger.info(f"    Pattern: {suggestion.pattern.name}")
                
            return suggestions
        except Exception as e:
            logger.error(f"Error checking suggestions: {e}")
            return []

def main():
    server_url = os.environ.get('AUTOMATION_SERVER_URL', 'http://127.0.0.1:17400')
    
    if len(sys.argv) < 2:
        print("Usage: python test_pattern_detection.py <command> [args]")
        print("Commands:")
        print("  generate <pattern_name> [repeat_count] - Generate a pattern")
        print("    Available patterns: copy_paste, browser_navigation, window_arrange")
        print("  check_patterns - Check for detected patterns")
        print("  check_suggestions - Check for automation suggestions")
        return
        
    command = sys.argv[1]
    
    # Create generator instance
    generator = TestPatternGenerator(server_url)
    
    if command == "generate":
        if len(sys.argv) < 3:
            print("Error: Missing pattern name")
            return
            
        pattern_name = sys.argv[2]
        repeat_count = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        
        generator.create_direct_events(pattern_name, repeat_count)
    elif command == "check_patterns":
        generator.check_patterns()
    elif command == "check_suggestions":
        generator.check_suggestions()
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()