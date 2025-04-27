import logging
from settings import Settings
from database import db_session
from models import Setting

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_settings():
    """Update settings for testing purposes"""
    settings = Settings()
    
    # Get current values
    current_threshold = settings.get_setting('automation_suggestion_threshold', default=3)
    
    logger.info(f"Current automation_suggestion_threshold: {current_threshold}")
    
    # Update threshold to 2 for testing
    settings.set_setting('automation_suggestion_threshold', 2)
    
    # Verify update
    new_threshold = settings.get_setting('automation_suggestion_threshold')
    logger.info(f"Updated automation_suggestion_threshold: {new_threshold}")
    
if __name__ == "__main__":
    update_settings()