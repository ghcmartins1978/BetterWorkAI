import os
import time
import json
import threading
import logging
import base64
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort, send_file, Response
import signal
import sys
import random

from database import init_db, db_session
from sqlalchemy import func
from models import Event, EventSequence, Pattern, Suggestion, Macro, MacroStep, Setting, AIAnalysisReport, MacroVariable, MacroExecution, Metric
import variable_detector
from settings import Settings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create and configure Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "betterman_ai_secret")

# Register custom filters
@app.template_filter('basename')
def basename_filter(path):
    """Get the basename of a path"""
    return os.path.basename(path) if path else ""
    
# Define template context processor to make functions available in templates
@app.context_processor
def utility_processor():
    def get_recent_executions(macro_id, limit=5):
        """Get recent executions for a macro, for use in templates"""
        try:
            return db_session.query(MacroExecution).filter_by(macro_id=macro_id).order_by(MacroExecution.start_time.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent executions: {e}")
            return []
    
    return dict(get_recent_executions=get_recent_executions)

# Initialize database
init_db()

# Check and update database schema if needed
from database import check_and_update_schema, async_db_writer
check_and_update_schema()

# Start async database writer
async_db_writer.start()

# Initialize settings
from settings import Settings
settings = Settings()

# Define the seed_demo_data function
def seed_demo_data():
    """Add demo data to the database if tables are empty"""
    try:
        # Check if we need to seed data
        if db_session.query(Pattern).count() == 0:
            logger.info("Seeding demo data...")
            
            # Add initial metrics if not present
            if db_session.query(Metric).filter(Metric.name == 'hours_saved_total').count() == 0:
                hours_saved_metric = Metric(
                    name='hours_saved_total',
                    value=5.2,  # Initial demo value
                    notes='Total hours saved by all macro executions'
                )
                db_session.add(hours_saved_metric)
                db_session.commit()
            
            # Create demo patterns
            patterns = [
                {
                    'name': 'Daily Data Entry Sequence',
                    'description': 'Pattern detected in spreadsheet data entry. You frequently copy data from emails, input into specific columns, and save the file.',
                    'score': 0.87,
                    'status': 'approved',
                    'detection_time': datetime.now() - timedelta(days=2, hours=3),
                    'last_match_time': datetime.now() - timedelta(hours=4),
                    'evaluation_notes': 'This pattern shows a highly structured data entry workflow that could be automated to save approximately 15 minutes daily.'
                },
                {
                    'name': 'Meeting Preparation Workflow',
                    'description': 'You follow a consistent sequence before meetings: opening calendar, checking email, opening the meeting document, and taking notes in a specific format.',
                    'score': 0.75,
                    'status': 'evaluating',
                    'detection_time': datetime.now() - timedelta(days=1, hours=7),
                    'last_match_time': datetime.now() - timedelta(hours=12),
                    'evaluation_notes': 'This pattern is being evaluated for automation potential. There appears to be a consistent structure suitable for partial automation.'
                },
                {
                    'name': 'Email Filing Routine',
                    'description': 'Pattern detected in email management. You regularly move emails to specific folders based on sender or subject keywords.',
                    'score': 0.92,
                    'status': 'approved',
                    'detection_time': datetime.now() - timedelta(days=4, hours=2),
                    'last_match_time': datetime.now() - timedelta(hours=1),
                    'evaluation_notes': 'This pattern shows a highly consistent email filing workflow that could be automated to save time daily.'
                },
                {
                    'name': 'Social Media Posting Workflow',
                    'description': 'You follow a specific sequence when posting content across multiple social media platforms, including copy-paste operations and formatting changes.',
                    'score': 0.68,
                    'status': 'detected',
                    'detection_time': datetime.now() - timedelta(hours=8),
                    'sequence_ids': json.dumps([15, 23, 41]),
                    'evaluation_notes': ''
                },
                {
                    'name': 'Invoice Processing Sequence',
                    'description': 'Pattern detected when processing invoices. You download PDFs, extract specific information, and enter it into an accounting system.',
                    'score': 0.82,
                    'status': 'approved',
                    'detection_time': datetime.now() - timedelta(days=6, hours=5),
                    'last_match_time': datetime.now() - timedelta(days=1, hours=3),
                    'evaluation_notes': 'This pattern involves consistent PDF data extraction and entry. Automation could reduce errors and save significant time.'
                },
                {
                    'name': 'Web Research Collection',
                    'description': 'Pattern detected in research workflow. You search for specific terms, save articles to read later, and create summaries.',
                    'score': 0.61,
                    'status': 'rejected',
                    'detection_time': datetime.now() - timedelta(days=8, hours=12),
                    'evaluation_notes': 'This pattern has too many variations and requires significant human judgment. Not suitable for automation at this time.'
                }
            ]
            
            created_patterns = []
            for pattern_data in patterns:
                pattern = Pattern(**pattern_data)
                db_session.add(pattern)
                db_session.flush()
                created_patterns.append(pattern)
            
            # Create demo suggestions
            suggestions = [
                {
                    'pattern_id': created_patterns[0].id,
                    'title': 'Automate Daily Data Entry',
                    'description': 'This automation will extract data from emails matching specific patterns and input it into your spreadsheet automatically, saving you approximately 15 minutes daily.',
                    'steps': json.dumps([
                        'Monitor for new emails matching the pattern',
                        'Extract data from email content based on template',
                        'Open the spreadsheet application',
                        'Input data into the corresponding columns',
                        'Save the file'
                    ]),
                    'creation_time': datetime.now() - timedelta(days=2),
                    'notification_time': datetime.now() - timedelta(days=2),
                    'status': 'pending'
                },
                {
                    'pattern_id': created_patterns[2].id,
                    'title': 'Email Auto-Filing Assistant',
                    'description': 'This automation will monitor your inbox and automatically file emails into appropriate folders based on sender, subject, and content patterns you have established.',
                    'steps': json.dumps([
                        'Monitor incoming emails',
                        'Match against filing rules based on your patterns',
                        'Move emails to appropriate folders',
                        'Provide a daily summary of filed emails'
                    ]),
                    'creation_time': datetime.now() - timedelta(days=3, hours=6),
                    'notification_time': datetime.now() - timedelta(days=3, hours=5),
                    'status': 'accepted',
                    'action_time': datetime.now() - timedelta(days=3, hours=4)
                },
                {
                    'pattern_id': created_patterns[4].id,
                    'title': 'Invoice Data Extraction Tool',
                    'description': 'This automation will extract key information from invoice PDFs (date, amount, vendor, invoice number) and enter it into your accounting system, reducing errors and saving time.',
                    'steps': json.dumps([
                        'Monitor download folder for new invoice PDFs',
                        'Extract key information using template matching',
                        'Open accounting software and navigate to entry form',
                        'Input extracted data into appropriate fields',
                        'Save the entry and file the PDF in organized storage'
                    ]),
                    'creation_time': datetime.now() - timedelta(days=5, hours=18),
                    'notification_time': datetime.now() - timedelta(days=5, hours=17),
                    'status': 'rejected',
                    'action_time': datetime.now() - timedelta(days=5, hours=6)
                },
                {
                    'pattern_id': created_patterns[1].id,
                    'title': 'Meeting Prep Assistant',
                    'description': 'This automation will prepare for your meetings by opening relevant documents, gathering recent emails from attendees, and creating a note-taking template.',
                    'steps': json.dumps([
                        'Monitor calendar for upcoming meetings',
                        'Search and open relevant documents based on meeting title/participants',
                        'Retrieve recent emails from meeting participants',
                        'Create and format note-taking document',
                        'Display meeting preparation dashboard 5 minutes before start'
                    ]),
                    'creation_time': datetime.now() - timedelta(days=1, hours=3),
                    'notification_time': datetime.now() - timedelta(days=1, hours=2),
                    'status': 'pending'
                }
            ]
            
            created_suggestions = []
            for suggestion_data in suggestions:
                suggestion = Suggestion(**suggestion_data)
                db_session.add(suggestion)
                db_session.flush()
                created_suggestions.append(suggestion)
            
            # Create demo macros
            macros = [
                {
                    'name': 'Email Filing Automation',
                    'description': 'Automatically files emails from specific senders into designated folders',
                    'creation_time': datetime.now() - timedelta(days=3, hours=2),
                    'last_execution_time': datetime.now() - timedelta(hours=3),
                    'execution_count': 42,
                    'success_count': 39,
                    'failure_count': 3,
                    'step_count': 8,
                    'status': 'recorded',
                    'original_sequence_duration': 45.0,  # 45 seconds per manual execution
                    'total_time_saved': 1560.0  # (45 secs * 39 successful executions) = 1755 - overhead
                },
                {
                    'name': 'Daily Report Generator',
                    'description': 'Extracts data from multiple sources and compiles it into a daily report',
                    'creation_time': datetime.now() - timedelta(days=10, hours=5),
                    'last_execution_time': datetime.now() - timedelta(hours=22),
                    'execution_count': 28,
                    'success_count': 24,
                    'failure_count': 4,
                    'step_count': 12,
                    'status': 'recorded',
                    'original_sequence_duration': 180.0,  # 3 minutes per manual execution
                    'total_time_saved': 4200.0  # (180 secs * 24 successful executions) = 4320 - overhead
                },
                {
                    'name': 'Invoice Data Entry',
                    'description': 'Extracts data from invoice PDFs and enters it into accounting software',
                    'creation_time': datetime.now() - timedelta(days=15, hours=8),
                    'last_execution_time': None,
                    'execution_count': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'step_count': 0,
                    'status': 'recording',
                    'original_sequence_duration': 0.0,
                    'total_time_saved': 0.0
                }
            ]
            
            created_macros = []
            for macro_data in macros:
                macro = Macro(**macro_data)
                db_session.add(macro)
                db_session.flush()
                created_macros.append(macro)
            
            # Associate the email filing macro with the accepted suggestion
            created_suggestions[1].macro_id = created_macros[0].id
            
            # Create demo macro executions with screenshot data
            executions = [
                {
                    'macro_id': created_macros[0].id,  # Email Filing Automation
                    'start_time': datetime.now() - timedelta(days=1, hours=3),
                    'end_time': datetime.now() - timedelta(days=1, hours=3, minutes=1),
                    'status': 'success',
                    'original_sequence_duration': 45.0,
                    'execution_duration': 38.2,
                    'time_saved': 6.8,
                    'execution_data': json.dumps({
                        'before_screenshot': 'data/screenshots/email_before.png',
                        'after_screenshot': 'data/screenshots/email_after.png',
                        'diff_screenshot': 'data/screenshots/email_diff.png',
                        'screen_change_percentage': 34.8
                    })
                },
                {
                    'macro_id': created_macros[0].id,  # Email Filing Automation
                    'start_time': datetime.now() - timedelta(days=2, hours=5),
                    'end_time': datetime.now() - timedelta(days=2, hours=5, minutes=1),
                    'status': 'success',
                    'original_sequence_duration': 45.0,
                    'execution_duration': 39.1,
                    'time_saved': 5.9,
                    'execution_data': json.dumps({
                        'before_screenshot': 'data/screenshots/email_before2.png',
                        'after_screenshot': 'data/screenshots/email_after2.png',
                        'diff_screenshot': 'data/screenshots/email_diff2.png',
                        'screen_change_percentage': 42.3
                    })
                },
                {
                    'macro_id': created_macros[0].id,  # Email Filing Automation
                    'start_time': datetime.now() - timedelta(days=3, hours=2),
                    'end_time': datetime.now() - timedelta(days=3, hours=2, minutes=1),
                    'status': 'failed',
                    'original_sequence_duration': 45.0,
                    'execution_duration': 12.3,
                    'error_message': 'Target email folder not found',
                    'execution_data': json.dumps({
                        'before_screenshot': 'data/screenshots/email_before_failed.png',
                        'after_screenshot': 'data/screenshots/email_after_failed.png',
                        'diff_screenshot': 'data/screenshots/email_diff_failed.png',
                        'screen_change_percentage': 2.1,
                        'warning': 'Minimal screen change detected (2.1%). The macro might not have completed its intended actions.'
                    })
                },
                {
                    'macro_id': created_macros[1].id,  # Daily Report Generator
                    'start_time': datetime.now() - timedelta(days=1, hours=1),
                    'end_time': datetime.now() - timedelta(days=1, hours=0, minutes=55),
                    'status': 'success',
                    'original_sequence_duration': 180.0,
                    'execution_duration': 152.3,
                    'time_saved': 27.7,
                    'execution_data': json.dumps({
                        'before_screenshot': 'data/screenshots/report_before.png',
                        'after_screenshot': 'data/screenshots/report_after.png',
                        'diff_screenshot': 'data/screenshots/report_diff.png',
                        'screen_change_percentage': 67.8
                    })
                }
            ]
            
            for execution_data in executions:
                execution = MacroExecution(**execution_data)
                db_session.add(execution)
            
            # Create demo macro steps
            steps = [
                # Steps for Email Filing Automation
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 0,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 450, 'y': 120, 'button': 'left'}),
                    'delay_before': 0.0
                },
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 1,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'ctrl+f'}),
                    'delay_before': 0.5
                },
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 2,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'sender:important'}),
                    'delay_before': 0.3
                },
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 3,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'enter'}),
                    'delay_before': 0.2
                },
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 4,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 680, 'y': 210, 'button': 'right'}),
                    'delay_before': 1.0
                },
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 5,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 720, 'y': 280, 'button': 'left'}),
                    'delay_before': 0.3
                },
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 6,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 400, 'y': 350, 'button': 'left'}),
                    'delay_before': 0.5
                },
                {
                    'macro_id': created_macros[0].id,
                    'step_number': 7,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'enter'}),
                    'delay_before': 0.2
                },
                
                # Steps for Daily Report Generator
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 0,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 30, 'y': 720, 'button': 'left'}),
                    'delay_before': 0.0
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 1,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'report generator'}),
                    'delay_before': 0.5
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 2,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'enter'}),
                    'delay_before': 0.2
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 3,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 450, 'y': 300, 'button': 'left'}),
                    'delay_before': 1.0
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 4,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'ctrl+a'}),
                    'delay_before': 0.3
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 5,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'delete'}),
                    'delay_before': 0.2
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 6,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'Daily Report - '}),
                    'delay_before': 0.5
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 7,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 780, 'y': 300, 'button': 'left'}),
                    'delay_before': 0.3
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 8,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 520, 'y': 400, 'button': 'left'}),
                    'delay_before': 0.5
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 9,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'ctrl+v'}),
                    'delay_before': 0.3
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 10,
                    'action_type': 'mouse_click',
                    'parameters': json.dumps({'x': 850, 'y': 600, 'button': 'left'}),
                    'delay_before': 0.8
                },
                {
                    'macro_id': created_macros[1].id,
                    'step_number': 11,
                    'action_type': 'key_press',
                    'parameters': json.dumps({'key': 'ctrl+s'}),
                    'delay_before': 0.4
                }
            ]
            
            for step_data in steps:
                step = MacroStep(**step_data)
                db_session.add(step)
            
            # Generate sequences for the pattern
            for pattern in created_patterns:
                sequence_ids = []
                for _ in range(3):
                    sequence = EventSequence(
                        start_time=datetime.now() - timedelta(days=random.randint(1, 10), hours=random.randint(1, 23)),
                        end_time=datetime.now() - timedelta(days=random.randint(0, 9), hours=random.randint(1, 23)),
                        event_count=random.randint(10, 50),
                        meta_data=json.dumps({
                            'windows': ['Email Client', 'Spreadsheet', 'Browser', 'Document Editor'],
                            'duration': random.randint(30, 300)
                        }),
                        data=json.dumps([{
                            'type': random.choice(['mouse_click', 'key_press', 'mouse_move']),
                            'timestamp': (datetime.now() - timedelta(days=random.randint(0, 10))).isoformat(),
                            'data': json.dumps({'x': random.randint(100, 900), 'y': random.randint(100, 700)})
                        } for _ in range(10)])
                    )
                    db_session.add(sequence)
                    db_session.flush()
                    sequence_ids.append(sequence.id)
                
                pattern.sequence_ids = json.dumps(sequence_ids)
            
            # Generate event statistics for demo
            event_types = ['mouse_click', 'mouse_move', 'key_press', 'key_release', 'window_change']
            for _ in range(500):
                event_type = random.choice(event_types)
                event_data = {
                    'x': random.randint(0, 1920),
                    'y': random.randint(0, 1080),
                    'window': random.choice(['Email Client', 'Web Browser', 'Document Editor', 'Spreadsheet', 'Terminal'])
                }
                
                if event_type == 'mouse_click':
                    event_data['button'] = random.choice(['left', 'right', 'middle'])
                elif event_type in ['key_press', 'key_release']:
                    event_data['key'] = random.choice(['a', 'b', 'c', 'ctrl', 'shift', 'enter', 'space'])
                
                event = Event(
                    type=event_type,
                    data=json.dumps(event_data),
                    timestamp=datetime.now() - timedelta(days=random.randint(0, 7), 
                                                      hours=random.randint(0, 23), 
                                                      minutes=random.randint(0, 59))
                )
                db_session.add(event)
            
            # Check if we need to create demo AI reports
            if db_session.query(AIAnalysisReport).count() == 0:
                logger.info("Creating demo AI analysis reports...")
                
                # Create demo AI analysis reports
                reports = [
                    {
                        'report_type': 'screenshot',
                        'timestamp': datetime.now() - timedelta(days=1, hours=4),
                        'analysis_data': json.dumps({
                            'detected_elements': ['button', 'form field', 'dropdown menu'],
                            'probable_action': 'form submission',
                            'application': 'Email Client',
                            'screen_area': 'Compose Window',
                            'repetition_indicators': True
                        }),
                        'summary': 'User is composing and sending emails with similar content structure to multiple recipients.',
                        'insights': 'This appears to be a repetitive task of sending similar emails to different people. The structure and content have significant overlap, suggesting potential for automation with customizable fields.',
                        'automation_potential': 0.85,
                        'application_context': 'Email Client - Message Composition'
                    },
                    {
                        'report_type': 'pattern',
                        'timestamp': datetime.now() - timedelta(days=2, hours=8),
                        'analysis_data': json.dumps({
                            'sequence_length': 12,
                            'frequency': 'Daily',
                            'common_applications': ['Spreadsheet', 'Web Browser', 'File Explorer'],
                            'complexity': 'Medium',
                            'keystrokes_saved': 87,
                            'estimated_time_saved': '4.5 minutes per execution'
                        }),
                        'summary': 'Pattern involves extracting data from web pages and organizing it in a spreadsheet following a consistent format.',
                        'insights': 'This data collection workflow follows a consistent pattern where specific elements from web pages are copied to designated spreadsheet columns. The structure is predictable with high consistency in placement.',
                        'automation_potential': 0.78,
                        'application_context': 'Web Research and Data Collection'
                    },
                    {
                        'report_type': 'screenshot',
                        'timestamp': datetime.now() - timedelta(hours=14),
                        'analysis_data': json.dumps({
                            'detected_elements': ['file dialog', 'document', 'toolbar options'],
                            'probable_action': 'document formatting',
                            'application': 'Word Processor',
                            'screen_area': 'Document View',
                            'repetition_indicators': True
                        }),
                        'summary': 'User is applying consistent formatting to multiple document sections.',
                        'insights': 'The document formatting pattern shows repeated application of the same style elements to different sections of text. This suggests a formatting template could be created to streamline the process.',
                        'automation_potential': 0.72,
                        'application_context': 'Word Processor - Document Formatting'
                    }
                ]
                
                for report_data in reports:
                    report = AIAnalysisReport(**report_data)
                    db_session.add(report)
                
                logger.info(f"Added {len(reports)} demo AI analysis reports")
            
            # Create macro execution records
            for macro in created_macros:
                if macro.execution_count > 0:
                    # Create execution records for each macro
                    success_executions = macro.success_count or 0
                    failure_executions = macro.failure_count or 0
                    
                    # Create success records
                    for i in range(min(10, success_executions)):  # Limit to 10 demo records
                        execution_time = datetime.now() - timedelta(days=random.randint(0, 5), 
                                                                   hours=random.randint(1, 23), 
                                                                   minutes=random.randint(0, 59))
                        duration = (macro.original_sequence_duration or 0) * 0.9  # Slightly faster than manual
                        
                        execution = MacroExecution(
                            macro_id=macro.id,
                            start_time=execution_time - timedelta(seconds=duration),
                            end_time=execution_time,
                            status='success',
                            original_sequence_duration=macro.original_sequence_duration,
                            execution_duration=duration,
                            time_saved=(macro.original_sequence_duration or 0) - duration,
                            log_path=f"/logs/execution_{macro.id}_{i}.log"
                        )
                        db_session.add(execution)
                    
                    # Create failure records
                    for i in range(min(5, failure_executions)):  # Limit to 5 demo records
                        execution_time = datetime.now() - timedelta(days=random.randint(0, 5), 
                                                                   hours=random.randint(1, 23), 
                                                                   minutes=random.randint(0, 59))
                        duration = (macro.original_sequence_duration or 0) * 0.5  # Failed halfway through
                        
                        execution = MacroExecution(
                            macro_id=macro.id,
                            start_time=execution_time - timedelta(seconds=duration),
                            end_time=execution_time,
                            status='failed',
                            original_sequence_duration=macro.original_sequence_duration,
                            execution_duration=duration,
                            time_saved=0,  # No time saved on failure
                            error_message="Element not found at expected position",
                            log_path=f"/logs/execution_{macro.id}_failed_{i}.log"
                        )
                        db_session.add(execution)
                        
            db_session.commit()
            logger.info("Demo data seeded successfully")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error seeding demo data: {e}")
        raise

