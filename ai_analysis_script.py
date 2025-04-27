#!/usr/bin/env python3
"""
Script to analyze patterns and sequences using OpenAI API and store the results in the database.
This script is independent of the main application and can be run separately.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

import openai
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY environment variable not set")
    exit(1)

client = OpenAI(api_key=api_key)
logger.info("OpenAI client initialized")

# Initialize database connection
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    logger.error("DATABASE_URL environment variable not set")
    exit(1)

engine = create_engine(db_url)
Session = scoped_session(sessionmaker(bind=engine))
db_session = Session()
logger.info("Database connection initialized")

def analyze_pattern_with_openai(pattern_data: Dict[str, Any], sequences_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze pattern data using OpenAI API.
    
    Args:
        pattern_data: Dictionary containing pattern data
        sequences_data: List of dictionaries containing sequence data
        
    Returns:
        Dictionary containing analysis results
    """
    # Prepare a prompt for OpenAI
    prompt = f"""
    I need you to analyze a workflow pattern detected in user behavior. The pattern has been identified across multiple sequences of user actions.

    Pattern Details:
    - Name: {pattern_data['name']}
    - Score: {pattern_data['score']}
    - Status: {pattern_data['status']}
    - Detection Time: {pattern_data['detection_time']}

    Sequence Data:
    """
    
    for i, seq in enumerate(sequences_data):
        prompt += f"\nSequence {i+1}:\n"
        prompt += f"- Start Time: {seq['start_time']}\n"
        prompt += f"- End Time: {seq['end_time']}\n"
        prompt += f"- Windows: {', '.join(json.loads(seq['meta_data']).get('windows', []))}\n"
        prompt += "- Events:\n"
        
        events = json.loads(seq['data'])
        for event in events:
            event_desc = f"  - {event['type']}"
            if event['type'] == 'window_change':
                event_desc += f": {event.get('window', 'Unknown')}"
            elif event['type'] in ['mouse_click', 'mouse_move']:
                event_desc += f": ({event.get('x', 0)}, {event.get('y', 0)})"
                if event['type'] == 'mouse_click':
                    event_desc += f", {event.get('button', 'left')} button"
            elif event['type'] in ['key_press', 'key_release']:
                event_desc += f": {event.get('key', 'Unknown')}"
            prompt += event_desc + "\n"
    
    prompt += """
    Based on the pattern and sequences above, please provide:
    1. A concise summary of the detected pattern (what the user is doing)
    2. Key insights on this behavior pattern
    3. Automation potential (score from 0.0 to 1.0, where 1.0 is highly automatable)
    4. Recommendations for automating this workflow
    5. Potential benefits of automation (time saving, error reduction, etc.)
    
    Format your response as a JSON object with the following structure:
    {
        "summary": "brief description",
        "insights": "key insights about the pattern",
        "automation_potential": float between 0 and 1,
        "recommendations": "suggestions for automation",
        "benefits": "potential benefits of automation"
    }
    """
    
    logger.info(f"Sending prompt to OpenAI API for pattern {pattern_data['name']}")
    
    try:
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": "You are an expert in workflow analysis and automation."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        analysis_data = json.loads(response.choices[0].message.content)
        logger.info(f"Received response from OpenAI API for pattern {pattern_data['name']}")
        
        return analysis_data
    
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return {
            "summary": "Error analyzing pattern",
            "insights": f"An error occurred during analysis: {e}",
            "automation_potential": 0.0,
            "recommendations": "Unable to provide recommendations due to analysis error",
            "benefits": "Unable to determine benefits due to analysis error"
        }

