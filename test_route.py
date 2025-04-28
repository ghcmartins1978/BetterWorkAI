"""
Add a test route to the main Flask application for testing the logger functionality
"""
import json
import time
from datetime import datetime
import logging
from flask import Blueprint, jsonify

from logger import log_event, get_recent_events
from database import session_scope
from models import Event

# Create a blueprint for the test routes
test_bp = Blueprint('test', __name__)
logger = logging.getLogger(__name__)

@test_bp.route('/test_logger')
def test_logger_route():
    """Test route for checking the logger with database insert queue"""
    try:
        # Generate test events
        event_count = 5
        for i in range(1, event_count + 1):
            event_data = {
                'type': 'test_event',
                'index': i,
                'message': f'Test event {i} from web route',
                'timestamp': datetime.now().isoformat()
            }
            
            # Log the event
            log_event(event_data)
            logger.info(f"Logged test event {i}")
            
            # Small delay to simulate real events
            time.sleep(0.2)
        
        # Let the async database writer process the queue
        logger.info("Waiting for async database writer to process events...")
        time.sleep(3)
        
        # Check in-memory cache
        recent_events = get_recent_events()
        memory_count = len([e for e in recent_events if e.get('type') == 'test_event'])
        logger.info(f"Recent test events in memory: {memory_count}")
        
        # Check database
        with session_scope() as session:
            db_events = session.query(Event).filter(Event.type == 'test_event').all()
            db_count = len(db_events)
            logger.info(f"Test events in database: {db_count}")
            
            events_info = []
            for event in db_events:
                event_data = json.loads(event.data)
                events_info.append({
                    'id': event.id,
                    'index': event_data.get('index'),
                    'type': event.type,
                    'message': event_data.get('message')
                })
        
        result = {
            'status': 'success',
            'memory_events': memory_count,
            'database_events': db_count,
            'events': events_info[-5:]  # Return last 5 events for display
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        error_trace = traceback.format_exc()
        
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': error_trace
        }), 500

# Function to register the blueprint with the Flask app
def register_test_routes(app):
    app.register_blueprint(test_bp, url_prefix='/test')