# Call seed_demo_data to populate the database with demo data
logger.info("Calling seed_demo_data()")
seed_demo_data()
logger.info("seed_demo_data() call completed")

# UI Routes for BettermanAI Web Interface

# Add context processor to make os available to all templates
@app.context_processor
def inject_os():
    return dict(os=os)

@app.route('/')
def index():
    """Main application page"""
    monitoring_enabled = settings.get_setting('monitoring_enabled', default=True)
    suggestion_count = db_session.query(Suggestion).filter_by(status='pending').count()
    pattern_count = db_session.query(Pattern).count()
    macro_count = db_session.query(Macro).count()
    
    # Get recent activity for the dashboard
    recent_patterns = db_session.query(Pattern).order_by(Pattern.detection_time.desc()).limit(3).all()
    recent_macros = db_session.query(Macro).order_by(Macro.creation_time.desc()).limit(3).all()
    
    # Create stats for the template
    stats = {
        'monitoring_since': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
        'event_count': db_session.query(Event).count(),
        'pattern_count': pattern_count,
        'suggestion_count': suggestion_count,
        'macro_count': macro_count
    }
    
    return render_template('index.html', 
                          monitoring_enabled=monitoring_enabled,
                          stats=stats,
                          suggestion_count=suggestion_count,
                          pattern_count=pattern_count,
                          macro_count=macro_count,
                          recent_patterns=recent_patterns,
                          recent_macros=recent_macros)

@app.route('/toggle_monitoring', methods=['POST'])
def toggle_monitoring():
    """Toggle monitoring status"""
    current_status = settings.get_setting('monitoring_enabled', default=True)
    new_status = not current_status
    settings.set_setting('monitoring_enabled', new_status)
    
    return jsonify({'success': True, 'monitoring_enabled': new_status})

