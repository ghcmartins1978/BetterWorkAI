import os
import logging
import json
import time
from datetime import datetime
import threading

from openai import OpenAI
from database import db_session
from models import Pattern, Suggestion

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """
    AI-powered reasoning engine for analyzing patterns and
    generating automation suggestions
    """
    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.evaluation_thread = None
        self.evaluation_interval = 300  # Check for patterns to evaluate every 5 minutes
        self.automation_executor = None
        
        # Initialize OpenAI client
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        if self.openai_api_key:
            self.openai = OpenAI(api_key=self.openai_api_key)
        else:
            logger.warning("OpenAI API key not found. AI reasoning will be limited.")
            self.openai = None
    
    def set_automation_executor(self, executor):
        """Set the automation executor for suggestion implementation"""
        self.automation_executor = executor
        
    def start(self):
        """Start the reasoning engine"""
        if self.running:
            return
            
        logger.info("Starting reasoning engine")
        self.running = True
        
        # Start evaluation thread
        self.evaluation_thread = threading.Thread(target=self._evaluation_loop, daemon=True)
        self.evaluation_thread.start()
        
    def stop(self):
        """Stop the reasoning engine"""
        logger.info("Stopping reasoning engine")
        self.running = False
        
    def evaluate_pattern(self, pattern_id):
        """
        Evaluate a detected pattern to determine if it can be automated
        
        Args:
            pattern_id: Database ID of the pattern to evaluate
        """
        if not self.running:
            return
            
        try:
            # Get pattern from database
            pattern = db_session.query(Pattern).get(pattern_id)
            
            if not pattern or pattern.status not in ['detected', 'pending_evaluation']:
                return
                
            logger.info(f"Evaluating pattern {pattern_id}")
            
            # Update pattern status
            pattern.status = 'evaluating'
            db_session.commit()
            
            # Get sequences for this pattern
            sequence_ids = json.loads(pattern.sequence_ids)
            
            if not sequence_ids or len(sequence_ids) < 2:
                pattern.status = 'rejected'
                pattern.evaluation_notes = "Insufficient sequences for evaluation"
                db_session.commit()
                return
                
            # Get sequence data
            sequences = []
            from models import EventSequence
            
            for seq_id in sequence_ids[:3]:  # Limit to first 3 sequences to keep analysis manageable
                seq = db_session.query(EventSequence).get(seq_id)
                if seq:
                    try:
                        seq_data = json.loads(seq.data)
                        seq_metadata = json.loads(seq.metadata)
                        sequences.append({
                            'id': seq.id,
                            'metadata': seq_metadata,
                            'sample_events': seq_data[:20] if len(seq_data) > 20 else seq_data
                        })
                    except Exception as e:
                        logger.error(f"Error processing sequence {seq_id}: {e}")
            
            if not sequences:
                pattern.status = 'rejected'
                pattern.evaluation_notes = "Failed to load sequence data"
                db_session.commit()
                return
                
            # Analyze pattern using AI if available
            if self.openai:
                analysis_result = self._analyze_with_ai(pattern, sequences)
            else:
                # Simple heuristic-based analysis
                analysis_result = self._analyze_with_heuristics(pattern, sequences)
                
            # Process analysis result
            if analysis_result.get('is_automatable', False):
                pattern.status = 'approved'
                pattern.evaluation_notes = analysis_result.get('notes', '')
                
                # Create suggestion
                suggestion = Suggestion(
                    pattern_id=pattern.id,
                    title=analysis_result.get('title', f"Automation for {pattern.name}"),
                    description=analysis_result.get('description', ''),
                    steps=json.dumps(analysis_result.get('steps', [])),
                    creation_time=datetime.now(),
                    status='pending'
                )
                db_session.add(suggestion)
                db_session.commit()
                
                # Notify user about suggestion
                if self.automation_executor:
                    self.automation_executor.notify_suggestion(suggestion.id)
            else:
                pattern.status = 'rejected'
                pattern.evaluation_notes = analysis_result.get('notes', 'Not automatable')
                db_session.commit()
                
        except Exception as e:
            logger.error(f"Error evaluating pattern {pattern_id}: {e}")
            
            # Update pattern status on error
            try:
                pattern = db_session.query(Pattern).get(pattern_id)
                pattern.status = 'error'
                pattern.evaluation_notes = f"Error during evaluation: {str(e)}"
                db_session.commit()
            except:
                pass
    
    def _evaluation_loop(self):
        """Thread function to periodically evaluate pending patterns"""
        while self.running:
            try:
                # Find patterns pending evaluation
                patterns = db_session.query(Pattern).filter(
                    Pattern.status.in_(['detected', 'pending_evaluation'])
                ).order_by(Pattern.detection_time.asc()).limit(5).all()
                
                for pattern in patterns:
                    if self.running:
                        self.evaluate_pattern(pattern.id)
                        
                        # Sleep briefly between evaluations to avoid overwhelming the system
                        time.sleep(5)
                        
            except Exception as e:
                logger.error(f"Error in evaluation loop: {e}")
                
            # Sleep until next check
            time.sleep(self.evaluation_interval)
            
    def _analyze_with_ai(self, pattern, sequences):
        """
        Analyze pattern using OpenAI GPT-4o to determine if it can be automated
        
        Args:
            pattern: Pattern object from database
            sequences: List of sequence dictionaries with metadata and sample events
            
        Returns:
            Dictionary with analysis results including is_automatable flag
        """
        try:
            # Prepare prompt
            prompt = f"""
            You are an AI assistant for BettermanAI, a personal workflow automation tool.
            You need to analyze a detected pattern of user behavior to determine if it can be automated.
            
            PATTERN INFORMATION:
            Pattern ID: {pattern.id}
            Pattern Name: {pattern.name}
            Detection Time: {pattern.detection_time}
            Pattern Score: {pattern.score}
            
            SEQUENCE DATA:
            
            """
            
            # Add sequence information to prompt
            for idx, seq in enumerate(sequences):
                prompt += f"SEQUENCE {idx+1}:\n"
                prompt += f"ID: {seq['id']}\n"
                
                metadata = seq['metadata']
                prompt += f"Start Time: {metadata.get('start_time', 'unknown')}\n"
                prompt += f"Duration: {metadata.get('duration', 'unknown')} seconds\n"
                prompt += f"Event Count: {metadata.get('event_count', 0)}\n"
                prompt += f"Windows: {', '.join(metadata.get('windows', []))}\n"
                
                # Add sample events
                prompt += "SAMPLE EVENTS:\n"
                for i, event in enumerate(seq['sample_events'][:10]):  # Limit to first 10 events
                    prompt += f"  Event {i+1}: Type={event.get('type', 'unknown')}"
                    if 'window' in event:
                        prompt += f", Window={event.get('window', 'unknown')}"
                    if event.get('type') == 'mouse_click':
                        prompt += f", Position=({event.get('x', 0)}, {event.get('y', 0)})"
                    prompt += "\n"
                    
                prompt += "\n"
                
            # Add analysis request
            prompt += """
            TASK:
            1. Analyze if this pattern represents a repetitive task that can be automated.
            2. Determine if the pattern shows consistent interaction with the same UI elements.
            3. Assess if automating this pattern would save the user time.
            4. If automatable, suggest steps for automation.
            
            Respond in JSON format with the following structure:
            {
                "is_automatable": true/false,
                "title": "Brief title for the automation",
                "description": "Detailed description of what this automation would do",
                "notes": "Explanation of your analysis",
                "steps": ["Step 1", "Step 2", ...],
                "confidence": 0.0-1.0
            }
            """
            
            # Call OpenAI API
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are BettermanAI's workflow analysis assistant. You help identify automatable patterns in user behavior."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            result = json.loads(response_text)
            
            # Add logging
            logger.info(f"AI analysis for pattern {pattern.id}: is_automatable={result.get('is_automatable', False)}, confidence={result.get('confidence', 0)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return {
                "is_automatable": False,
                "notes": f"Error in AI analysis: {str(e)}",
                "confidence": 0
            }
    
    def _analyze_with_heuristics(self, pattern, sequences):
        """
        Analyze pattern using simple heuristics when AI is unavailable
        
        Args:
            pattern: Pattern object from database
            sequences: List of sequence dictionaries with metadata and sample events
            
        Returns:
            Dictionary with analysis results including is_automatable flag
        """
        # Extract key characteristics
        is_automatable = False
        notes = []
        
        # Check if sequences have consistent windows
        window_sets = []
        for seq in sequences:
            windows = seq['metadata'].get('windows', [])
            window_sets.append(set(windows))
            
        if window_sets:
            common_windows = set.intersection(*window_sets) if window_sets else set()
            if common_windows:
                notes.append(f"Consistent windows: {', '.join(common_windows)}")
            else:
                notes.append("Inconsistent windows across sequences")
                
        # Check event type consistency
        event_type_patterns = []
        for seq in sequences:
            event_types = [e.get('type', '') for e in seq.get('sample_events', [])]
            if event_types:
                event_type_pattern = ''.join([e[0] if e else '?' for e in event_types])
                event_type_patterns.append(event_type_pattern)
                
        if len(set(event_type_patterns)) == 1:
            notes.append("Consistent event pattern across sequences")
        else:
            notes.append("Inconsistent event patterns")
            
        # Check sequence lengths
        seq_lengths = [len(seq.get('sample_events', [])) for seq in sequences]
        length_variance = max(seq_lengths) / min(seq_lengths) if min(seq_lengths) > 0 else float('inf')
        
        if length_variance < 1.5:
            notes.append("Consistent sequence lengths")
        else:
            notes.append("Inconsistent sequence lengths")
            
        # Pattern must have a good score
        if pattern.score >= 0.7:
            notes.append(f"Good pattern score: {pattern.score:.2f}")
        else:
            notes.append(f"Weak pattern score: {pattern.score:.2f}")
            
        # Determine automation potential
        if (
            pattern.score >= 0.7 and
            common_windows and
            length_variance < 1.5 and
            len(set(event_type_patterns)) == 1
        ):
            is_automatable = True
            
        # Create result
        result = {
            "is_automatable": is_automatable,
            "title": f"Automate workflow in {', '.join(list(common_windows)[:2])}" if common_windows else f"Potential automation for {pattern.name}",
            "description": f"Automate a repetitive task that was detected {len(sequences)} times",
            "notes": " | ".join(notes),
            "steps": ["Start recording", "Execute steps", "Save automation"],
            "confidence": 0.5 if is_automatable else 0.1
        }
        
        return result
