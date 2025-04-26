import os
import logging
from flask import render_template, redirect, url_for, request, jsonify, send_from_directory
from database import db_session
from models import Suggestion, Macro, Pattern, Event, EventSequence
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def init_ui_routes(app, settings):
    """Initialize UI routes for the Flask app"""
    
    @app.route('/')
    def index():
        """Main application page"""
        monitoring_enabled = settings.get_setting('monitoring_enabled')
        event_count = db_session.query(Event).count()
        pattern_count = db_session.query(Pattern).count()
        suggestion_count = db_session.query(Suggestion).filter(Suggestion.status == 'pending').count()
        
        # Get statistics for display
        stats = {
            'event_count': event_count,
            'pattern_count': pattern_count,
            'suggestion_count': suggestion_count,
            'monitoring_since': settings.get_setting('monitoring_start_time') or 'Not started'
        }
        
        return render_template('index.html', 
                              monitoring_enabled=monitoring_enabled, 
                              stats=stats)
                              
    @app.route('/settings')
    def settings_page():
        """Settings page"""
        all_settings = {
            'monitoring_enabled': settings.get_setting('monitoring_enabled'),
            'track_mouse_moves': settings.get_setting('track_mouse_moves'),
            'track_mouse_clicks': settings.get_setting('track_mouse_clicks'),
            'track_mouse_scrolls': settings.get_setting('track_mouse_scrolls'),
            'track_keyboard': settings.get_setting('track_keyboard'),
            'track_windows': settings.get_setting('track_windows'),
            'enable_notifications': settings.get_setting('enable_notifications'),
            'show_execution_countdown': settings.get_setting('show_execution_countdown')
        }
        
        return render_template('settings.html', settings=all_settings)
        
    @app.route('/settings/update', methods=['POST'])
    def update_settings():
        """Update settings via AJAX"""
        setting_name = request.form.get('name')
        setting_value = request.form.get('value')
        
        if setting_name:
            # Convert to boolean if value is 'true' or 'false'
            if setting_value.lower() == 'true':
                setting_value = True
            elif setting_value.lower() == 'false':
                setting_value = False
                
            settings.set_setting(setting_name, setting_value)
            
            # Special handling for monitoring_enabled
            if setting_name == 'monitoring_enabled' and setting_value:
                settings.set_setting('monitoring_start_time', datetime.now().isoformat())
                
        return jsonify({'success': True})
        
    @app.route('/suggestions')
    def suggestions():
        """View automation suggestions"""
        pending_suggestions = db_session.query(Suggestion).filter(
            Suggestion.status == 'pending'
        ).order_by(Suggestion.creation_time.desc()).all()
        
        accepted_suggestions = db_session.query(Suggestion).filter(
            Suggestion.status == 'accepted'
        ).order_by(Suggestion.creation_time.desc()).all()
        
        rejected_suggestions = db_session.query(Suggestion).filter(
            Suggestion.status == 'rejected'
        ).order_by(Suggestion.creation_time.desc()).limit(5).all()
        
        return render_template('suggestions.html',
                              pending_suggestions=pending_suggestions,
                              accepted_suggestions=accepted_suggestions,
                              rejected_suggestions=rejected_suggestions)
                              
    @app.route('/suggestion/<int:suggestion_id>')
    def view_suggestion(suggestion_id):
        """View a specific suggestion"""
        suggestion = db_session.query(Suggestion).get(suggestion_id)
        if not suggestion:
            return redirect(url_for('suggestions'))
            
        # Get the pattern for this suggestion
        pattern = db_session.query(Pattern).get(suggestion.pattern_id)
        
        # Parse steps
        steps = json.loads(suggestion.steps) if suggestion.steps else []
        
        return render_template('suggestion.html', 
                              suggestion=suggestion,
                              pattern=pattern,
                              steps=steps)
                              
    @app.route('/suggestion/<int:suggestion_id>/action', methods=['POST'])
    def suggestion_action(suggestion_id):
        """Accept or reject a suggestion"""
        suggestion = db_session.query(Suggestion).get(suggestion_id)
        if not suggestion:
            return jsonify({'success': False, 'error': 'Suggestion not found'})
            
        action = request.form.get('action')
        
        if action == 'accept':
            # Create a macro from the suggestion
            from macro_recorder import MacroRecorder
            recorder = MacroRecorder(settings)
            
            # Create an empty macro
            recorder.start_recording(
                macro_name=suggestion.title,
                description=suggestion.description
            )
            
            # Stop recording to create the empty macro
            macro_id = recorder.stop_recording()
            
            if macro_id:
                # Update suggestion status
                suggestion.status = 'accepted'
                suggestion.action_time = datetime.now()
                suggestion.macro_id = macro_id
                db_session.commit()
                
                # Redirect to macro recording page
                return jsonify({
                    'success': True,
                    'redirect': url_for('edit_macro', macro_id=macro_id)
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to create macro'})
                
        elif action == 'reject':
            suggestion.status = 'rejected'
            suggestion.action_time = datetime.now()
            db_session.commit()
            return jsonify({'success': True})
            
        return jsonify({'success': False, 'error': 'Invalid action'})
        
    @app.route('/macros')
    def macros():
        """View recorded macros"""
        all_macros = db_session.query(Macro).order_by(Macro.creation_time.desc()).all()
        return render_template('macros.html', macros=all_macros)
        
    @app.route('/macro/<int:macro_id>')
    def view_macro(macro_id):
        """View a specific macro"""
        macro = db_session.query(Macro).get(macro_id)
        if not macro:
            return redirect(url_for('macros'))
            
        # Get steps
        from models import MacroStep
        steps = db_session.query(MacroStep).filter(
            MacroStep.macro_id == macro_id
        ).order_by(MacroStep.step_number).all()
        
        return render_template('macro.html', macro=macro, steps=steps)
        
    @app.route('/macro/<int:macro_id>/edit')
    def edit_macro(macro_id):
        """Edit a macro"""
        macro = db_session.query(Macro).get(macro_id)
        if not macro:
            return redirect(url_for('macros'))
            
        return render_template('edit_macro.html', macro=macro)
        
    @app.route('/macro/<int:macro_id>/record', methods=['POST'])
    def record_macro(macro_id):
        """Start recording a macro"""
        macro = db_session.query(Macro).get(macro_id)
        if not macro:
            return jsonify({'success': False, 'error': 'Macro not found'})
            
        # Start recording
        from macro_recorder import MacroRecorder
        recorder = MacroRecorder(settings)
        
        success = recorder.start_recording(
            macro_name=macro.name,
            description=macro.description
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to start recording'})
            
    @app.route('/macro/<int:macro_id>/stop', methods=['POST'])
    def stop_recording(macro_id):
        """Stop recording a macro"""
        macro = db_session.query(Macro).get(macro_id)
        if not macro:
            return jsonify({'success': False, 'error': 'Macro not found'})
            
        # Stop recording
        from macro_recorder import MacroRecorder
        recorder = MacroRecorder(settings)
        
        new_macro_id = recorder.stop_recording()
        
        if new_macro_id:
            return jsonify({
                'success': True,
                'redirect': url_for('view_macro', macro_id=new_macro_id)
            })
        else:
            return jsonify({'success': False, 'error': 'No steps were recorded'})
            
    @app.route('/macro/<int:macro_id>/execute', methods=['POST'])
    def execute_macro(macro_id):
        """Execute a macro"""
        macro = db_session.query(Macro).get(macro_id)
        if not macro:
            return jsonify({'success': False, 'error': 'Macro not found'})
            
        # Execute macro
        from automation_executor import AutomationExecutor
        executor = AutomationExecutor(settings)
        
        success = executor.execute_macro(macro_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to execute macro'})
            
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
            return redirect(url_for('patterns'))
            
        # Get sequences
        sequence_ids = json.loads(pattern.sequence_ids) if pattern.sequence_ids else []
        sequences = []
        
        for seq_id in sequence_ids:
            seq = db_session.query(EventSequence).get(seq_id)
            if seq:
                try:
                    metadata = json.loads(seq.metadata)
                    sequences.append({
                        'id': seq.id,
                        'start_time': seq.start_time,
                        'end_time': seq.end_time,
                        'event_count': seq.event_count,
                        'windows': metadata.get('windows', []),
                        'duration': metadata.get('duration', 0)
                    })
                except:
                    pass
                    
        return render_template('pattern.html', pattern=pattern, sequences=sequences)
        
    @app.route('/statistics')
    def statistics():
        """View system statistics"""
        # Event statistics
        event_count = db_session.query(Event).count()
        recent_events = db_session.query(Event).order_by(
            Event.timestamp.desc()
        ).limit(100).all()
        
        # Group events by type
        event_types = {}
        for event in recent_events:
            event_type = event.type
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
        # Get event timestamps for time-based graph
        event_times = db_session.query(Event.timestamp).order_by(
            Event.timestamp
        ).all()
        
        # Group by hour for graph
        hourly_events = {}
        for timestamp in event_times:
            hour = timestamp[0].replace(minute=0, second=0, microsecond=0)
            hourly_events[hour] = hourly_events.get(hour, 0) + 1
            
        hourly_data = {
            'labels': [h.strftime('%Y-%m-%d %H:%M') for h in sorted(hourly_events.keys())],
            'data': [hourly_events[h] for h in sorted(hourly_events.keys())]
        }
        
        # Pattern statistics
        pattern_count = db_session.query(Pattern).count()
        patterns_by_status = db_session.query(
            Pattern.status, db_session.func.count(Pattern.id)
        ).group_by(Pattern.status).all()
        
        pattern_status = {status: count for status, count in patterns_by_status}
        
        # Automation statistics
        macro_count = db_session.query(Macro).count()
        suggestion_count = db_session.query(Suggestion).count()
        
        statistics = {
            'event_count': event_count,
            'pattern_count': pattern_count,
            'macro_count': macro_count,
            'suggestion_count': suggestion_count,
            'event_types': event_types,
            'pattern_status': pattern_status,
            'hourly_events': hourly_data
        }
        
        return render_template('statistics.html', statistics=statistics)
        
    @app.route('/privacy')
    def privacy():
        """Privacy information"""
        return render_template('privacy.html')
        
    @app.route('/about')
    def about():
        """About BettermanAI"""
        return render_template('about.html')
        
    @app.route('/logs')
    def logs():
        """View system logs"""
        if not os.path.isdir('logs'):
            return render_template('logs.html', logs=[], error="No logs found")
            
        log_files = [f for f in os.listdir('logs') if f.endswith('.json')]
        logs = []
        
        for log_file in sorted(log_files, reverse=True)[:5]:  # Most recent 5 log files
            try:
                with open(os.path.join('logs', log_file), 'r') as f:
                    log_data = [json.loads(line) for line in f.readlines()]
                    logs.extend(log_data[:100])  # First 100 entries
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
                
        return render_template('logs.html', logs=logs[:1000])  # Limit to 1000 entries
        
    @app.route('/static/<path:path>')
    def send_static(path):
        """Serve static files"""
        return send_from_directory('static', path)
        
    @app.route('/toggle_monitoring', methods=['POST'])
    def toggle_monitoring():
        """Toggle monitoring status"""
        current = settings.get_setting('monitoring_enabled')
        settings.set_setting('monitoring_enabled', not current)
        
        if not current:  # Turning on
            settings.set_setting('monitoring_start_time', datetime.now().isoformat())
            
            # Start services
            from main import init_services
            init_services()
            
        return jsonify({'success': True, 'monitoring': not current})