@app.route('/suggestions')
def suggestions():
    """View automation suggestions"""
    pending_suggestions = db_session.query(Suggestion).filter_by(status='pending').all()
    accepted_suggestions = db_session.query(Suggestion).filter_by(status='accepted').all()
    rejected_suggestions = db_session.query(Suggestion).filter_by(status='rejected').all()
    
    return render_template('suggestions.html', 
                          pending_suggestions=pending_suggestions,
                          accepted_suggestions=accepted_suggestions,
                          rejected_suggestions=rejected_suggestions)

@app.route('/suggestion/<int:suggestion_id>')
def view_suggestion(suggestion_id):
    """View a specific suggestion"""
    suggestion = db_session.query(Suggestion).get(suggestion_id)
    if not suggestion:
        flash('Suggestion not found', 'error')
        return redirect(url_for('suggestions'))
    
    pattern = db_session.query(Pattern).get(suggestion.pattern_id) if suggestion.pattern_id else None
    steps = json.loads(suggestion.steps) if suggestion.steps else []
    
    return render_template('suggestion.html', suggestion=suggestion, pattern=pattern, steps=steps)

@app.route('/suggestion/<int:suggestion_id>/action', methods=['POST'])
def suggestion_action(suggestion_id):
    """Accept or reject a suggestion"""
    action = request.form.get('action')
    suggestion = db_session.query(Suggestion).get(suggestion_id)
    
    if not suggestion:
        return jsonify({'success': False, 'error': 'Suggestion not found'})
    
    if action == 'accept':
        suggestion.status = 'accepted'
        suggestion.action_time = datetime.now()
        
        # Create a macro for this suggestion
        macro = Macro(
            name=f"Auto: {suggestion.title}",
            description=suggestion.description,
            creation_time=datetime.now(),
            status='created'
        )
        db_session.add(macro)
        db_session.flush()
        
        # Link the macro to the suggestion
        suggestion.macro_id = macro.id
        
        flash('Suggestion accepted and automation created', 'success')
    elif action == 'reject':
        suggestion.status = 'rejected'
        suggestion.action_time = datetime.now()
        flash('Suggestion rejected', 'info')
    
    db_session.commit()
    return jsonify({'success': True, 'redirect': url_for('suggestions')})

@app.route('/patterns')
def patterns():
    """View detected patterns"""
    all_patterns = db_session.query(Pattern).order_by(Pattern.detection_time.desc()).all()
    return render_template('patterns.html', patterns=all_patterns)

@app.route('/pattern/<int:pattern_id>')
def view_pattern(pattern_id):
    """View a specific pattern"""
    pattern = db_session.query(Pattern).get(pattern_id)
    if not pattern:
        flash('Pattern not found', 'error')
        return redirect(url_for('patterns'))
    
    # Get sequences for this pattern
    sequences = []
    if pattern.sequence_ids:
        sequence_ids = json.loads(pattern.sequence_ids)
        for seq_id in sequence_ids:
            seq = db_session.query(EventSequence).get(seq_id)
            if seq:
                seq_data = {
                    'id': seq.id,
                    'start_time': seq.start_time,
                    'event_count': seq.event_count,
                    'duration': 0,
                    'windows': []
                }
                
                if seq.meta_data:
                    meta_data = json.loads(seq.meta_data)
                    seq_data['duration'] = meta_data.get('duration', 0)
                    seq_data['windows'] = meta_data.get('windows', [])
                
                sequences.append(seq_data)
    
    return render_template('pattern.html', pattern=pattern, sequences=sequences)

@app.route('/macros')
def macros():
    """View recorded macros"""
    all_macros = db_session.query(Macro).all()
    return render_template('macros.html', macros=all_macros)

@app.route('/macro-library')
def macro_library():
    """Modern macro library UI"""
    return render_template('macro_library.html')

@app.route('/macro/<int:macro_id>')
def view_macro(macro_id):
    """View a specific macro"""
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        flash('Macro not found', 'error')
        return redirect(url_for('macros'))
    
    steps = db_session.query(MacroStep).filter_by(macro_id=macro.id).order_by(MacroStep.step_number).all()
    
    return render_template('macro.html', macro=macro, steps=steps)
    
@app.route('/execution/<int:execution_id>')
def view_execution(execution_id):
    """View details of a specific macro execution"""
    execution = db_session.query(MacroExecution).get(execution_id)
    if not execution:
        flash('Execution record not found', 'error')
        return redirect(url_for('macros'))
    
    macro = db_session.query(Macro).get(execution.macro_id)
    if not macro:
        flash('Associated macro not found', 'error')
        return redirect(url_for('macros'))
    
    # Determine status color for badge display
    status_color = 'secondary'
    if execution.status == 'success':
        status_color = 'success'
    elif execution.status == 'failed':
        status_color = 'danger'
    elif execution.status == 'timeout':
        status_color = 'warning'
    elif execution.status == 'running':
        status_color = 'primary'
    
    # Parse execution data if available
    execution_data = None
    if execution.execution_data:
        try:
            execution_data = json.loads(execution.execution_data)
            
            # Create symlinks to screenshots in static folder if needed
            if 'before_screenshot' in execution_data and execution_data['before_screenshot']:
                try:
                    src = execution_data['before_screenshot']
                    dst = os.path.join('static/screenshots', os.path.basename(src))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    # Create symlink if it doesn't exist
                    if not os.path.exists(dst):
                        os.symlink(src, dst)
                except Exception as e:
                    logger.error(f"Error creating symlink for before screenshot: {e}")
            
            if 'after_screenshot' in execution_data and execution_data['after_screenshot']:
                try:
                    src = execution_data['after_screenshot']
                    dst = os.path.join('static/screenshots', os.path.basename(src))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    if not os.path.exists(dst):
                        os.symlink(src, dst)
                except Exception as e:
                    logger.error(f"Error creating symlink for after screenshot: {e}")
            
            if 'diff_screenshot' in execution_data and execution_data['diff_screenshot']:
                try:
                    src = execution_data['diff_screenshot']
                    dst = os.path.join('static/screenshots', os.path.basename(src))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    if not os.path.exists(dst):
                        os.symlink(src, dst)
                except Exception as e:
                    logger.error(f"Error creating symlink for diff screenshot: {e}")
                    
        except Exception as e:
            logger.error(f"Error parsing execution data: {e}")
    
    return render_template('execution_detail.html', 
                          execution=execution, 
                          macro=macro, 
                          status_color=status_color,
                          execution_data=execution_data)

@app.route('/macro/new')
def new_macro():
    """Create a new macro"""
    macro = Macro(
        name="New Macro",
        description="",
        creation_time=datetime.now(),
        status='created'
    )
    db_session.add(macro)
    db_session.commit()
    
    return redirect(url_for('edit_macro', macro_id=macro.id))

@app.route('/macro/<int:macro_id>/edit')
def edit_macro(macro_id):
    """Edit a macro"""
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        flash('Macro not found', 'error')
        return redirect(url_for('macros'))
    
    return render_template('edit_macro.html', macro=macro)

@app.route('/macro/<int:macro_id>/record', methods=['POST'])
def record_macro(macro_id):
    """Start recording a macro"""
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        return jsonify({'success': False, 'error': 'Macro not found'})
    
    macro.status = 'recording'
    db_session.commit()
    
    return jsonify({'success': True})

@app.route('/macro/<int:macro_id>/stop', methods=['POST'])
def stop_recording(macro_id):
    """Stop recording a macro"""
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        return jsonify({'success': False, 'error': 'Macro not found'})
    
    macro.status = 'recorded'
    macro.step_count = db_session.query(MacroStep).filter_by(macro_id=macro.id).count()
    db_session.commit()
    
    # In a real implementation, we would stop the recording thread
    # Here we simulate by adding random steps
    if macro.step_count == 0:
        action_types = ['mouse_click', 'key_press', 'mouse_move']
        for i in range(random.randint(5, 10)):
            action_type = random.choice(action_types)
            parameters = {}
            
            if action_type in ['mouse_click', 'mouse_move']:
                parameters = {
                    'x': random.randint(100, 900),
                    'y': random.randint(100, 700)
                }
                if action_type == 'mouse_click':
                    parameters['button'] = random.choice(['left', 'right'])
            elif action_type == 'key_press':
                parameters = {'key': random.choice(['a', 'b', 'enter', 'shift', 'ctrl+c', 'ctrl+v'])}
            
            step = MacroStep(
                macro_id=macro.id,
                step_number=i,
                action_type=action_type,
                parameters=json.dumps(parameters),
                delay_before=random.uniform(0.1, 1.0)
            )
            db_session.add(step)
        
        macro.step_count = random.randint(5, 10)
        db_session.commit()
    
    return jsonify({'success': True, 'redirect': url_for('view_macro', macro_id=macro.id)})

@app.route('/macro/<int:macro_id>/execute', methods=['POST'])
def web_execute_macro(macro_id):
    """Web route to execute a macro, redirects back to the macro view page"""
    # Call the API execute_macro function with default mode
    result = execute_macro(macro_id, 'normal')
    
    # For web routes, return a redirect to the macro view page
    if result.get('status') == 'error':
        flash(f"Error executing macro: {result.get('message')}", 'danger')
    else:
        flash(f"Macro execution started successfully", 'success')
        
    return redirect(url_for('view_macro', macro_id=macro_id))

@app.route('/statistics')
def statistics():
    """View system statistics"""
    # Get basic counts
    event_count = db_session.query(Event).count()
    pattern_count = db_session.query(Pattern).count()
    suggestion_count = db_session.query(Suggestion).count()
    macro_count = db_session.query(Macro).count()
    
    # Get event type distribution
    event_types = {}
    event_type_results = db_session.query(Event.type, db_session.func.count(Event.id)).group_by(Event.type).all()
    for event_type, count in event_type_results:
        event_types[event_type] = count
    
    # Get pattern status distribution
    pattern_status = {}
    pattern_status_results = db_session.query(Pattern.status, db_session.func.count(Pattern.id)).group_by(Pattern.status).all()
    for status, count in pattern_status_results:
        pattern_status[status] = count
    
    # Simulate hourly events data
    hourly_events = []
    for hour in range(24):
        timestamp = datetime.now() - timedelta(hours=23-hour)
        count = random.randint(10, 100)
        hourly_events.append({
            'hour': timestamp.strftime('%H:%M'),
            'count': count
        })
    
    stats = {
        'event_count': event_count,
        'pattern_count': pattern_count,
        'suggestion_count': suggestion_count,
        'macro_count': macro_count,
        'event_types': event_types,
        'pattern_status': pattern_status,
        'hourly_events': hourly_events
    }
    
    return render_template('statistics.html', statistics=stats)

@app.route('/logs')
def logs():
    """View system logs"""
    # In a real implementation, this would read actual log files
    # Here we generate simulated log entries
    try:
        logs = []
        for _ in range(100):
            event_type = random.choice(['mouse_click', 'mouse_move', 'key_press', 'key_release', 'window_change'])
            window = random.choice(['Email Client', 'Web Browser', 'Document Editor', 'Spreadsheet', 'Terminal'])
            timestamp = (datetime.now() - timedelta(minutes=random.randint(1, 120))).strftime('%Y-%m-%d %H:%M:%S')
            
            log_entry = {
                'timestamp': timestamp,
                'type': event_type,
                'window': window
            }
            
            if event_type == 'mouse_click':
                log_entry['x'] = random.randint(0, 1920)
                log_entry['y'] = random.randint(0, 1080)
                log_entry['button'] = random.choice(['left', 'right', 'middle'])
            elif event_type == 'mouse_move':
                log_entry['x'] = random.randint(0, 1920)
                log_entry['y'] = random.randint(0, 1080)
            elif event_type == 'mouse_scroll':
                log_entry['x'] = random.randint(0, 1920)
                log_entry['y'] = random.randint(0, 1080)
                log_entry['dx'] = random.randint(-10, 10)
                log_entry['dy'] = random.randint(-10, 10)
            elif event_type in ['key_press', 'key_release']:
                log_entry['key'] = random.choice(['a', 'b', 'c', 'ctrl', 'shift', 'enter', 'space'])
            
            logs.append(log_entry)
        
        # Sort logs by timestamp, most recent first
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return render_template('logs.html', logs=logs, error=None)
    except Exception as e:
        return render_template('logs.html', logs=[], error=str(e))