def store_analysis_in_database(pattern_id: int, analysis_data: Dict[str, Any]) -> None:
    """
    Store analysis data in the database.
    
    Args:
        pattern_id: ID of the pattern being analyzed
        analysis_data: Dictionary containing analysis results
    """
    try:
        # Check if an analysis report already exists for this pattern
        existing_report = db_session.execute(
            text("SELECT id FROM ai_analysis_reports WHERE report_type = 'pattern' AND source_id = :pattern_id"),
            {"pattern_id": pattern_id}
        ).fetchone()
        
        if existing_report:
            # Update existing report
            db_session.execute(
                text("""
                UPDATE ai_analysis_reports 
                SET analysis_data = :analysis_data,
                    summary = :summary,
                    insights = :insights,
                    automation_potential = :potential,
                    timestamp = :timestamp
                WHERE id = :report_id
                """),
                {
                    "analysis_data": json.dumps(analysis_data),
                    "summary": analysis_data.get("summary", ""),
                    "insights": analysis_data.get("insights", ""),
                    "potential": analysis_data.get("automation_potential", 0.0),
                    "timestamp": datetime.now(),
                    "report_id": existing_report[0]
                }
            )
            logger.info(f"Updated existing analysis report for pattern {pattern_id}")
        else:
            # Create new report
            db_session.execute(
                text("""
                INSERT INTO ai_analysis_reports 
                (report_type, source_id, timestamp, analysis_data, summary, insights, automation_potential, application_context)
                VALUES 
                (:report_type, :source_id, :timestamp, :analysis_data, :summary, :insights, :potential, :context)
                """),
                {
                    "report_type": "pattern",
                    "source_id": pattern_id,
                    "timestamp": datetime.now(),
                    "analysis_data": json.dumps(analysis_data),
                    "summary": analysis_data.get("summary", ""),
                    "insights": analysis_data.get("insights", ""),
                    "potential": analysis_data.get("automation_potential", 0.0),
                    "context": analysis_data.get("application_context", "Multiple applications")
                }
            )
            logger.info(f"Created new analysis report for pattern {pattern_id}")
        
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error storing analysis in database: {e}")

def main():
    """Main function to analyze patterns and store results."""
    try:
        # Get all patterns
        pattern_rows = db_session.execute(text("SELECT * FROM patterns")).fetchall()
        logger.info(f"Found {len(pattern_rows)} patterns to analyze")
        
        for pattern_row in pattern_rows:
            # Convert row to dict properly
            pattern_dict = {}
            for column, value in pattern_row._mapping.items():
                pattern_dict[column] = value
                
            pattern_id = pattern_dict['id']
            logger.info(f"Processing pattern {pattern_id}: {pattern_dict['name']}")
            
            # Get the sequences for this pattern
            try:
                sequence_ids = json.loads(pattern_dict.get('sequence_ids', '[]'))
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding sequence_ids for pattern {pattern_id}: {e}")
                logger.info(f"Raw sequence_ids value: {pattern_dict.get('sequence_ids')}")
                continue
                
            if not sequence_ids:
                logger.warning(f"Pattern {pattern_id} has no sequences")
                continue
            
            # Prepare a comma-separated list of sequence IDs
            seq_id_list = ', '.join(str(seq_id) for seq_id in sequence_ids)
            
            # Get the sequences
            sequence_rows = db_session.execute(
                text(f"SELECT * FROM event_sequences WHERE id IN ({seq_id_list})")
            ).fetchall()
            
            if not sequence_rows:
                logger.warning(f"No sequences found for pattern {pattern_id}")
                continue
            
            logger.info(f"Analyzing pattern {pattern_id} with {len(sequence_rows)} sequences")
            
            # Convert sequences to dictionaries properly
            sequence_dicts = []
            for seq_row in sequence_rows:
                seq_dict = {}
                for column, value in seq_row._mapping.items():
                    seq_dict[column] = value
                sequence_dicts.append(seq_dict)
            
            # Analyze the pattern
            analysis_data = analyze_pattern_with_openai(pattern_dict, sequence_dicts)
            
            # Store the analysis in the database
            store_analysis_in_database(pattern_id, analysis_data)
            
            logger.info(f"Completed analysis for pattern {pattern_id}")
    
    except Exception as e:
        logger.error(f"Error in main function: {e}")
    finally:
        db_session.close()

if __name__ == "__main__":
    main()