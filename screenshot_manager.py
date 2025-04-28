import os
import json
import base64
import logging
from datetime import datetime
from database import session_scope
from models import AIAnalysisReport, Event
from ai_llm import ai_llm

logger = logging.getLogger(__name__)

class ScreenshotManager:
    """
    Manages capturing and analyzing screenshots of user actions
    """
    def __init__(self, settings):
        self.settings = settings
        self.screenshot_dir = os.path.join(os.getcwd(), 'logs', 'screenshots')
        self.ensure_directory_exists()
        
    def ensure_directory_exists(self):
        """Ensure the screenshot directory exists"""
        if not os.path.exists(self.screenshot_dir):
            try:
                os.makedirs(self.screenshot_dir)
                logger.info(f"Created screenshot directory: {self.screenshot_dir}")
            except Exception as e:
                logger.error(f"Error creating screenshot directory: {e}")
                
    def save_screenshot(self, screenshot_base64, event_data):
        """
        Save a screenshot to disk
        
        Args:
            screenshot_base64: Base64 encoded screenshot data
            event_data: Event data associated with the screenshot
            
        Returns:
            Path to the saved screenshot or None if failed
        """
        try:
            # Get timestamp and event type for filename
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            event_type = event_data.get('type', 'unknown')
            
            # Create filename
            filename = f"{timestamp}_{event_type}.jpg"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # Save the image
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(screenshot_base64))
                
            # Create metadata file
            metadata_path = f"{filepath}.json"
            with open(metadata_path, "w") as f:
                json.dump(event_data, f, indent=2)
                
            logger.debug(f"Saved screenshot and metadata: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return None
            
    def analyze_screenshot(self, screenshot_path, event_data):
        """
        Analyze a screenshot using AI
        
        Args:
            screenshot_path: Path to the screenshot
            event_data: Event data associated with the screenshot
            
        Returns:
            Analysis results or None if AI is not available
        """
        try:
            # Check if OpenAI API is available
            
            if not ai_llm.is_available():
                logger.warning("OpenAI API not available for screenshot analysis")
                return None
                
            # Read the screenshot
            with open(screenshot_path, "rb") as f:
                screenshot_base64 = base64.b64encode(f.read()).decode('utf-8')
                
            # Analyze with AI
            analysis = ai_llm.analyze_screenshot(
                screenshot_base64=screenshot_base64,
                action_type=event_data.get('type', 'unknown'),
                action_params=event_data.get('data', {})
            )
            
            if analysis:
                # Save analysis to a JSON file
                analysis_path = f"{screenshot_path}.analysis.json"
                with open(analysis_path, "w") as f:
                    json.dump(analysis, f, indent=2)
                    
                logger.info(f"Screenshot analysis saved to {analysis_path}")
                
                # Try to convert automation_potential to a float if it exists
                automation_potential = 0.0
                if 'automation_potential' in analysis:
                    pot = analysis['automation_potential']
                    if isinstance(pot, str):
                        if pot.lower() == 'high':
                            automation_potential = 0.9
                        elif pot.lower() == 'medium':
                            automation_potential = 0.6
                        elif pot.lower() == 'low':
                            automation_potential = 0.3
                    else:
                        # Try to convert to float
                        try:
                            automation_potential = float(pot)
                        except (ValueError, TypeError):
                            automation_potential = 0.0
                
                # Create summary and insights from analysis
                summary = analysis.get('action_description', 'No description available')
                insights = analysis.get('insights', 'No insights available')
                app_context = analysis.get('application', 'Unknown application')
                
                # Save to database
                with session_scope() as db:
                    report = AIAnalysisReport(
                        report_type='screenshot',
                        source_id=event_data.get('id'),
                        source_path=screenshot_path,
                        analysis_data=json.dumps(analysis),
                        summary=summary,
                        insights=insights,
                        automation_potential=automation_potential,
                        application_context=app_context
                    )
                    db.add(report)
                    db.commit()
                    
                    # Update the event record if we have an ID
                    if 'id' in event_data:
                        try:
                            event = db.query(Event).get(event_data['id'])
                            if event:
                                event.has_screenshot = 1
                                event.analysis_report_id = report.id
                                db.commit()
                        except Exception as db_error:
                            logger.error(f"Error updating event record: {db_error}")
                
                logger.info(f"Screenshot analysis saved to database with ID {report.id}")
                
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {e}")
            return None