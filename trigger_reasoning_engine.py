import os
import sys
import time
import json
import logging
from datetime import datetime
from sqlalchemy import desc

from database import db_session
from models import Event, EventSequence, Pattern, Suggestion
from reasoning_engine import ReasoningEngine
from settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def force_pattern_evaluation():
    """Force reasoning engine to evaluate patterns and create suggestions"""
    # Initialize settings and reasoning engine
    settings = Settings()
    engine = ReasoningEngine(settings)
    
    # Get all detected patterns
    patterns = db_session.query(Pattern).filter(Pattern.status == 'detected').all()
    
    if not patterns:
        logger.info("No patterns in 'detected' status found in database")
        return
        
    logger.info(f"Found {len(patterns)} patterns to evaluate...")
    
    # Process patterns
    for pattern in patterns:
        try:
            logger.info(f"Evaluating pattern {pattern.id}: {pattern.name}")
            engine.evaluate_pattern(pattern.id)
            
        except Exception as e:
            logger.error(f"Error evaluating pattern {pattern.id}: {e}")
            
    # Check for suggestions
    suggestions = db_session.query(Suggestion).order_by(desc(Suggestion.creation_time)).all()
    
    if not suggestions:
        logger.info("No suggestions created after evaluation")
        return
        
    logger.info(f"Created/Found {len(suggestions)} suggestions:")
    for suggestion in suggestions:
        logger.info(f"  Suggestion {suggestion.id}: {suggestion.title}")
        logger.info(f"    Status: {suggestion.status}")
        logger.info(f"    Created: {suggestion.creation_time}")
        logger.info(f"    Description: {suggestion.description}")
        
        # Get pattern info
        if suggestion.pattern:
            logger.info(f"    Pattern: {suggestion.pattern.name}")
            logger.info(f"    Pattern Status: {suggestion.pattern.status}")
            
def create_macro_from_suggestions():
    """Create macros from any pending suggestions"""
    # Initialize settings and reasoning engine
    settings = Settings()
    engine = ReasoningEngine(settings)
    
    # Get all pending suggestions
    suggestions = db_session.query(Suggestion).filter(Suggestion.status == 'pending').all()
    
    if not suggestions:
        logger.info("No pending suggestions found")
        return
        
    logger.info(f"Found {len(suggestions)} pending suggestions, creating macros...")
    
    # Process suggestions
    for suggestion in suggestions:
        try:
            logger.info(f"Creating macro from suggestion {suggestion.id}: {suggestion.title}")
            macro_id = engine.create_macro_from_suggestion(suggestion.id)
            
            if macro_id:
                logger.info(f"  Created macro {macro_id}")
                
                # Enhance with AI if OpenAI key is available
                if 'OPENAI_API_KEY' in os.environ and os.environ.get('OPENAI_API_KEY'):
                    logger.info(f"  Enhancing macro {macro_id} with AI")
                    engine.enhance_macro_with_ai(macro_id)
            else:
                logger.error(f"  Failed to create macro")
                
        except Exception as e:
            logger.error(f"Error creating macro from suggestion {suggestion.id}: {e}")

def main():
    # Check for command argument
    if len(sys.argv) > 1 and sys.argv[1] == 'create_macros':
        create_macro_from_suggestions()
    else:
        force_pattern_evaluation()

if __name__ == "__main__":
    main()