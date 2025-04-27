import os
import sys
import time
import json
import logging
from datetime import datetime
from sqlalchemy import desc

from database import db_session
from models import Event, EventSequence, Pattern
from pattern_detector import PatternDetector
from settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def force_pattern_detection():
    """Force pattern detection on all sequences"""
    # Initialize settings and detector
    settings = Settings()
    detector = PatternDetector(settings)
    
    # Get all sequences
    sequences = db_session.query(EventSequence).order_by(EventSequence.start_time).all()
    
    if not sequences:
        logger.info("No sequences found in database")
        return
        
    logger.info(f"Found {len(sequences)} sequences, analyzing...")
    
    # Process sequences
    for seq in sequences:
        try:
            # Parse data
            events = json.loads(seq.data)
            metadata = json.loads(seq.meta_data) if seq.meta_data else {}
            
            # Analyze sequence
            logger.info(f"Analyzing sequence {seq.id} with {seq.event_count} events")
            detector._check_for_immediate_match(seq.id, events, metadata)
            
        except Exception as e:
            logger.error(f"Error processing sequence {seq.id}: {e}")
            
    # Check for patterns
    patterns = db_session.query(Pattern).order_by(desc(Pattern.detection_time)).all()
    
    if not patterns:
        logger.info("No patterns detected after analysis")
        return
        
    logger.info(f"Detected {len(patterns)} patterns:")
    for pattern in patterns:
        logger.info(f"  Pattern {pattern.id}: {pattern.name}")
        logger.info(f"    Status: {pattern.status}")
        logger.info(f"    Score: {pattern.score}")
        logger.info(f"    Detected: {pattern.detection_time}")
        
        # Get number of sequences
        sequence_ids = json.loads(pattern.sequence_ids)
        logger.info(f"    Sequences: {len(sequence_ids)}")
        
def main():
    force_pattern_detection()

if __name__ == "__main__":
    main()