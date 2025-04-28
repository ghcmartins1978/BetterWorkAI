import os
import json
import logging
from datetime import datetime

# Import database components
from database import async_db_writer
from models import Event

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# In-memory event cache for fast access to recent events
recent_events = []
MAX_RECENT_EVENTS = 1000

def get_log_file_path():
    """Get the path for the current log file (based on date)"""
    today = datetime.now().strftime('%Y-%m-%d')
    log_dir = os.path.join(os.getcwd(), 'logs')
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    return os.path.join(log_dir, f'events_{today}.json')

def _db_store_event(session, event_type, event_data_json):
    """
    Store an event in the database
    This function is called by the async database writer
    
    Args:
        session: Database session
        event_type: Type of event
        event_data_json: JSON string of event data
    """
    # Create a new Event object
    event = Event(
        type=event_type,
        data=event_data_json,
        timestamp=datetime.now()
    )
    
    # Add to session
    session.add(event)
    logger.debug(f"Event stored in database: {event_type}")
    
    return event.id

def log_event(event_data):
    """
    Log an event to the daily JSON log file and the database
    
    Args:
        event_data: Dictionary with event data
    """
    try:
        # Add timestamp if not present
        if 'timestamp' not in event_data:
            event_data['timestamp'] = datetime.now().isoformat()
            
        # Add to in-memory cache
        recent_events.append(event_data)
        
        # Trim cache if needed
        if len(recent_events) > MAX_RECENT_EVENTS:
            del recent_events[0]
            
        # Get log file path
        log_file = get_log_file_path()
        
        # Check if file exists
        if os.path.exists(log_file):
            try:
                # Read existing events
                with open(log_file, 'r') as f:
                    events = json.load(f)
            except json.JSONDecodeError:
                # File exists but is invalid JSON
                events = []
        else:
            # Create new file
            events = []
            
        # Add event to list
        events.append(event_data)
        
        # Write back to file
        with open(log_file, 'w') as f:
            json.dump(events, f, indent=2)
            
        # Queue database insert using async writer
        # Extract event type from the data
        event_type = event_data.get('type', 'unknown')
        
        # Convert data to JSON string
        event_data_json = json.dumps(event_data)
        
        # Add to async database writer queue
        async_db_writer.add_task(_db_store_event, event_type, event_data_json)
        logger.debug(f"Event queued for database insert: {event_type}")
            
    except Exception as e:
        logger.error(f"Error logging event: {e}")
        
def get_recent_events(max_count=100):
    """
    Get the most recent events from the log
    
    Args:
        max_count: Maximum number of events to return
        
    Returns:
        List of event dictionaries, most recent first
    """
    events = list(recent_events)
    events.reverse()  # Most recent first
    return events[:max_count]