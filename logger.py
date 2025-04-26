import os
import logging
import json
from datetime import datetime

# Configure standard Python logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def get_log_file_path():
    """Get the path for the current log file (based on date)"""
    today = datetime.now().strftime('%Y%m%d')
    return os.path.join('logs', f'events_{today}.json')

def log_event(event_data):
    """
    Log an event to the daily JSON log file
    
    Args:
        event_data: Dictionary with event data
    """
    try:
        log_file = get_log_file_path()
        
        # Write event data to log file
        with open(log_file, 'a') as f:
            f.write(json.dumps(event_data) + '\n')
            
    except Exception as e:
        logger.error(f"Error writing to event log: {e}")

def get_recent_events(max_count=100):
    """
    Get the most recent events from the log
    
    Args:
        max_count: Maximum number of events to return
        
    Returns:
        List of event dictionaries, most recent first
    """
    events = []
    
    try:
        log_file = get_log_file_path()
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                
                # Parse the most recent events (at the end of the file)
                for line in reversed(lines[-max_count:]):
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except json.JSONDecodeError:
                        logger.error(f"Error parsing event log line: {line}")
                        
    except Exception as e:
        logger.error(f"Error reading event log: {e}")
        
    return events
