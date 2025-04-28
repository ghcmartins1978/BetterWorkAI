"""
Test script for the logger module, specifically the database insert queue functionality.
"""
import time
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the logger module
from logger import log_event, get_recent_events
from database import async_db_writer, session_scope
from models import Event


def test_log_event():
    """Test logging events with the enhanced logger"""
    logger.info("Starting event logging test")
    
    # Generate test events
    for i in range(1, 6):
        event_data = {
            'type': 'test_event',
            'index': i,
            'message': f'Test event {i}',
            'timestamp': datetime.now().isoformat()
        }
        
        # Log the event
        log_event(event_data)
        logger.info(f"Logged test event {i}")
        
        # Small delay to simulate real events
        time.sleep(0.5)
    
    # Let the async database writer process the queue
    logger.info("Waiting for async database writer to process events...")
    time.sleep(3)
    
    # Check in-memory cache
    recent_events = get_recent_events()
    logger.info(f"Recent events in memory: {len(recent_events)}")
    
    # Check database
    with session_scope() as session:
        db_events = session.query(Event).filter(Event.type == 'test_event').all()
        logger.info(f"Events in database: {len(db_events)}")
        
        for event in db_events:
            event_data = json.loads(event.data)
            logger.info(f"Database event: {event.id}, Index: {event_data.get('index')}, Type: {event.type}")
    
    return len(recent_events), len(db_events)


if __name__ == "__main__":
    # Test logging and retrieving events
    try:
        in_memory_count, db_count = test_log_event()
        logger.info(f"Test completed. In-memory events: {in_memory_count}, Database events: {db_count}")
        
        if in_memory_count > 0 and db_count > 0:
            logger.info("SUCCESS: Events were successfully logged to both memory and database")
        else:
            logger.error("FAILURE: Events were not properly logged")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
    finally:
        # Make sure we stop the async writer
        logger.info("Test finished, but not stopping async_db_writer as it's used by the main application")