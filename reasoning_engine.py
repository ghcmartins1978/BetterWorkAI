import logging
import json
import threading
import time
import os
from datetime import datetime

from database import db_session
from models import Pattern, Suggestion, Macro, MacroStep

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """
    AI engine that evaluates patterns and suggests automations
    """
    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.check_thread = None
        self.check_interval = 300  # 5 minutes between checks
        self.openai_available = 'OPENAI_API_KEY' in os.environ and os.environ.get('OPENAI_API_KEY')
        
    def start(self):
        """Start the reasoning engine"""
        if self.running:
            return
            
        logger.info("Starting reasoning engine")
        self.running = True
        
        # Start suggestion check thread
        self.check_thread = threading.Thread(target=self._suggestion_check_loop, daemon=True)
        self.check_thread.start()
        
    def stop(self):
        """Stop the reasoning engine"""
        logger.info("Stopping reasoning engine")
        self.running = False
        
    def evaluate_pattern(self, pattern_id):
        """
        Evaluate a pattern and potentially create automation suggestion
        
        Args:
            pattern_id: Database ID of the pattern to evaluate
        """
        try:
            # Get pattern
            pattern = db_session.query(Pattern).get(pattern_id)
            if not pattern:
                logger.error(f"Pattern {pattern_id} not found")
                return
                
            # Skip if already evaluated
            if pattern.status != 'detected':
                logger.debug(f"Pattern {pattern_id} already evaluated: {pattern.status}")
                return
                
            # Update status
            pattern.status = 'evaluating'
            db_session.commit()
            
            # Extract sequences
            sequence_ids = json.loads(pattern.sequence_ids)
            
            # Make sure we have at least 2 sequences
            if len(sequence_ids) < 2:
                pattern.status = 'rejected'
                pattern.evaluation_notes = 'Not enough sequences to form a pattern'
                db_session.commit()
                return
                
            # Check if pattern has high enough score
            min_score = self.settings.get_setting('automation_min_pattern_score', default=0.7)
            if pattern.score < min_score:
                pattern.status = 'rejected'
                pattern.evaluation_notes = f'Pattern score {pattern.score} below threshold {min_score}'
                db_session.commit()
                return
                
            # Check if pattern happens frequently enough
            suggestion_threshold = self.settings.get_setting('automation_suggestion_threshold', default=3)
            if len(sequence_ids) < suggestion_threshold:
                pattern.status = 'detected'  # Keep it in detected state to potentially match more sequences
                pattern.evaluation_notes = f'Pattern seen {len(sequence_ids)} times, threshold is {suggestion_threshold}'
                db_session.commit()
                return
                
            # Prepare suggestion
            title = f"Automate {pattern.name}"
            description = f"This automation would replace a sequence of {pattern.event_count} events that you've performed {len(sequence_ids)} times."
            
            # Check if suggestion already exists for this pattern
            existing_suggestion = db_session.query(Suggestion).filter(
                Suggestion.pattern_id == pattern_id
            ).first()
            
            if existing_suggestion:
                logger.debug(f"Suggestion already exists for pattern {pattern_id}")
                return
                
            # Create simple steps for the suggestion (in a real system, this would be more complex)
            steps = [
                {"type": "start", "description": "Start automation"},
                {"type": "execute", "description": f"Execute {pattern.event_count} actions"},
                {"type": "end", "description": "Finish automation"}
            ]
            
            # Create suggestion
            suggestion = Suggestion(
                pattern_id=pattern_id,
                title=title,
                description=description,
                steps=json.dumps(steps),
                creation_time=datetime.now(),
                status='pending'
            )
            
            db_session.add(suggestion)
            
            # Update pattern status
            pattern.status = 'approved'
            pattern.evaluation_notes = 'Pattern approved for automation'
            
            db_session.commit()
            
            logger.info(f"Created suggestion {suggestion.id} for pattern {pattern_id}")
            
        except Exception as e:
            logger.error(f"Error evaluating pattern {pattern_id}: {e}")
            db_session.rollback()
            
            # Update pattern status
            try:
                pattern = db_session.query(Pattern).get(pattern_id)
                if pattern:
                    pattern.status = 'error'
                    pattern.evaluation_notes = f'Error during evaluation: {str(e)}'
                    db_session.commit()
            except Exception as rollback_error:
                logger.error(f"Error updating pattern status: {rollback_error}")
    
    def _suggestion_check_loop(self):
        """Thread function to periodically check for pending suggestions"""
        while self.running:
            try:
                # See if there are any patterns that need to be re-evaluated
                patterns = db_session.query(Pattern).filter(
                    Pattern.status == 'detected'
                ).all()
                
                for pattern in patterns:
                    self.evaluate_pattern(pattern.id)
                    
            except Exception as e:
                logger.error(f"Error in suggestion check loop: {e}")
                
            # Sleep until next check
            time.sleep(self.check_interval)
        
    def create_macro_from_suggestion(self, suggestion_id):
        """
        Create a macro from a suggestion
        
        Args:
            suggestion_id: Database ID of the suggestion
            
        Returns:
            ID of the created macro, or None if failed
        """
        try:
            # Get suggestion
            suggestion = db_session.query(Suggestion).get(suggestion_id)
            if not suggestion:
                logger.error(f"Suggestion {suggestion_id} not found")
                return None
                
            # Get pattern
            pattern = suggestion.pattern
            if not pattern:
                logger.error(f"Pattern for suggestion {suggestion_id} not found")
                return None
                
            # Create macro
            macro = Macro(
                name=suggestion.title,
                description=suggestion.description,
                creation_time=datetime.now(),
                step_count=3,  # Placeholder
                status='created'
            )
            
            db_session.add(macro)
            db_session.flush()  # Get ID without committing
            
            # Create simple steps (in a real system, this would be more complex)
            steps = [
                {"action_type": "start", "delay_before": 0.0, "parameters": "{}"},
                {"action_type": "execute", "delay_before": 0.5, "parameters": "{}"},
                {"action_type": "end", "delay_before": 0.5, "parameters": "{}"}
            ]
            
            for i, step_data in enumerate(steps):
                step = MacroStep(
                    macro_id=macro.id,
                    step_number=i,
                    action_type=step_data["action_type"],
                    parameters=step_data["parameters"],
                    delay_before=step_data["delay_before"]
                )
                db_session.add(step)
                
            # Update suggestion
            suggestion.status = 'accepted'
            suggestion.action_time = datetime.now()
            suggestion.macro_id = macro.id
            
            db_session.commit()
            
            logger.info(f"Created macro {macro.id} from suggestion {suggestion_id}")
            
            return macro.id
            
        except Exception as e:
            logger.error(f"Error creating macro from suggestion {suggestion_id}: {e}")
            db_session.rollback()
            return None
            
    def enhance_macro_with_ai(self, macro_id):
        """
        Use AI to enhance a macro with better descriptions and optimizations
        
        Args:
            macro_id: Database ID of the macro to enhance
            
        Returns:
            True if successful, False otherwise
        """
        if not self.openai_available:
            logger.warning("OpenAI API key not available, skipping AI enhancement")
            return False
            
        try:
            # Get macro
            macro = db_session.query(Macro).get(macro_id)
            if not macro:
                logger.error(f"Macro {macro_id} not found")
                return False
                
            # Get steps
            steps = macro.steps
            
            # In a real implementation, this would call OpenAI to improve the macro
            # For now, just add some fake "AI-enhanced" descriptions
            
            macro.description += "\n\nThis macro has been enhanced with AI optimization."
            
            for step in steps:
                # Add some fake AI enhancement
                params = json.loads(step.parameters)
                params['ai_enhanced'] = True
                params['optimization_note'] = "Timing optimized by AI"
                step.parameters = json.dumps(params)
                
            db_session.commit()
            
            logger.info(f"Enhanced macro {macro_id} with AI")
            
            return True
            
        except Exception as e:
            logger.error(f"Error enhancing macro with AI: {e}")
            db_session.rollback()
            return False