#!/usr/bin/env python3
"""
AI LLM Helper Module for BettermanAI
Provides integrated functionality for all OpenAI API interactions in the application.
This module combines functionality from the previous ai_helper.py and ai_analysis_script.py.
"""

import os
import json
import logging
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional

from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

from database import session_scope

# Configure logging
logger = logging.getLogger(__name__)

# The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# Do not change this unless explicitly requested by the user
DEFAULT_MODEL = "gpt-4o"

class AILLMHelper:
    """
    Integrated helper class for all AI-related functionality using OpenAI's API.
    """
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized")
        else:
            logger.warning("OpenAI API key not available")
            
    def is_available(self) -> bool:
        """Check if OpenAI API is available"""
        return self.client is not None
        
    def enhance_macro_description(self, 
                                 macro_name: str, 
                                 current_description: str, 
                                 steps: List[Dict[str, Any]]) -> Optional[str]:
        """
        Use AI to enhance a macro description.
        
        Args:
            macro_name: Name of the macro
            current_description: Current description of the macro
            steps: List of steps in the macro
            
        Returns:
            Enhanced description or None if API is not available
        """
        if not self.is_available():
            return None
            
        try:
            steps_text = ""
            for i, step in enumerate(steps):
                step_desc = f"Step {i+1}: {step['action_type']}"
                if 'parameters' in step and step['parameters']:
                    try:
                        params = json.loads(step['parameters'])
                        step_desc += f" with parameters: {json.dumps(params, indent=2)}"
                    except:
                        step_desc += f" with parameters: {step['parameters']}"
                if 'delay_before' in step:
                    step_desc += f" (delay: {step['delay_before']}s)"
                steps_text += step_desc + "\n"
                
            prompt = f"""
            You are an AI assistant that helps optimize workflows and automation.
            
            Please enhance the following macro description to make it more clear, 
            detailed, and provide insights on its purpose and potential benefits.
            
            Macro Name: {macro_name}
            Current Description: {current_description}
            
            Steps:
            {steps_text}
            
            Please provide:
            1. An improved description that explains what this automation does in clear language
            2. The potential benefits of this automation (time savings, reduced errors, etc.)
            3. Any suggestions for further optimization or improvements
            
            Format your response as plain text that can be used directly as the new macro description.
            """
            
            response = self.client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            
            enhanced_description = response.choices[0].message.content.strip()
            return enhanced_description
            
        except Exception as e:
            logger.error(f"Error enhancing macro description: {e}")
            return None
            
    def enhance_macro_steps(self, 
                           macro_name: str, 
                           steps: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        Use AI to enhance macro steps.
        
        Args:
            macro_name: Name of the macro
            steps: List of steps in the macro
            
        Returns:
            Enhanced steps or None if API is not available
        """
        if not self.is_available():
            return None
            
        try:
            steps_text = ""
            for i, step in enumerate(steps):
                step_desc = f"Step {i+1}: {step['action_type']}"
                if 'parameters' in step and step['parameters']:
                    try:
                        params = json.loads(step['parameters'])
                        step_desc += f" with parameters: {json.dumps(params, indent=2)}"
                    except:
                        step_desc += f" with parameters: {step['parameters']}"
                if 'delay_before' in step:
                    step_desc += f" (delay: {step['delay_before']}s)"
                steps_text += step_desc + "\n"
                
            prompt = f"""
            You are an AI assistant that helps optimize workflows and automation.
            
            Please analyze and enhance the following macro steps to make them more efficient.
            
            Macro Name: {macro_name}
            
            Current Steps:
            {steps_text}
            
            Please suggest any improvements to these steps, such as:
            1. Optimizing delay times
            2. Adding helpful properties to parameters
            3. Improving the overall flow of the automation
            
            Return your response as a JSON array of steps with the same structure, but with your improvements.
            Each step should have: action_type, parameters (as a JSON string), and delay_before (in seconds).
            """
            
            response = self.client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Parse the response content
            try:
                result = json.loads(response_content)
                if "steps" in result:
                    return result["steps"]
                return result
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON response from OpenAI")
                return None
                
        except Exception as e:
            logger.error(f"Error enhancing macro steps: {e}")
            return None
            
    def analyze_pattern(self, 
                       pattern_name: str, 
                       sequences: List[Dict[str, Any]], 
                       score: float) -> Optional[Dict[str, Any]]:
        """
        Use AI to analyze a pattern and provide insights.
        
        Args:
            pattern_name: Name of the pattern
            sequences: List of sequences that match the pattern
            score: Similarity score of the pattern
            
        Returns:
            Analysis results or None if API is not available
        """
        if not self.is_available():
            return None
            
        try:
            sequences_text = json.dumps(sequences, indent=2)
            
            prompt = f"""
            You are an AI assistant that helps analyze user behavior patterns.
            
            Please analyze the following pattern of user actions and provide insights:
            
            Pattern Name: {pattern_name}
            Similarity Score: {score}
            
            Sequences:
            {sequences_text}
            
            Please provide:
            1. A clear description of what this pattern represents
            2. The potential automation opportunity (what could be automated)
            3. The potential benefits of automating this pattern
            4. Any potential challenges or considerations for automation
            
            Return your analysis as a JSON object with the following fields:
            - description: A clear description of the pattern
            - automation_opportunity: What could be automated
            - benefits: Potential benefits of automation
            - challenges: Potential challenges or considerations
            - improved_name: A more descriptive name for this pattern
            """
            
            response = self.client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Parse the response content
            try:
                return json.loads(response_content)
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON response from OpenAI")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing pattern: {e}")
            return None
    
    def analyze_pattern_with_database(self, pattern_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze pattern data using OpenAI API and store the results in the database.
        
        Args:
            pattern_id: ID of the pattern to analyze
            
        Returns:
            Dictionary containing analysis results or None if API is not available
        """
        if not self.is_available():
            return None
            
        try:
            # Use session_scope from database.py
            with session_scope() as db:
                # Get pattern data from database
                pattern_query = """
                SELECT 
                    id, name, detection_count, last_detected,
                    similarity_score, confidence, status
                FROM 
                    pattern
                WHERE 
                    id = :pattern_id
                """
                
                pattern_result = db.execute(text(pattern_query), {"pattern_id": pattern_id}).mappings().first()
                
                if not pattern_result:
                    logger.error(f"Pattern with ID {pattern_id} not found")
                    return None
                
                # Get sequences for this pattern
                sequences_query = """
                SELECT 
                    id, pattern_id, start_time, end_time, 
                    event_count, sequence_data
                FROM 
                    sequence
                WHERE 
                    pattern_id = :pattern_id
                LIMIT 5
                """
                
                sequences_result = db.execute(text(sequences_query), {"pattern_id": pattern_id}).mappings().all()
                
                # Convert sequences to a list of dictionaries and parse sequence_data JSON
                sequences_data = []
                for seq in sequences_result:
                    seq_dict = dict(seq)
                    if seq_dict.get('sequence_data'):
                        try:
                            seq_dict['sequence_data'] = json.loads(seq_dict['sequence_data'])
                        except:
                            # Keep as is if not valid JSON
                            pass
                    sequences_data.append(seq_dict)
                
                # No sequences found, can't analyze
                if not sequences_data:
                    logger.error(f"No sequences found for pattern with ID {pattern_id}")
                    return None
                
                # Perform AI analysis with the data
                pattern_data = dict(pattern_result)
                
                return self.analyze_pattern(
                    pattern_name=pattern_data.get('name', f"Pattern {pattern_id}"),
                    sequences=sequences_data,
                    score=pattern_data.get('similarity_score', 0.5)
                )
                
        except Exception as e:
            logger.error(f"Error in analyze_pattern_with_database: {e}")
            return None
    
    def store_analysis_in_database(self, pattern_id: int, analysis_data: Dict[str, Any]) -> bool:
        """
        Store analysis data in the database.
        
        Args:
            pattern_id: ID of the pattern being analyzed
            analysis_data: Dictionary containing analysis results
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Use session_scope from database.py
            with session_scope() as db:
                # First, check if the pattern exists
                pattern_check = db.execute(
                    text("SELECT id FROM pattern WHERE id = :pattern_id"),
                    {"pattern_id": pattern_id}
                ).scalar()
                
                if not pattern_check:
                    logger.error(f"Pattern with ID {pattern_id} not found")
                    return False
                
                # Convert analysis data to JSON
                analysis_json = json.dumps(analysis_data)
                
                # Update pattern with analysis
                db.execute(
                    text("""
                    UPDATE pattern 
                    SET 
                        ai_analysis = :analysis,
                        updated_at = NOW()
                    WHERE id = :pattern_id
                    """),
                    {
                        "pattern_id": pattern_id,
                        "analysis": analysis_json
                    }
                )
                
                # Also update the pattern name if improved_name is provided
                if 'improved_name' in analysis_data and analysis_data['improved_name']:
                    db.execute(
                        text("""
                        UPDATE pattern 
                        SET 
                            name = :name,
                            updated_at = NOW()
                        WHERE id = :pattern_id
                        """),
                        {
                            "pattern_id": pattern_id,
                            "name": analysis_data['improved_name']
                        }
                    )
                
                # Log the analysis
                logger.info(f"Stored AI analysis for pattern {pattern_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing analysis in database: {e}")
            return False
            
    def analyze_screenshot(self, 
                         screenshot_base64: str, 
                         action_type: str, 
                         action_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Use AI to analyze a screenshot and action data.
        
        Args:
            screenshot_base64: Base64 encoded screenshot
            action_type: Type of action performed
            action_params: Parameters of the action
            
        Returns:
            Analysis results or None if API is not available
        """
        if not self.is_available():
            return None
            
        try:
            action_params_text = json.dumps(action_params, indent=2)
            
            prompt = f"""
            You are an AI assistant that helps analyze user interactions with computer interfaces.
            
            Please analyze the following screenshot and action data:
            
            Action Type: {action_type}
            Action Parameters: {action_params_text}
            
            The screenshot shows what the user was seeing when they performed this action.
            
            Based on the screenshot and action data, please:
            1. Describe what the user was doing
            2. Identify the application or website being used
            3. Suggest if this action could be part of an automation pattern
            4. Provide any insights that might help automate this workflow
            
            Return your analysis as a JSON object with the following fields:
            - action_description: What the user was doing
            - application: The application or website being used
            - automation_potential: Whether this could be automated (high, medium, low)
            - insights: Any insights for automation
            """
            
            response = self.client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Parse the response content
            try:
                return json.loads(response_content)
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON response from OpenAI")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {e}")
            return None

# Singleton instance
ai_llm = AILLMHelper()