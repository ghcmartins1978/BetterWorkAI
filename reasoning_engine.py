import logging
import json
import threading
import time
import os
from datetime import datetime

from database import db_session
from models import Pattern, Suggestion, Macro, MacroStep, EventSequence

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
                
            # Get sequences for AI analysis
            sequences = []
            event_count = 0
            
            try:
                for seq_id in sequence_ids:
                    seq = db_session.query(EventSequence).get(seq_id)
                    if seq:
                        # Use the first sequence to determine event count
                        if event_count == 0:
                            event_count = seq.event_count
                            
                        # Get the sequence data
                        if seq.data:
                            seq_data = json.loads(seq.data)
                            sequences.append(seq_data)
            except Exception as e:
                logger.error(f"Error getting sequences: {e}")
                
            if event_count == 0:
                event_count = "multiple"
                
            # Prepare suggestion with default values
            title = f"Automate {pattern.name}"
            description = f"This automation would replace a sequence of {event_count} events that you've performed {len(sequence_ids)} times."
            
            # Use AI to analyze the pattern if available
            ai_analysis = None
            if self.openai_available and sequences:
                from ai_helper import ai_helper
                
                try:
                    ai_analysis = ai_helper.analyze_pattern(
                        pattern_name=pattern.name,
                        sequences=sequences,
                        score=pattern.score
                    )
                    
                    if ai_analysis:
                        # Update pattern with AI insights
                        if 'improved_name' in ai_analysis and ai_analysis['improved_name']:
                            pattern.name = ai_analysis['improved_name']
                            title = f"Automate {pattern.name}"
                            
                        # Build better description with AI insights
                        if 'description' in ai_analysis and ai_analysis['description']:
                            description = ai_analysis['description'] + "\n\n"
                            
                        if 'automation_opportunity' in ai_analysis and ai_analysis['automation_opportunity']:
                            description += f"Automation opportunity: {ai_analysis['automation_opportunity']}\n\n"
                            
                        if 'benefits' in ai_analysis and ai_analysis['benefits']:
                            description += f"Benefits: {ai_analysis['benefits']}\n\n"
                            
                        if 'challenges' in ai_analysis and ai_analysis['challenges']:
                            description += f"Considerations: {ai_analysis['challenges']}"
                            
                        # Store AI analysis in evaluation notes
                        pattern.evaluation_notes = f"AI Analysis: {json.dumps(ai_analysis)}"
                        logger.info(f"Enhanced pattern {pattern_id} with AI analysis")
                except Exception as ai_error:
                    logger.error(f"Error analyzing pattern with AI: {ai_error}")
                    # Continue with default description if AI analysis fails
            
            # Check if suggestion already exists for this pattern
            existing_suggestion = db_session.query(Suggestion).filter(
                Suggestion.pattern_id == pattern_id
            ).first()
            
            if existing_suggestion:
                logger.debug(f"Suggestion already exists for pattern {pattern_id}")
                return
                
            # Create steps for the suggestion
            steps = [
                {"type": "start", "description": "Start automation"},
                {"type": "execute", "description": f"Execute {event_count} actions"},
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
            if not pattern.evaluation_notes:
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
            
            # Use OpenAI to enhance the macro
            from ai_helper import ai_helper
            
            # Convert steps for AI processing
            steps_data = []
            for step in steps:
                step_data = {
                    'action_type': step.action_type,
                    'parameters': step.parameters,
                    'delay_before': step.delay_before
                }
                steps_data.append(step_data)
            
            # Enhance description
            enhanced_description = ai_helper.enhance_macro_description(
                macro_name=macro.name,
                current_description=macro.description,
                steps=steps_data
            )
            
            if enhanced_description:
                macro.description = enhanced_description
                logger.info(f"Enhanced macro {macro_id} description with AI")
            
            # Enhance steps
            enhanced_steps = ai_helper.enhance_macro_steps(
                macro_name=macro.name,
                steps=steps_data
            )
            
            if enhanced_steps:
                # Update steps with enhanced parameters
                for i, step in enumerate(steps):
                    if i < len(enhanced_steps):
                        enhanced_step = enhanced_steps[i]
                        
                        # Update delay if provided
                        if 'delay_before' in enhanced_step:
                            try:
                                delay = float(enhanced_step['delay_before'])
                                step.delay_before = delay
                            except:
                                pass
                            
                        # Update parameters if provided
                        if 'parameters' in enhanced_step:
                            try:
                                # If parameters is a string, use it directly
                                if isinstance(enhanced_step['parameters'], str):
                                    step.parameters = enhanced_step['parameters']
                                # If parameters is a dict, convert to JSON string
                                elif isinstance(enhanced_step['parameters'], dict):
                                    step.parameters = json.dumps(enhanced_step['parameters'])
                            except:
                                pass
                
                logger.info(f"Enhanced macro {macro_id} steps with AI")
            
            db_session.commit()
            logger.info(f"Successfully enhanced macro {macro_id} with AI")
            
            return True
            
        except Exception as e:
            logger.error(f"Error enhancing macro with AI: {e}")
            db_session.rollback()
            return False