@app.route('/settings')
def settings_page():
    """Settings page"""
    all_settings = db_session.query(Setting).all()
    
    # Convert settings to a dictionary for the template
    settings_dict = {}
    for setting in all_settings:
        if setting.value_type == 'boolean':
            settings_dict[setting.name] = setting.value.lower() == 'true'
        elif setting.value_type == 'number':
            settings_dict[setting.name] = float(setting.value)
            if settings_dict[setting.name].is_integer():
                settings_dict[setting.name] = int(settings_dict[setting.name])
        else:
            settings_dict[setting.name] = setting.value
    
    # Add special settings
    settings_dict['automation_server_url'] = os.environ.get('AUTOMATION_SERVER_URL', '')
    
    # Check connection status
    import requests
    from requests.exceptions import RequestException
    
    connection_status = {
        'connected': False,
        'screen_size': {'width': 0, 'height': 0},
        'monitoring': False
    }
    
    server_url = settings_dict.get('automation_server_url')
    if server_url:
        try:
            response = requests.get(f"{server_url}/api/status", timeout=3)
            if response.status_code == 200:
                status_data = response.json()
                connection_status = {
                    'connected': True,
                    'screen_size': status_data.get('screen_size', {'width': 1920, 'height': 1080}),
                    'monitoring': status_data.get('monitoring', False)
                }
        except Exception:
            # Connection failed
            pass
    
    return render_template('settings.html', 
                          settings=settings_dict,
                          connection_status=connection_status)

@app.route('/settings/update', methods=['POST'])
def update_settings():
    """Update settings via AJAX"""
    setting_name = request.form.get('name')
    setting_value = request.form.get('value')
    
    if not setting_name:
        return jsonify({'success': False, 'error': 'Setting name is required'})
    
    success = settings.set_setting(setting_name, setting_value)
    
    return jsonify({'success': success})

@app.route('/test_connection')
def test_connection():
    """Test connection to automation server"""
    server_url = settings.get_setting('automation_server_url', '')
    
    if not server_url:
        return jsonify({
            'connected': False, 
            'error': 'Server URL not configured'
        })
    
    # Initialize the client with the server URL
    client = AutomationClient(server_url)
    
    try:
        # Test the connection by getting the screen size
        is_connected = client.is_connected()
        
        if is_connected:
            # Get screen size for additional verification
            response = requests.get(f"{server_url}/screen_size")
            if response.status_code == 200:
                screen_size = response.json()
                return jsonify({
                    'connected': True,
                    'screen_size': screen_size
                })
            else:
                return jsonify({
                    'connected': False,
                    'error': 'Connected, but failed to get screen size'
                })
        else:
            return jsonify({
                'connected': False,
                'error': 'Failed to connect to automation server'
            })
    except Exception as e:
        return jsonify({
            'connected': False,
            'error': str(e)
        })

@app.route('/scheduled_jobs')
def scheduled_jobs():
    """View and manage scheduled jobs"""
    from models import ScheduledJob
    
    # Get all jobs
    jobs = db_session.query(ScheduledJob).order_by(ScheduledJob.job_type).all()
    
    # Get settings for the template
    all_settings = {}
    for setting in db_session.query(Setting).all():
        if setting.name.startswith('jobs_') or setting.name.startswith('rolling_') or setting.name.startswith('nightly_'):
            if setting.value_type == 'boolean':
                all_settings[setting.name] = setting.value.lower() == 'true'
            elif setting.value_type == 'number':
                all_settings[setting.name] = float(setting.value)
                if all_settings[setting.name].is_integer():
                    all_settings[setting.name] = int(all_settings[setting.name])
            else:
                all_settings[setting.name] = setting.value
    
    return render_template('scheduled_jobs.html', jobs=jobs, settings=all_settings)

@app.route('/api/jobs/<int:job_id>/result')
def get_job_result(job_id):
    """Get the result of a scheduled job"""
    from models import ScheduledJob
    
    job = db_session.query(ScheduledJob).get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'})
    
    try:
        result = json.loads(job.result) if job.result else {}
    except Exception:
        result = {'error': 'Invalid result data'}
    
    return jsonify({'success': True, 'result': result})

@app.route('/api/jobs/<int:job_id>/toggle', methods=['POST'])
def toggle_job_status(job_id):
    """Toggle a job's enabled status"""
    from models import ScheduledJob
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request'})
    
    job = db_session.query(ScheduledJob).get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'})
    
    try:
        job.enabled = 1 if data.get('enabled', False) else 0
        db_session.commit()
        return jsonify({'success': True, 'enabled': job.enabled == 1})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/jobs/<int:job_id>/run-now', methods=['POST'])
def run_job_now(job_id):
    """Run a job immediately"""
    from models import ScheduledJob
    
    job = db_session.query(ScheduledJob).get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'})
    
    try:
        # Update job to run immediately
        job.next_run_time = datetime.now()
        job.status = 'scheduled'
        db_session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_settings', methods=['POST'])
def update_settings_api():
    """Update multiple settings at once via AJAX"""
    data = request.json
    section = data.get('section', 'general')
    settings_data = data.get('settings', {})
    
    results = {}
    for name, value in settings_data.items():
        # Special case for automation_server_url - store in environment variable
        if name == 'automation_server_url' and value:
            os.environ['AUTOMATION_SERVER_URL'] = value
            results[name] = True
        else:
            results[name] = settings.set_setting(name, value)
    
    return jsonify({
        'success': all(results.values()),
        'results': results
    })

@app.route('/ai_reports')
def ai_reports():
    """View AI analysis reports"""
    # Get all AI analysis reports, ordered by timestamp (newest first)
    reports = db_session.query(AIAnalysisReport).order_by(AIAnalysisReport.timestamp.desc()).all()
    return render_template('ai_reports.html', reports=reports)

@app.route('/ai_report/<int:report_id>')
def view_ai_report(report_id):
    """View a specific AI analysis report"""
    # Get the report
    report = db_session.query(AIAnalysisReport).filter(AIAnalysisReport.id == report_id).first()
    
    # Return 404 if report not found
    if not report:
        abort(404)
    
    # Parse the analysis data JSON
    analysis = {}
    if report.analysis_data:
        try:
            analysis = json.loads(report.analysis_data)
        except:
            analysis = {"error": "Could not parse analysis data"}
    
    # Get associated event if this is a screenshot report
    event = None
    if report.report_type == 'screenshot' and report.source_id:
        event = db_session.query(Event).filter(Event.id == report.source_id).first()
    
    return render_template('view_ai_report.html', report=report, analysis=analysis, event=event)

@app.route('/about')
def about():
    """About BettermanAI"""
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    """Privacy information"""
    return render_template('privacy.html')


@app.route('/server-url-manager')
def server_url_manager():
    """Server URL Manager page"""
    server_url = os.environ.get('AUTOMATION_SERVER_URL', '')
    return render_template('server_url_manager.html', server_url=server_url)


