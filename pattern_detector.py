import logging
import json
import time
import threading
from datetime import datetime, timedelta
import difflib

from database import db_session
from models import EventSequence, Pattern

logger = logging.getLogger(__name__)

class PatternDetector:
    """
    Identifies repetitive behaviors in event sequences
    """
    def __init__(self, settings):
        self.settings = settings
        self.reasoning_engine = None
        self.running = False
        self.pattern_check_thread = None
        self.pattern_check_interval = 600  # check for patterns every 10 minutes
        
    def set_reasoning_engine(self, engine):
        """Set the reasoning engine for pattern evaluation"""
        self.reasoning_engine = engine
        
    def start(self):
        """Start pattern detection"""
        if self.running:
            return
            
        logger.info("Starting pattern detector")
        self.running = True
        
        # Start pattern checking thread
        self.pattern_check_thread = threading.Thread(target=self._pattern_check_loop, daemon=True)
        self.pattern_check_thread.start()
        
    def stop(self):
        """Stop pattern detection"""
        logger.info("Stopping pattern detector")
        self.running = False
        
    def analyze_sequence(self, sequence_id, events, metadata):
        """
        Analyze a completed sequence of events for patterns
        
        Args:
            sequence_id: Database ID of the sequence
            events: List of event dictionaries
            metadata: Dictionary with sequence metadata
        """
        if not self.running:
            return
            
        logger.debug(f"Analyzing sequence {sequence_id} with {len(events)} events")
        
        # Quick check if sequence is worth analyzing
        if len(events) < 10:
            logger.debug(f"Sequence {sequence_id} too short for pattern analysis")
            return
            
        # Check for immediate pattern match with recent sequences
        self._check_for_immediate_match(sequence_id, events, metadata)
        
    def _check_for_immediate_match(self, sequence_id, events, metadata):
        """Check if this sequence matches any recent sequences"""
        # Get recent sequences from the last 24 hours
        try:
            yesterday = datetime.now() - timedelta(days=1)
            recent_sequences = db_session.query(EventSequence).filter(
                EventSequence.id != sequence_id,
                EventSequence.start_time > yesterday
            ).order_by(EventSequence.start_time.desc()).limit(10).all()
            
            if not recent_sequences:
                return
                
            for seq in recent_sequences:
                try:
                    seq_events = json.loads(seq.data)
                    similarity = self._calculate_sequence_similarity(events, seq_events)
                    
                    if similarity > 0.7:  # High similarity threshold
                        logger.info(f"Found similar sequence {seq.id} with similarity {similarity:.2f}")
                        
                        # Create or update pattern
                        self._record_pattern_match(sequence_id, seq.id, similarity)
                        
                        # Stop after finding one high-similarity match
                        break
                        
                except Exception as e:
                    logger.error(f"Error comparing with sequence {seq.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error retrieving recent sequences: {e}")
            
    def _pattern_check_loop(self):
        """Thread function to periodically do deep pattern analysis"""
        while self.running:
            try:
                logger.debug("Running periodic pattern analysis")
                
                # Find sequences from last week
                week_ago = datetime.now() - timedelta(days=7)
                sequences = db_session.query(EventSequence).filter(
                    EventSequence.start_time > week_ago
                ).order_by(EventSequence.start_time.desc()).all()
                
                if len(sequences) > 1:
                    self._analyze_sequences_for_patterns(sequences)
                    
            except Exception as e:
                logger.error(f"Error in pattern check loop: {e}")
                
            # Sleep until next check
            time.sleep(self.pattern_check_interval)
            
    def _analyze_sequences_for_patterns(self, sequences):
        """Analyze all sequences for patterns using clustering approach"""
        logger.info(f"Analyzing {len(sequences)} sequences for patterns")
        
        # Simple clustering by comparing all sequences
        clusters = []
        
        for i, seq1 in enumerate(sequences):
            # Skip if already in a cluster
            if any(seq1.id in cluster for cluster in clusters):
                continue
                
            # Start a new cluster
            current_cluster = [seq1.id]
            seq1_events = json.loads(seq1.data)
            
            # Compare with remaining sequences
            for j in range(i+1, len(sequences)):
                seq2 = sequences[j]
                
                # Skip if already in a cluster
                if any(seq2.id in cluster for cluster in clusters):
                    continue
                    
                try:
                    seq2_events = json.loads(seq2.data)
                    similarity = self._calculate_sequence_similarity(seq1_events, seq2_events)
                    
                    if similarity > 0.6:  # Lower threshold for clustering
                        current_cluster.append(seq2.id)
                        
                except Exception as e:
                    logger.error(f"Error comparing sequences {seq1.id} and {seq2.id}: {e}")
                    
            # Add cluster if it has multiple sequences
            if len(current_cluster) > 1:
                clusters.append(current_cluster)
                
        # Process found clusters
        for i, cluster in enumerate(clusters):
            if len(cluster) >= 2:
                logger.info(f"Found pattern cluster #{i+1} with {len(cluster)} sequences")
                
                # Create pattern from cluster
                name = f"Detected Pattern #{i+1}"
                description = f"Pattern detected across {len(cluster)} similar sequences"
                
                # Create or update pattern in database
                try:
                    pattern = Pattern(
                        name=name,
                        description=description,
                        sequence_ids=json.dumps(cluster),
                        detection_time=datetime.now(),
                        score=len(cluster) / 10.0,  # Score based on cluster size
                        status="detected"
                    )
                    db_session.add(pattern)
                    db_session.commit()
                    
                    # Send to reasoning engine for evaluation
                    if self.reasoning_engine:
                        self.reasoning_engine.evaluate_pattern(pattern.id)
                        
                except Exception as e:
                    logger.error(f"Error storing pattern: {e}")
                    db_session.rollback()
                
    def _record_pattern_match(self, sequence_id1, sequence_id2, similarity):
        """Record a pattern match between two sequences"""
        try:
            # Check if pattern already exists for these sequences
            existing_patterns = db_session.query(Pattern).all()
            
            for pattern in existing_patterns:
                try:
                    sequence_ids = json.loads(pattern.sequence_ids)
                    
                    # Check if both sequences are in this pattern
                    if sequence_id1 in sequence_ids and sequence_id2 in sequence_ids:
                        logger.debug(f"Sequences already part of pattern {pattern.id}")
                        return pattern.id
                        
                    # Check if one sequence is in this pattern
                    elif sequence_id1 in sequence_ids or sequence_id2 in sequence_ids:
                        # Add the other sequence to this pattern
                        if sequence_id1 not in sequence_ids:
                            sequence_ids.append(sequence_id1)
                        if sequence_id2 not in sequence_ids:
                            sequence_ids.append(sequence_id2)
                            
                        # Update pattern
                        pattern.sequence_ids = json.dumps(sequence_ids)
                        pattern.score = max(pattern.score, similarity)
                        pattern.last_match_time = datetime.now()
                        db_session.commit()
                        
                        # Send to reasoning engine for evaluation
                        if self.reasoning_engine:
                            self.reasoning_engine.evaluate_pattern(pattern.id)
                            
                        return pattern.id
                        
                except Exception as e:
                    logger.error(f"Error processing pattern {pattern.id}: {e}")
            
            # Create new pattern
            name = f"Pattern {datetime.now().strftime('%Y%m%d-%H%M%S')}"
            description = f"Pattern between sequences {sequence_id1} and {sequence_id2}"
            sequence_ids = [sequence_id1, sequence_id2]
            
            pattern = Pattern(
                name=name,
                description=description,
                sequence_ids=json.dumps(sequence_ids),
                detection_time=datetime.now(),
                last_match_time=datetime.now(),
                score=similarity,
                status="detected"
            )
            db_session.add(pattern)
            db_session.commit()
            
            # Send to reasoning engine for evaluation
            if self.reasoning_engine:
                self.reasoning_engine.evaluate_pattern(pattern.id)
                
            return pattern.id
            
        except Exception as e:
            logger.error(f"Error recording pattern match: {e}")
            db_session.rollback()
            return None
            
    def _calculate_sequence_similarity(self, events1, events2):
        """
        Calculate similarity between two event sequences
        
        This uses a simplified approach combining:
        1. Event type sequence similarity
        2. Window context similarity
        3. Duration similarity
        """
        # Extract event types sequences
        types1 = [e['type'] for e in events1]
        types2 = [e['type'] for e in events2]
        
        # Calculate type sequence similarity
        type_sim = difflib.SequenceMatcher(None, types1, types2).ratio()
        
        # Extract windows
        windows1 = []
        windows2 = []
        
        for e in events1:
            if 'window' in e and e['window'] and e['window'] not in windows1:
                windows1.append(e['window'])
                
        for e in events2:
            if 'window' in e and e['window'] and e['window'] not in windows2:
                windows2.append(e['window'])
                
        # Calculate window similarity
        if windows1 and windows2:
            common_windows = set(windows1).intersection(set(windows2))
            window_sim = len(common_windows) / max(len(windows1), len(windows2))
        else:
            window_sim = 0
            
        # Calculate length similarity
        len_sim = min(len(events1), len(events2)) / max(len(events1), len(events2))
        
        # Calculate weighted similarity
        similarity = (type_sim * 0.5) + (window_sim * 0.3) + (len_sim * 0.2)
        
        return similarity
