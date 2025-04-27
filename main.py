import os
import time
import json
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
import signal
import sys
import random

from database import init_db, db_session
from models import Event, EventSequence, Pattern, Suggestion, Macro, MacroStep, Setting, AIAnalysisReport
from settings import Settings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create and configure Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "betterman_ai_secret")

# Initialize database
init_db()

# Check and update database schema if needed
from database import check_and_update_schema
check_and_update_schema()

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
                    'execution_count': 5,
                    'step_count': 8,
                    'status': 'recorded'
                },
                {
                    'name': 'Daily Report Generator',
                    'description': 'Extracts data from multiple sources and compiles it into a daily report',
                    'creation_time': datetime.now() - timedelta(days=10, hours=5),
                    'last_execution_time': datetime.now() - timedelta(hours=22),
                    'execution_count': 15,
                    'step_count': 12,
                    'status': 'recorded'
                },
                {
                    'name': 'Invoice Data Entry',
                    'description': 'Extracts data from invoice PDFs and enters it into accounting software',
                    'creation_time': datetime.now() - timedelta(days=15, hours=8),
                    'last_execution_time': None,
                    'execution_count': 0,
                    'step_count': 0,
                    'status': 'recording'
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

@app.route('/macro/<int:macro_id>')
def view_macro(macro_id):
    """View a specific macro"""
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        flash('Macro not found', 'error')
        return redirect(url_for('macros'))
    
    steps = db_session.query(MacroStep).filter_by(macro_id=macro.id).order_by(MacroStep.step_number).all()
    
    return render_template('macro.html', macro=macro, steps=steps)

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
def execute_macro(macro_id):
    """Execute a macro"""
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        return jsonify({'success': False, 'error': 'Macro not found'})
    
    # In a real implementation, this would execute the macro
    # Here we just update the execution count and time
    macro.status = 'executing'
    db_session.commit()
    
    # Simulate execution delay
    time.sleep(2)
    
    macro.status = 'recorded'
    macro.execution_count += 1
    macro.last_execution_time = datetime.now()
    db_session.commit()
    
    return jsonify({'success': True})

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
def test_connection():
    """Test connection to the local automation server"""
    import requests
    from requests.exceptions import RequestException

    data = request.json
    server_url = data.get('server_url', os.environ.get('AUTOMATION_SERVER_URL', ''))
    
    if not server_url:
        return jsonify({'success': False, 'error': 'No server URL provided'})
    
    try:
        # Try to get the status of the server
        response = requests.get(f"{server_url}/api/status", timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            
            # Update the settings with the new URL if successful
            settings.set_setting('automation_server_url', server_url)
            
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
    db_session.remove()
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
        'automation_execution_confirmation': True
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

def start_monitoring_components():
    """Initialize and start the monitoring components"""
    from settings import Settings
    from event_listener import EventListener
    from context_analyzer import ContextAnalyzer
    from pattern_detector import PatternDetector
    from reasoning_engine import ReasoningEngine
    
    try:
        # Initialize components
        settings = Settings()
        event_listener = EventListener(settings)
        context_analyzer = ContextAnalyzer(settings)
        pattern_detector = PatternDetector(settings)
        reasoning_engine = ReasoningEngine(settings)
        
        # Connect components
        event_listener.set_analyzer(context_analyzer)
        context_analyzer.set_pattern_detector(pattern_detector)
        pattern_detector.set_reasoning_engine(reasoning_engine)
        
        # Start components in reverse order
        reasoning_engine.start()
        pattern_detector.start()
        context_analyzer.start()
        event_listener.start()
        
        logger.info("All monitoring components started successfully")
        
        # Store components for future reference
        return {
            'event_listener': event_listener,
            'context_analyzer': context_analyzer,
            'pattern_detector': pattern_detector,
            'reasoning_engine': reasoning_engine
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