@app.route('/api/update-server-url', methods=['POST'])
def update_server_url():
    """API endpoint to test and update the automation server URL"""
    try:
        data = request.json
        server_url = data.get('server_url', '')
        permanent = data.get('permanent', False)
        
        if not server_url:
            return jsonify({
                'status': 'error',
                'message': 'No server URL provided'
            })
        
        # Run various connection tests
        import requests
        from requests.exceptions import RequestException
        
        tests = []
        
        # Test basic connectivity
        try:
            status_response = requests.get(f"{server_url}/api/status", timeout=3)
            if status_response.status_code == 200:
                tests.append({
                    'name': 'Basic API Connectivity',
                    'status': 'success',
                    'message': 'Successfully connected to the server API'
                })
            else:
                tests.append({
                    'name': 'Basic API Connectivity',
                    'status': 'failed',
                    'message': f'Server returned status code {status_response.status_code}'
                })
        except Exception as e:
            tests.append({
                'name': 'Basic API Connectivity',
                'status': 'failed',
                'message': f'Failed to connect: {str(e)}'
            })
        
        # Test window list API
        try:
            from automation_client import AutomationClient
            client = AutomationClient(server_url)
            window_list = client.get_window_list()
            if isinstance(window_list, list):
                tests.append({
                    'name': 'Window List API',
                    'status': 'success',
                    'message': f'Retrieved window list with {len(window_list)} windows'
                })
            else:
                tests.append({
                    'name': 'Window List API',
                    'status': 'failed',
                    'message': 'Failed to get window list'
                })
        except Exception as e:
            tests.append({
                'name': 'Window List API',
                'status': 'failed',
                'message': f'Error getting window list: {str(e)}'
            })
        
        # Check overall connection status
        connection_success = any(test['status'] == 'success' for test in tests)
        
        if connection_success:
            # Update the environment variable permanently if requested
            if permanent:
                os.environ['AUTOMATION_SERVER_URL'] = server_url
                settings.set_setting('automation_server_url', server_url)
                tests.append({
                    'name': 'Environment Update',
                    'status': 'success',
                    'message': 'Updated environment variable permanently'
                })
            
            return jsonify({
                'status': 'success',
                'message': 'Successfully connected to the automation server',
                'tests': tests
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to connect to the automation server',
                'tests': tests
            })
    except Exception as e:
        logger.error(f"Error updating server URL: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

@app.route('/audio')
def audio_settings():
    """Audio settings page"""
    all_settings = {}
    for setting in db_session.query(Setting).all():
        if setting.name.startswith('audio_'):
            if setting.value_type == 'boolean':
                all_settings[setting.name] = setting.value.lower() == 'true'
            elif setting.value_type == 'number':
                all_settings[setting.name] = float(setting.value)
                if all_settings[setting.name].is_integer():
                    all_settings[setting.name] = int(all_settings[setting.name])
            else:
                all_settings[setting.name] = setting.value
    
    # Check if we have an OpenAI API key
    api_key_exists = bool(os.environ.get("OPENAI_API_KEY"))
    all_settings['openai_api_key_exists'] = api_key_exists
    
    return render_template('audio_settings.html', settings=all_settings)

@app.route('/webcam')
def webcam_settings():
    """Webcam settings page"""
    all_settings = {}
    for setting in db_session.query(Setting).all():
        if setting.name.startswith('webcam_'):
            if setting.value_type == 'boolean':
                all_settings[setting.name] = setting.value.lower() == 'true'
            elif setting.value_type == 'number':
                all_settings[setting.name] = float(setting.value)
                if all_settings[setting.name].is_integer():
                    all_settings[setting.name] = int(all_settings[setting.name])
            else:
                all_settings[setting.name] = setting.value
    
    return render_template('webcam_settings.html', settings=all_settings)

@app.route('/api/audio/start_capture', methods=['POST'])
def start_audio_capture():
    """Start audio capture"""
    from audio_capture import AudioCapture
    
    # Check if audio is enabled
    if not settings.get_setting('audio_enabled', default=False):
        return jsonify({'success': False, 'error': 'Audio capture is disabled in settings'})
    
    try:
        # Initialize audio capture
        audio_buffer_size = settings.get_setting('audio_buffer_size', default=15)
        local_model = settings.get_setting('audio_local_model_path', default='')
        
        audio_capture = AudioCapture(settings, buffer_size=audio_buffer_size, 
                               local_stt_model=local_model if local_model else None)
        
        # Store in app context for reuse
        app.config['AUDIO_CAPTURE'] = audio_capture
        
        # Start capturing
        audio_capture.start_capture()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error starting audio capture: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/audio/stop_capture', methods=['POST'])
def stop_audio_capture():
    """Stop audio capture"""
    audio_capture = app.config.get('AUDIO_CAPTURE')
    
    if not audio_capture:
        return jsonify({'success': False, 'error': 'No active audio capture'})
    
    try:
        # Stop capturing
        audio_capture.stop_capture()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error stopping audio capture: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/audio/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe captured audio"""
    audio_capture = app.config.get('AUDIO_CAPTURE')
    
    if not audio_capture:
        return jsonify({'success': False, 'error': 'No active audio capture'})
    
    try:
        # Transcribe the audio in the buffer
        result = audio_capture.transcribe_buffer()
        
        # Add success flag if not present
        if 'success' not in result:
            result['success'] = bool(result.get('text'))
            
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings/openai_api_key', methods=['POST'])
def save_openai_api_key():
    """Save the OpenAI API key as an environment variable"""
    data = request.json
    api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API key is required'})
    
    try:
        # Store in environment variable
        os.environ['OPENAI_API_KEY'] = api_key
        
        # We don't store the key in the database for security reasons
        # Instead, we just store a flag that it's been set
        settings.set_setting('audio_use_openai_whisper', True)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving OpenAI API key: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/webcam/start_capture', methods=['POST'])
def start_webcam_capture():
    """Start webcam capture"""
    from webcam_capture import WebcamCapture
    
    # Check if webcam is enabled
    if not settings.get_setting('webcam_enabled', default=False):
        return jsonify({'success': False, 'error': 'Webcam capture is disabled in settings'})
    
    try:
        # Initialize webcam capture
        webcam_capture = WebcamCapture(settings)
        
        # Store in app context for reuse
        app.config['WEBCAM_CAPTURE'] = webcam_capture
        
        # Start capturing
        webcam_capture.start_capture()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error starting webcam capture: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/webcam/stop_capture', methods=['POST'])
def stop_webcam_capture():
    """Stop webcam capture"""
    webcam_capture = app.config.get('WEBCAM_CAPTURE')
    
    if not webcam_capture:
        return jsonify({'success': False, 'error': 'No active webcam capture'})
    
    try:
        # Stop capturing
        webcam_capture.stop_capture()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error stopping webcam capture: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/webcam/frame')
def get_webcam_frame():
    """Get current webcam frame as JPEG image"""
    webcam_capture = app.config.get('WEBCAM_CAPTURE')
    
    if not webcam_capture:
        # Return placeholder image
        return send_file('static/img/webcam-placeholder.png', mimetype='image/png')
    
    try:
        # Get frame as base64
        frame_base64 = webcam_capture.get_frame_as_base64()
        
        if not frame_base64:
            # Return placeholder if no frame is available
            return send_file('static/img/webcam-placeholder.png', mimetype='image/png')
        
        # Convert base64 to binary and return as JPEG
        frame_binary = base64.b64decode(frame_base64)
        return Response(frame_binary, mimetype='image/jpeg')
    except Exception as e:
        logger.error(f"Error getting webcam frame: {e}")
        # Return placeholder on error
        return send_file('static/img/webcam-placeholder.png', mimetype='image/png')

@app.route('/api/webcam/snapshot', methods=['POST'])
def take_webcam_snapshot():
    """Take a snapshot from the webcam"""
    webcam_capture = app.config.get('WEBCAM_CAPTURE')
    
    if not webcam_capture:
        return jsonify({'success': False, 'error': 'No active webcam capture'})
    
    try:
        # Get frame as base64
        frame_base64 = webcam_capture.get_frame_as_base64()
        
        if not frame_base64:
            return jsonify({'success': False, 'error': 'No frame available'})
        
        # If save_frames is enabled, save the frame to disk
        if settings.get_setting('webcam_save_frames', default=False):
            # Create snapshots directory if it doesn't exist
            os.makedirs('snapshots', exist_ok=True)
            
            # Save frame with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join('snapshots', f'snapshot_{timestamp}.jpg')
            
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(frame_base64))
                
            logger.info(f"Saved snapshot to {filepath}")
        
        return jsonify({
            'success': True, 
            'image': frame_base64,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error taking snapshot: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/webcam/detect_faces')
def detect_webcam_faces():
    """Detect faces in the current webcam frame"""
    webcam_capture = app.config.get('WEBCAM_CAPTURE')
    
    if not webcam_capture:
        return jsonify({'success': False, 'error': 'No active webcam capture'})
    
    # Check if face detection is enabled
    if not settings.get_setting('webcam_face_detection', default=True):
        return jsonify({'success': False, 'error': 'Face detection is disabled in settings'})
    
    try:
        # Detect faces
        faces = webcam_capture.detect_faces()
        
        return jsonify({
            'success': True,
            'faces': faces,
            'count': len(faces)
        })
    except Exception as e:
        logger.error(f"Error detecting faces: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
def api_stats():
    """API endpoint to get basic stats for dashboard updates"""
    event_count = db_session.query(Event).count()
    pattern_count = db_session.query(Pattern).count()
    suggestion_count = db_session.query(Suggestion).filter_by(status='pending').count()
    macro_count = db_session.query(Macro).count()
    
    return jsonify({
        'event_count': event_count,
        'pattern_count': pattern_count,
        'suggestion_count': suggestion_count,
        'macro_count': macro_count,
        'monitoring_enabled': settings.get_setting('monitoring_enabled', default=True)
    })

@app.route('/api/test_connection', methods=['POST'])
def api_test_connection():
    """Test connection to the local automation server"""
    import requests
    from requests.exceptions import RequestException

    data = request.json
    server_url = data.get('server_url', os.environ.get('AUTOMATION_SERVER_URL', ''))
    update_env = data.get('update_env', False)
    
    if not server_url:
        return jsonify({'success': False, 'error': 'No server URL provided'})
    
    try:
        # Try to get the status of the server
        response = requests.get(f"{server_url}/api/status", timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            
            # Update the settings with the new URL if successful
            settings.set_setting('automation_server_url', server_url)
            
            # If requested, also update the environment variable
            if update_env:
                # Update the environment variable for the current process
                os.environ['AUTOMATION_SERVER_URL'] = server_url
                logger.info(f"Updated AUTOMATION_SERVER_URL to: {server_url}")
                
                # Add a success message about updating the environment variable
                return jsonify({
                    'success': True,
                    'screen_size': status_data.get('screen_size', {'width': 1920, 'height': 1080}),
                    'monitoring': status_data.get('monitoring', False),
                    'message': f"Connected successfully and updated environment variable to {server_url}"
                })
            
            return jsonify({
                'success': True,
                'screen_size': status_data.get('screen_size', {'width': 1920, 'height': 1080}),
                'monitoring': status_data.get('monitoring', False)
            })
        else:
            return jsonify({'success': False, 'error': f"Server returned status code {response.status_code}"})
    except RequestException as e:
        return jsonify({'success': False, 'error': f"Connection error: {str(e)}"})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
        
@app.route('/monitor')
def monitor_dashboard():
    """Real-time monitoring dashboard"""
    from monitor_controller import MonitorController
    
    # Create controller
    controller = MonitorController()
    
    # Get server URL
    server_url = os.environ.get('AUTOMATION_SERVER_URL', '')
    
    # Check connection status
    connection_status = {
        'connected': False,
        'screen_size': {'width': 0, 'height': 0},
        'monitoring': False
    }
    
    if controller.is_connected():
        status = controller.get_status()
        connection_status = {
            'connected': True,
            'screen_size': status.get('screen_size', {'width': 1920, 'height': 1080}),
            'monitoring': status.get('monitoring', False)
        }
    
    return render_template('monitor_dashboard.html',
                          server_url=server_url,
                          connection_status=connection_status,
                          monitoring_active=connection_status.get('monitoring', False))
                          
@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """Start monitoring on the local server"""
    from monitor_controller import MonitorController
    
    controller = MonitorController()
    result = controller.start_monitoring()
    
    return jsonify(result)
    
@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """Stop monitoring on the local server"""
    from monitor_controller import MonitorController
    
    controller = MonitorController()
    result = controller.stop_monitoring()
    
    return jsonify(result)
    
@app.route('/api/events')
def get_events():
    """Get events from the local server"""
    from monitor_controller import MonitorController
    import logging
    
    controller = MonitorController()
    count = request.args.get('count', default=100, type=int)
    offset = request.args.get('offset', default=0, type=int)
    event_type = request.args.get('type')
    
    try:
        events = controller.get_events(count=count, event_type=event_type)
        logging.info(f"Retrieved {len(events)} events from automation server")
        
        # Apply offset if provided
        if offset > 0 and offset < len(events):
            events = events[offset:]
            
        return jsonify({'events': events})
    except Exception as e:
        logging.error(f"Error getting events: {e}")
        return jsonify({'events': [], 'error': str(e)})

# Handle graceful shutdown
def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received, cleaning up...")
    
    # Stop async database writer
    try:
        async_db_writer.stop()
        logger.info("Async database writer stopped")
    except Exception as e:
        logger.error(f"Error stopping async database writer: {e}")
    
    # Clean up database session
    db_session.remove()
    
    # Exit gracefully
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialize settings with defaults if needed
def init_default_settings():
    """Initialize default settings"""
    default_settings = {
        'monitoring_enabled': True,
        'general_startup_monitoring': True,
        'general_notification_timeout': 5,
        'privacy_track_mouse': True,
        'privacy_track_keyboard': True,
        'privacy_track_windows': True,
        'privacy_data_retention_days': 30,
        'automation_min_pattern_score': 0.7,
        'automation_suggestion_threshold': 3,
        'automation_use_ai': True,
        'automation_execution_confirmation': True,
        
        # Variable handling settings
        'prompt_required_variables': True,
        'variable_prompt_timeout': 30,
        'allow_variable_formatting': True,
        'allow_conditional_variables': True,
        'save_variable_values': True,
        
        # Sequence and adaptive timeout settings
        'sequence_adaptive_timeout_enabled': True,
        'sequence_min_timeout': 5,
        'sequence_max_timeout': 60,
        'sequence_default_timeout': 15,
        'sequence_max_events': 200,
        
        # Scheduled jobs settings
        'jobs_enabled': True,
        'rolling_pattern_detection_interval': 240,  # minutes (4 hours)
        'rolling_pattern_detection_time_window': 2,  # days
        'nightly_pattern_analysis_time': '03:00',  # 3 AM
        'nightly_pattern_analysis_time_window': 7,  # days
        'nightly_pattern_analysis_min_score': 0.7,
        
        # Audio capture settings
        'audio_enabled': False,
        'audio_buffer_size': 15,  # seconds
        'audio_capture_mode': 'manual',  # manual, continuous, trigger
        'audio_stt_engine': 'openai',  # openai, local
        'audio_local_model_path': '',
        'audio_privacy_mode': True,
        'audio_use_openai_whisper': True,
        
        # Webcam capture settings
        'webcam_enabled': False,
        'webcam_capture_mode': 'manual',  # manual, continuous, trigger
        'webcam_privacy_mode': 'blur',  # blur, pixelate, silhouette, none
        'webcam_blur_strength': 15,
        'webcam_pixelate_factor': 15,
        'webcam_face_detection': True,
        'webcam_save_frames': False
    }
    
    for name, value in default_settings.items():
        if settings.get_setting(name) is None:
            value_type = 'boolean' if isinstance(value, bool) else 'number' if isinstance(value, (int, float)) else 'string'
            setting = Setting(
                name=name,
                value=str(value).lower() if isinstance(value, bool) else str(value),
                value_type=value_type,
                description=f"Default setting for {name.replace('_', ' ')}"
            )
            db_session.add(setting)
    
    db_session.commit()

# Automation manager route
@app.route('/automation')
def automation_manager():
    """UI for managing automation macros"""
    return render_template('automation_manager.html')

# YAML DSL Compiler route
@app.route('/yaml-compiler')
def yaml_compiler():
    """UI for testing the YAML to TagUI compiler"""
    return render_template('yaml_compiler.html')

# Dry Run Overlay test route
@app.route('/dry-run-overlay')
def dry_run_overlay():
    """Test page for the Dry Run Overlay feature"""
    return render_template('dry_run_overlay.html')

# Test Macro Execution route
@app.route('/test-macro-execution')
def test_macro_execution():
    """Test page for macro execution"""
    # Load the sample macro from the test file and create a database record
    try:
        import yaml
        
        # Ensure the data directories exist
        os.makedirs("data/macros", exist_ok=True)
        os.makedirs("logs/macros", exist_ok=True)
        
        # Check if we already have a test macro in the database
        existing_macro = db_session.query(Macro).filter_by(name="Test Macro").first()
        
        if existing_macro:
            # Use the existing macro
            macro_id = existing_macro.id
            macro = existing_macro
        else:
            # Create a new macro in the database
            # First, check if the test macro YAML exists
            test_macro_path = "data/macros/test_macro.yaml"
            if os.path.exists(test_macro_path):
                # Load the YAML file
                with open(test_macro_path, 'r') as f:
                    yaml_content = f.read()
                
                # Parse the YAML content
                macro_data = yaml.safe_load(yaml_content)
                
                # Extract steps
                steps = []
                for step in macro_data.get('steps', []):
                    steps.append({
                        'type': step.get('type'),
                        'params': step.get('params', {})
                    })
                
                # Create the macro in the database
                macro = Macro(
                    name=macro_data['metadata']['name'],
                    description=macro_data['metadata']['description'],
                    status='recorded',
                    step_count=len(steps),
                    execution_count=0
                )
                
                # Add the macro to the database
                db_session.add(macro)
                db_session.commit()
                
                # Now create the step objects
                for index, step in enumerate(steps):
                    macro_step = MacroStep(
                        macro_id=macro.id,
                        step_number=index + 1,
                        action_type=step['type'],
                        parameters=json.dumps(step['params']),
                        delay_before=0.0
                    )
                    db_session.add(macro_step)
                
                db_session.add(macro)
                db_session.commit()
                macro_id = macro.id
            else:
                # Create a default test macro if no YAML exists
                sample_steps = [
                    {
                        "type": "mouse_move",
                        "params": {"x": 100, "y": 100}
                    },
                    {
                        "type": "mouse_click",
                        "params": {"button": "left", "clicks": 1}
                    },
                    {
                        "type": "keyboard_type",
                        "params": {"text": "Hello, world!"}
                    },
                    {
                        "type": "keyboard_press",
                        "params": {"key": "enter"}
                    },
                    {
                        "type": "wait",
                        "params": {"seconds": 2}
                    }
                ]
                
                macro = Macro(
                    name="Test Macro",
                    description="A simple test macro for validating the execution process",
                    status='recorded',
                    step_count=len(sample_steps),
                    execution_count=0
                )
                
                db_session.add(macro)
                db_session.commit()
                
                # Now create step objects for this macro
                for index, step in enumerate(sample_steps):
                    macro_step = MacroStep(
                        macro_id=macro.id,
                        step_number=index + 1,
                        action_type=step['type'],
                        parameters=json.dumps(step['params']),
                        delay_before=0.0
                    )
                    db_session.add(macro_step)
                
                db_session.commit()
                macro_id = macro.id
        
        # Convert macro steps relationship to a list of dictionaries for the template
        steps_list = []
        for step in macro.steps:
            step_dict = {
                'type': step.action_type,
                'params': json.loads(step.parameters) if isinstance(step.parameters, str) else step.parameters
            }
            steps_list.append(step_dict)
        
        # Convert to dict for template
        macro_dict = {
            'macro_id': macro.id,  # Use the database ID
            'name': macro.name,
            'description': macro.description,
            'steps': steps_list
        }
        
        # Return the test macro execution page with the macro data
        return render_template("test_macro_execution.html", macro=macro_dict)
    except Exception as e:
        logger.error(f"Error loading test macro: {e}")
        # Make sure to rollback the transaction in case of failure
        try:
            db_session.rollback()
        except:
            pass
        
        flash(f"Error loading test macro: {e}", "danger")
        # Redirect to the automation manager since there's no 'automation' route
        return redirect(url_for("automation_manager"))

# TagUI Automation API Routes
from automation_macros import (
    list_macros, get_macro, save_macro, delete_macro,
    execute_macro, get_macro_status, stop_macro, get_log_content, create_sample_macro
)

@app.route('/api/automation/macros', methods=['GET'])
def api_list_macros():
    """API endpoint to list all macros"""
    try:
        macros = list_macros()
        return jsonify({
            'status': 'success',
            'macros': macros
        })
    except Exception as e:
        logger.error(f"Error listing macros: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/macros/<macro_id>', methods=['GET'])
def api_get_macro(macro_id):
    """API endpoint to get a macro by ID"""
    try:
        macro = get_macro(macro_id)
        if macro:
            return jsonify({
                'status': 'success',
                'macro': macro
            })
        return jsonify({
            'status': 'error',
            'message': f"Macro with ID {macro_id} not found"
        }), 404
    except Exception as e:
        logger.error(f"Error getting macro {macro_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/macros', methods=['POST'])
def api_save_macro():
    """API endpoint to save a macro"""
    try:
        macro_data = request.json
        result = save_macro(macro_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error saving macro: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/macros/<macro_id>', methods=['DELETE'])
def api_delete_macro(macro_id):
    """API endpoint to delete a macro by ID"""
    try:
        result = delete_macro(macro_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error deleting macro {macro_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

def execute_macro(macro_id, mode='normal'):
    """
    Execute a macro
    
    Args:
        macro_id: ID of the macro to execute (can be an integer or string)
        mode: Execution mode ('normal' or 'dry-run')
        
    Returns:
        Dictionary with execution result
    """
    # Check if the macro_id is 'test_macro' which is a special case for the test page
    if macro_id == 'test_macro':
        # Try to load the YAML file and create a temporary macro object for execution
        try:
            from automation_macros import AutomationMacro
            import yaml
            
            # Ensure the data directories exist
            os.makedirs("data/macros", exist_ok=True)
            os.makedirs("logs", exist_ok=True)
            
            # Check if the test macro exists
            test_macro_path = "data/macros/test_macro.yaml"
            if os.path.exists(test_macro_path):
                with open(test_macro_path, 'r') as f:
                    yaml_content = f.read()
                
                # Parse the YAML content
                macro_data = yaml.safe_load(yaml_content)
                
                # Create a temporary DB record for this test macro
                macro = Macro(
                    name=macro_data['metadata']['name'],
                    description=macro_data['metadata']['description'],
                    status='recorded',
                    step_count=len(macro_data['steps']),
                    execution_count=0
                )
                db_session.add(macro)
                db_session.commit()
                
                # Add step objects for this macro
                for index, step_data in enumerate(macro_data['steps']):
                    macro_step = MacroStep(
                        macro_id=macro.id,
                        step_number=index + 1,
                        action_type=step_data['type'],
                        parameters=json.dumps(step_data['params'] if 'params' in step_data else {}),
                        delay_before=0.0
                    )
                    db_session.add(macro_step)
                
                db_session.commit()
                
                # Override macro_id with the newly created database ID
                macro_id = macro.id
                
                logger.info(f"Created temporary macro with ID {macro_id} for test execution")
            else:
                return {'status': 'error', 'message': 'Test macro file not found'}
        except Exception as e:
            logger.error(f"Error loading test macro: {e}")
            return {'status': 'error', 'message': f'Error loading test macro: {e}'}
    
    # Check if the macro ID is numeric (from database)
    try:
        # Try to convert to int if it's a string representing a number
        if isinstance(macro_id, str) and macro_id.isdigit():
            macro_id = int(macro_id)
    except (ValueError, TypeError):
        pass  # Keep as is if not convertible
    
    # Now get the macro from the database
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        return {'status': 'error', 'message': f'Macro not found with ID {macro_id}'}
    
    # Log the execution attempt
    logger.info(f"Executing macro {macro_id} in {mode} mode")
    
    try:
        # In a real implementation, this would execute the macro
        # Here we just update the execution count and time
        macro.status = 'running'
        macro.last_execution_time = datetime.now()  # Use last_execution_time instead of last_execution
        macro.execution_count += 1
        db_session.commit()
        
        # Prepare the result
        result = {
            'status': 'running',
            'macro_id': macro_id,
            'mode': mode,
            'name': macro.name,
            'description': macro.description,
            'started_at': macro.last_execution_time.isoformat() if hasattr(macro, 'last_execution_time') and macro.last_execution_time else None,
        }
        
        # For normal execution, connect to the local automation server
        # For dry-run, just simulate the execution in the browser
        if mode == 'normal':
            # Get the automation server URL from environment
            server_url = os.environ.get('AUTOMATION_SERVER_URL')
            if not server_url:
                return {
                    'status': 'error',
                    'message': 'Automation server URL not configured. Please configure it in the Server URL Manager.',
                    'macro_id': macro_id
                }
                
            # Log the attempt to connect to the server
            logger.info(f"Connecting to automation server at {server_url}")
            result['server_url'] = server_url
            
            # Create a temporary directory for execution logs
            log_dir = os.path.join(os.getcwd(), 'logs', 'macros', str(macro_id))
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f"execution_{int(time.time())}.log")
            
            # Log the created log path
            logger.info(f"Created log file at {log_path}")
            result['log_path'] = log_path
            
            # Record the log path for later retrieval
            with open(log_path, 'w') as f:
                f.write(f"Starting execution of macro {macro.name} (ID: {macro_id}) at {datetime.now().isoformat()}\n")
                f.write(f"Mode: {mode}\n")
                f.write(f"Server URL: {server_url}\n")
                f.write("Steps to execute:\n")
                
                # Write the steps to the log
                for i, step in enumerate(macro.steps):
                    step_params = json.loads(step.parameters) if isinstance(step.parameters, str) else step.parameters
                    f.write(f"  {i+1}. {step.action_type}: {json.dumps(step_params)}\n")
                
                f.write("\nExecution log:\n")
        
        return result
    except Exception as e:
        logger.error(f"Error executing macro {macro_id}: {e}")
        
        # Update the macro status
        try:
            macro.status = 'failed'
            db_session.commit()
        except:
            pass
            
        # Return the error
        return {
            'status': 'error',
            'message': str(e),
            'macro_id': macro_id
        }

@app.route('/api/automation/macros/<macro_id>/execute', methods=['POST'])
def api_execute_macro(macro_id):
    """API endpoint to execute a macro"""
    try:
        mode = request.json.get('mode', 'normal')
        result = execute_macro(macro_id, mode)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error executing macro {macro_id}: {e}")
        # Include the stack trace in the response for debugging
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(f"Stack trace: {stack_trace}")
        
        return jsonify({
            'status': 'error',
            'message': str(e),
            'details': stack_trace,
            'server_diagnostics': {
                'automation_server_url': os.environ.get('AUTOMATION_SERVER_URL', 'Not set')
            }
        })

def get_macro_status(macro_id):
    """
    Get the status of a running macro
    
    Args:
        macro_id: ID of the macro to check
        
    Returns:
        Dictionary with status information
    """
    # Check if the macro ID is numeric (from database)
    try:
        # Try to convert to int if it's a string representing a number
        if isinstance(macro_id, str) and macro_id.isdigit():
            macro_id = int(macro_id)
    except (ValueError, TypeError):
        pass  # Keep as is if not convertible
    
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        return {'status': 'error', 'message': 'Macro not found'}
    
    # In a real implementation, this would check the actual execution status
    # Here we just return the stored status
    status = 'completed'  # Default to completed for this example
    if macro.status == 'running':
        status = 'running'
    elif macro.status == 'failed':
        status = 'failed'
    
    # Find any log files for this macro
    log_dir = os.path.join(os.getcwd(), 'logs', 'macros', str(macro_id))
    log_path = None
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.startswith('execution_')]
        if log_files:
            # Get the most recent log file
            log_files.sort(reverse=True)
            log_path = os.path.join(log_dir, log_files[0])
    
    return {
        'status': status,
        'macro_id': macro_id,
        'name': macro.name,
        'description': macro.description,
        'execution_count': macro.execution_count,
        'last_execution': macro.last_execution_time.isoformat() if hasattr(macro, 'last_execution_time') and macro.last_execution_time else None,
        'log_path': log_path
    }

@app.route('/api/automation/macros/<macro_id>/status', methods=['GET'])
def api_get_macro_status(macro_id):
    """API endpoint to get the status of a running macro"""
    try:
        result = get_macro_status(macro_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting status for macro {macro_id}: {e}")
        # Include the stack trace in the response for debugging
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(f"Stack trace: {stack_trace}")
        
        return jsonify({
            'status': 'error',
            'message': str(e),
            'details': stack_trace,
            'server_diagnostics': {
                'automation_server_url': os.environ.get('AUTOMATION_SERVER_URL', 'Not set')
            }
        })

def stop_macro(macro_id):
    """
    Stop a running macro
    
    Args:
        macro_id: ID of the macro to stop (can be an integer or string)
        
    Returns:
        Dictionary with result status
    """
    # Check if the macro ID is numeric (from database)
    try:
        # Try to convert to int if it's a string representing a number
        if isinstance(macro_id, str) and macro_id.isdigit():
            macro_id = int(macro_id)
    except (ValueError, TypeError):
        pass  # Keep as is if not convertible
    
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        return {'status': 'error', 'message': f'Macro not found with ID {macro_id}'}
    
    # In a real implementation, this would send a stop signal to the automation server
    # Here we just update the status
    if macro.status == 'running':
        macro.status = 'stopped'
        db_session.commit()
        
        # Add stop message to log if exists
        log_dir = os.path.join(os.getcwd(), 'logs', 'macros', str(macro_id))
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.startswith('execution_')]
            if log_files:
                # Get the most recent log file
                log_files.sort(reverse=True)
                log_path = os.path.join(log_dir, log_files[0])
                try:
                    with open(log_path, 'a') as f:
                        f.write(f"\nExecution stopped manually at {datetime.now().isoformat()}\n")
                except Exception as e:
                    logger.error(f"Error updating log file: {e}")
        
        return {
            'status': 'stopped',
            'macro_id': macro_id,
            'name': macro.name,
            'message': 'Macro execution stopped successfully'
        }
    else:
        return {
            'status': 'not_running',
            'macro_id': macro_id,
            'name': macro.name,
            'message': 'Macro was not running'
        }

@app.route('/api/automation/macros/<macro_id>/stop', methods=['POST'])
def api_stop_macro(macro_id):
    """API endpoint to stop a running macro"""
    try:
        result = stop_macro(macro_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error stopping macro {macro_id}: {e}")
        # Include the stack trace in the response for debugging
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(f"Stack trace: {stack_trace}")
        
        return jsonify({
            'status': 'error',
            'message': str(e),
            'details': stack_trace,
            'server_diagnostics': {
                'automation_server_url': os.environ.get('AUTOMATION_SERVER_URL', 'Not set')
            }
        })

def get_log_content(log_path):
    """
    Get the content of a log file
    
    Args:
        log_path: Path to the log file
        
    Returns:
        String content of the log file or None if not found
    """
    try:
        # Sanitize and validate the log path to prevent directory traversal
        abs_path = os.path.abspath(log_path)
        base_logs_dir = os.path.abspath(os.path.join(os.getcwd(), 'logs'))
        
        # Verify that the requested path is within the logs directory
        if not abs_path.startswith(base_logs_dir):
            logger.warning(f"Attempted access to log file outside logs directory: {log_path}")
            return None
        
        if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            logger.warning(f"Log file does not exist: {abs_path}")
            return None
        
        # Read and return the log file content
        with open(abs_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading log file {log_path}: {e}")
        return None

@app.route('/api/automation/logs/<path:log_path>', methods=['GET'])
def api_get_log_content(log_path):
    """API endpoint to get the content of a log file"""
    try:
        content = get_log_content(log_path)
        if content is not None:
            return jsonify({
                'status': 'success',
                'content': content
            })
        return jsonify({
            'status': 'error',
            'message': f"Log file {log_path} not found"
        }), 404
    except Exception as e:
        logger.error(f"Error getting log content for {log_path}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@app.route('/api/logs', methods=['GET'])
def get_log_content_direct():
    """API endpoint to get the content of a log file directly (for test pages)"""
    try:
        log_path = request.args.get('path')
        if not log_path:
            return "No log path provided", 400
        
        # Use our own get_log_content function defined above
        content = get_log_content(log_path)
        if content is None:
            return "Log file not found", 404
        
        return content
    except Exception as e:
        logger.error(f"Error getting log content: {e}")
        return f"Error getting log content: {e}", 500

def create_sample_macro():
    """
    Create a sample macro for testing purposes
    
    Returns:
        ID of the created macro
    """
    # Create a sample macro with basic steps
    sample_steps = [
        {
            "type": "mouse_move",
            "params": {"x": 100, "y": 100}
        },
        {
            "type": "mouse_click",
            "params": {"button": "left", "clicks": 1}
        },
        {
            "type": "keyboard_type",
            "params": {"text": "Hello, world!"}
        },
        {
            "type": "keyboard_press",
            "params": {"key": "enter"}
        },
        {
            "type": "wait",
            "params": {"seconds": 2}
        }
    ]
    
    # Create the macro in the database
    macro = Macro(
        name="Sample Test Macro",
        description="A sample macro for testing the execution system",
        status='recorded',
        step_count=len(sample_steps),
        execution_count=0
    )
    
    db_session.add(macro)
    db_session.commit()
    
    # Now create the step objects
    for index, step in enumerate(sample_steps):
        macro_step = MacroStep(
            macro_id=macro.id,
            step_number=index + 1,
            action_type=step['type'],
            parameters=json.dumps(step['params']),
            delay_before=0.0
        )
        db_session.add(macro_step)
    
    db_session.commit()
    
    return macro.id

@app.route('/api/automation/sample', methods=['POST'])
def api_create_sample_macro():
    """API endpoint to create a sample macro for testing"""
    try:
        macro_id = create_sample_macro()
        return jsonify({
            'status': 'success',
            'macro_id': macro_id,
            'message': 'Sample macro created successfully'
        })
    except Exception as e:
        logger.error(f"Error creating sample macro: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/yaml-compile', methods=['POST'])
def api_compile_yaml():
    """API endpoint to test the YAML to TagUI compiler"""
    import tempfile
    from yaml_to_tagui import compile_yaml_to_tagui
    
    try:
        # Check if we have raw YAML content in the request
        if 'yaml_content' in request.json:
            yaml_content = request.json['yaml_content']
            
            # Create a temporary directory for the files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the YAML content to a file
                yaml_path = os.path.join(temp_dir, "temp.yaml")
                with open(yaml_path, "w") as f:
                    f.write(yaml_content)
                
                # Compile the YAML file to TagUI script
                output_path = os.path.join(temp_dir, "temp.tag")
                compile_yaml_to_tagui(yaml_path, output_path)
                
                # Read the compiled script
                with open(output_path, "r") as f:
                    tagui_script = f.read()
                
                return jsonify({
                    'status': 'success',
                    'tagui_script': tagui_script
                })
        
        # Check if we have a YAML file in the request
        elif 'yaml_file' in request.files:
            yaml_file = request.files['yaml_file']
            if yaml_file.filename == '':
                return jsonify({'status': 'error', 'message': 'No file selected'})
            
            # Create a temporary directory for the files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save the uploaded YAML file
                yaml_path = os.path.join(temp_dir, yaml_file.filename)
                yaml_file.save(yaml_path)
                
                # Compile the YAML file to TagUI script
                output_path = os.path.join(temp_dir, os.path.splitext(yaml_file.filename)[0] + ".tag")
                
                compile_yaml_to_tagui(yaml_path, output_path)
                
                # Read the compiled script
                with open(output_path, "r") as f:
                    tagui_script = f.read()
                
                return jsonify({
                    'status': 'success', 
                    'yaml_filename': yaml_file.filename,
                    'tagui_script': tagui_script
                })
        else:
            return jsonify({'status': 'error', 'message': 'No YAML content or file provided'})
    except Exception as e:
        logger.error(f"Error compiling YAML: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/automation/macros/<macro_id>/export', methods=['GET'])
def api_export_macro(macro_id):
    """API endpoint to export a macro to YAML format"""
    try:
        # Get the macro
        macro = db_session.query(Macro).get(macro_id)
        if not macro:
            return jsonify({
                'status': 'error',
                'message': f'Macro with ID {macro_id} not found'
            })
        
        # Get steps
        steps = db_session.query(MacroStep).filter_by(macro_id=macro.id).order_by(MacroStep.step_number).all()
        
        # Get variables
        variables = db_session.query(MacroVariable).filter_by(macro_id=macro.id).all()
        variables_dict = {}
        for var in variables:
            variables_dict[var.name] = {
                'description': var.description or f"Variable {var.name}",
                'type': var.variable_type or 'string',
                'default_value': var.default_value or '',
                'is_required': var.is_required == 1
            }
        
        # Format macro steps
        steps_data = []
        for step in steps:
            try:
                params = json.loads(step.parameters)
                steps_data.append({
                    'type': step.action_type,
                    'params': params,
                    'delay_before': step.delay_before
                })
            except:
                logger.warning(f"Could not parse parameters for step {step.id}")
        
        # Format tags
        tags = []
        if macro.tags:
            try:
                # Try to parse as JSON first
                tags = json.loads(macro.tags)
            except:
                # Fallback to comma-separated
                tags = [tag.strip() for tag in macro.tags.split(',') if tag.strip()]
        
        # Create YAML structure
        yaml_data = {
            'metadata': {
                'name': macro.name,
                'description': macro.description or '',
                'id': str(macro.id),
                'created_at': macro.creation_time.timestamp() if macro.creation_time else time.time(),
                'updated_at': macro.last_execution_time.timestamp() if macro.last_execution_time else time.time(),
                'tags': tags,
                'color': macro.color or 'secondary',
                'icon': macro.icon or 'robot'
            },
            'variables': variables_dict,
            'steps': steps_data
        }
        
        # Convert to YAML
        import yaml
        yaml_str = yaml.dump(yaml_data, default_flow_style=False)
        
        return jsonify({
            'status': 'success',
            'yaml': yaml_str
        })
    except Exception as e:
        logger.error(f"Error exporting macro {macro_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/macros/import', methods=['POST'])
def api_import_macro():
    """API endpoint to import a macro from YAML format"""
    try:
        # Get the YAML content
        if 'yaml' not in request.json:
            return jsonify({
                'status': 'error',
                'message': 'No YAML content provided'
            })
        
        yaml_content = request.json['yaml']
        
        # Parse YAML
        import yaml
        try:
            yaml_data = yaml.safe_load(yaml_content)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid YAML format: {str(e)}'
            })
        
        # Validate basic structure
        if 'metadata' not in yaml_data or 'steps' not in yaml_data:
            return jsonify({
                'status': 'error',
                'message': 'Invalid macro format: missing metadata or steps'
            })
        
        # Extract metadata
        metadata = yaml_data['metadata']
        name = metadata.get('name', 'Imported Macro')
        description = metadata.get('description', '')
        tags = metadata.get('tags', [])
        color = metadata.get('color', 'secondary')
        icon = metadata.get('icon', 'robot')
        
        # Create new macro
        macro = Macro(
            name=name,
            description=description,
            tags=json.dumps(tags) if isinstance(tags, list) else tags,
            color=color,
            icon=icon,
            status='imported',
            creation_time=datetime.now(),
            step_count=len(yaml_data['steps']),
            execution_count=0
        )
        db_session.add(macro)
        db_session.flush()  # Get ID without committing
        
        # Import steps
        for i, step_data in enumerate(yaml_data['steps']):
            step_type = step_data.get('type')
            params = step_data.get('params', {})
            delay = step_data.get('delay_before', 0.0)
            
            if not step_type:
                continue
                
            step = MacroStep(
                macro_id=macro.id,
                step_number=i + 1,
                action_type=step_type,
                parameters=json.dumps(params),
                delay_before=delay
            )
            db_session.add(step)
        
        # Import variables if present
        if 'variables' in yaml_data and yaml_data['variables']:
            for name, var_data in yaml_data['variables'].items():
                variable = MacroVariable(
                    macro_id=macro.id,
                    name=name,
                    description=var_data.get('description', f"Variable {name}"),
                    default_value=var_data.get('default_value', ''),
                    current_value=var_data.get('default_value', ''),
                    variable_type=var_data.get('type', 'string'),
                    is_required=1 if var_data.get('is_required', True) else 0
                )
                db_session.add(variable)
        
        # Commit changes
        db_session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Macro imported successfully',
            'macro_id': macro.id
        })
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error importing macro: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

# Variable detection and management API endpoints
@app.route('/api/automation/macros/<macro_id>/detect-variables', methods=['POST'])
def api_detect_variables(macro_id):
    """API endpoint to detect variables in a macro"""
    try:
        variables = variable_detector.detect_variables_in_macro(macro_id)
        return jsonify({
            'status': 'success',
            'variables': variables
        })
    except Exception as e:
        logger.error(f"Error detecting variables in macro {macro_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/macros/<macro_id>/register-variables', methods=['POST'])
def api_register_variables(macro_id):
    """API endpoint to register detected variables in the database"""
    try:
        variables = variable_detector.register_variables_for_macro(macro_id)
        return jsonify({
            'status': 'success',
            'variables': variables
        })
    except Exception as e:
        logger.error(f"Error registering variables for macro {macro_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/macros/<macro_id>/variables', methods=['GET'])
def api_get_variables(macro_id):
    """API endpoint to get all variables for a macro"""
    try:
        variables = variable_detector.get_variables_for_macro(macro_id)
        return jsonify({
            'status': 'success',
            'variables': variables
        })
    except Exception as e:
        logger.error(f"Error getting variables for macro {macro_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/automation/variables/<variable_id>', methods=['PUT'])
def api_update_variable(variable_id):
    """API endpoint to update a variable's properties"""
    try:
        data = request.json
        
        # Check if it's a full variable update or just a value update
        if 'value' in data and len(data) == 1:
            # Simple value update
            success = variable_detector.update_variable_value(variable_id, data['value'])
        else:
            # Full variable update
            success = variable_detector.update_variable(variable_id, data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Variable updated successfully'
            })
        return jsonify({
            'status': 'error',
            'message': f'Failed to update variable {variable_id}'
        })
    except Exception as e:
        logger.error(f"Error updating variable {variable_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })
        
@app.route('/variable_prompt', methods=['GET'])
def variable_prompt():
    """
    Display a form to prompt for variable values during macro execution.
    This is opened by the automation executor when variables need to be filled in.
    """
    try:
        # Get parameters
        macro_id = request.args.get('macro_id')
        temp_file = request.args.get('temp_file')
        
        if not macro_id or not temp_file:
            return render_template('error.html', 
                                   error="Missing required parameters", 
                                   details="Both macro_id and temp_file are required.")
        
        # Check if the temp file exists
        if not os.path.exists(temp_file):
            return render_template('error.html', 
                                   error="Invalid temporary file", 
                                   details="The specified temporary file does not exist.")
        
        # Load variable data from the temp file
        with open(temp_file, 'r') as f:
            data = json.load(f)
            
        # Render the variable prompt template
        return render_template('variable_prompt.html',
                              macro_id=macro_id,
                              macro_name=data.get('macro_name', 'Unknown Macro'),
                              variables=data.get('variables', []),
                              timeout=data.get('timeout', 30),
                              temp_file=temp_file)
    except Exception as e:
        logger.error(f"Error displaying variable prompt: {e}")
        return render_template('error.html', 
                               error="Error displaying variable prompt", 
                               details=str(e))

@app.route('/variable_prompt_submit', methods=['POST'])
def variable_prompt_submit():
    """
    Handle submission of variable values from the variable prompt form.
    Saves the values to a response file that will be read by the automation executor.
    """
    try:
        data = request.json
        macro_id = data.get('macro_id')
        variables = data.get('variables', {})
        temp_file = data.get('temp_file')
        
        if not macro_id or not temp_file:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters'
            })
        
        # Save the response to a file that will be read by the automation executor
        response_file = temp_file + '.response'
        with open(response_file, 'w') as f:
            json.dump(variables, f)
            
        return jsonify({
            'status': 'success',
            'message': 'Variables saved successfully'
        })
    except Exception as e:
        logger.error(f"Error saving variable prompt response: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })
        
@app.route('/variable_documentation', methods=['GET'])
def variable_documentation():
    """
    Display documentation for the variable system.
    Helps users understand how to use variables, formatting, and conditional expressions.
    """
    try:
        return render_template('variable_documentation.html')
    except Exception as e:
        logger.error(f"Error displaying variable documentation: {e}")
        return render_template('error.html', 
                               error="Error displaying variable documentation", 
                               details=str(e))

@app.route('/variable_editor/<macro_id>', methods=['GET'])
def variable_editor(macro_id):
    """
    Display the variable editor for a specific macro.
    This page allows editing variable properties such as description, default value, type, etc.
    """
    try:
        # Get the macro
        macro = db_session.query(Macro).get(macro_id)
        if not macro:
            return render_template('error.html', 
                                error="Macro not found", 
                                details=f"No macro found with ID {macro_id}")
        
        # Get variables for this macro
        variables_dict = variable_detector.get_variables_for_macro(macro_id)
        variables = []
        
        # Convert dictionary to list for easier template rendering
        for name, var_data in variables_dict.items():
            # Extract choice options from metadata if present
            choice_options = []
            if var_data.get('type') == 'choice' and 'id' in var_data:
                # Fetch the variable from database to access its metadata
                variable = db_session.query(MacroVariable).get(var_data['id'])
                if variable and variable.metadata:
                    try:
                        metadata = json.loads(variable.metadata)
                        choice_options = metadata.get('choice_options', [])
                    except:
                        pass
            
            # Add to variables list
            var_data['choice_options'] = choice_options
            variables.append(var_data)
            
        # Define a Jinja2 filter for variable type badge styling
        @app.template_filter('format_variable_type_badge')
        def format_variable_type_badge(variable_type):
            type_badges = {
                'string': 'primary',
                'number': 'success',
                'boolean': 'warning',
                'choice': 'secondary',
                'date': 'info'
            }
            return type_badges.get(variable_type, 'primary')
            
        return render_template('variable_editor.html',
                              macro=macro,
                              variables=variables)
    except Exception as e:
        logger.error(f"Error displaying variable editor: {e}")
        return render_template('error.html', 
                              error="Error displaying variable editor", 
                              details=str(e))

@app.route('/metrics', methods=['GET'])
def metrics_dashboard():
    """
    Dashboard for metrics including time saved by automations.
    Shows KPIs for automation effectiveness and time savings.
    """
    try:
        return render_template('metrics_dashboard.html')
    except Exception as e:
        logger.error(f"Error displaying metrics dashboard: {e}")
        return render_template('error.html', 
                              error="Error displaying metrics dashboard", 
                              details=str(e))

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """
    Get all metrics as JSON for the metrics dashboard.
    Returns system-wide metrics for automation effectiveness.
    """
    try:
        metrics = db_session.query(Metric).all()
        metrics_data = {}
        
        for metric in metrics:
            metrics_data[metric.name] = {
                'value': float(metric.value),
                'timestamp': metric.timestamp.isoformat() if metric.timestamp else None,
                'notes': metric.notes
            }
            
        # Calculate additional stats for macros
        total_macros = db_session.query(func.count(Macro.id)).scalar() or 0
        active_macros = db_session.query(func.count(Macro.id)).filter(
            Macro.execution_count > 0
        ).scalar() or 0
        
        total_executions = db_session.query(func.sum(Macro.execution_count)).scalar() or 0
        successful_executions = db_session.query(func.sum(Macro.success_count)).scalar() or 0
        
        # Success rate
        success_rate = 0
        if total_executions > 0:
            success_rate = (successful_executions / total_executions) * 100
            
        # Add these stats to the response
        metrics_data['total_macros'] = {'value': total_macros}
        metrics_data['active_macros'] = {'value': active_macros}
        metrics_data['total_executions'] = {'value': total_executions}
        metrics_data['successful_executions'] = {'value': successful_executions}
        metrics_data['success_rate'] = {'value': success_rate}
        
        # If hours_saved_total metric doesn't exist, add it with default 0
        if 'hours_saved_total' not in metrics_data:
            metrics_data['hours_saved_total'] = {'value': 0.0}
            
        return jsonify(metrics_data)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/macros', methods=['GET'])
def get_macro_metrics():
    """
    Get metrics for individual macros.
    Returns performance data for each macro including success rate and time saved.
    """
    try:
        macros = db_session.query(Macro).all()
        
        macro_metrics = []
        for macro in macros:
            # Skip macros that have never been executed
            if not macro.execution_count:
                continue
                
            success_rate = 0
            if macro.execution_count > 0:
                success_rate = (macro.success_count / macro.execution_count) * 100
                
            # Convert seconds to hours for display
            hours_saved = (macro.total_time_saved or 0) / 3600.0
                
            macro_metrics.append({
                'id': macro.id,
                'name': macro.name,
                'execution_count': macro.execution_count,
                'success_count': macro.success_count,
                'failure_count': macro.failure_count,
                'success_rate': success_rate,
                'original_sequence_duration': macro.original_sequence_duration,
                'total_time_saved_seconds': macro.total_time_saved,
                'total_time_saved_hours': hours_saved,
                'last_execution_time': macro.last_execution_time.isoformat() if macro.last_execution_time else None
            })
            
        return jsonify(macro_metrics)
    except Exception as e:
        logger.error(f"Error getting macro metrics: {e}")
        return jsonify({'error': str(e)}), 500

def start_monitoring_components():
    """Initialize and start the monitoring components"""
    from settings import Settings
    from event_listener import EventListener
    from context_analyzer import ContextAnalyzer
    from pattern_detector import PatternDetector
    from reasoning_engine import ReasoningEngine
    from scheduled_jobs import JobScheduler
    
    try:
        # Initialize components
        settings = Settings()
        event_listener = EventListener(settings)
        context_analyzer = ContextAnalyzer(settings)
        pattern_detector = PatternDetector(settings)
        reasoning_engine = ReasoningEngine(settings)
        job_scheduler = JobScheduler(settings)
        
        # Connect components
        event_listener.set_analyzer(context_analyzer)
        context_analyzer.set_pattern_detector(pattern_detector)
        pattern_detector.set_reasoning_engine(reasoning_engine)
        
        # Start components in reverse order
        reasoning_engine.start()
        pattern_detector.start()
        context_analyzer.start()
        event_listener.start()
        job_scheduler.start()
        
        logger.info("All monitoring components started successfully")
        
        # Store components for future reference
        return {
            'event_listener': event_listener,
            'context_analyzer': context_analyzer,
            'pattern_detector': pattern_detector,
            'reasoning_engine': reasoning_engine,
            'job_scheduler': job_scheduler
        }
    except Exception as e:
        logger.error(f"Error starting monitoring components: {e}")
        return {}

# Initialize components dict
monitoring_components = {}

if __name__ == '__main__':
    try:
        # Initialize default settings
        init_default_settings()
        
        # Seed demo data
        seed_demo_data()
        
        # Start monitoring components if enabled
        if os.environ.get('AUTOMATION_SERVER_URL') and settings.get_setting('monitoring_enabled', default=True):
            monitoring_components = start_monitoring_components()
        
        # Start Flask app
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"Error starting BettermanAI: {e}")
    finally:
        # Stop monitoring components
        for component in monitoring_components.values():
            if hasattr(component, 'stop'):
                component.stop()
                
        db_session.remove()
