import json
from datetime import datetime, timedelta
from database import db_session
from models import MacroExecution, Macro

def add_demo_executions():
    """Add demo execution data with screenshots"""
    try:
        # Get the first macro ID (we'll use this for our demo executions)
        macro = db_session.query(Macro).first()
        if not macro:
            print("No macros found in the database. Please run the application first to seed data.")
            return
            
        # Check if we already have executions
        existing_count = db_session.query(MacroExecution).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} executions. Skipping demo execution data.")
            return
            
        print(f"Adding demo execution data for macro {macro.id}: {macro.name}")
            
        # Create demo executions with screenshot data
        executions = [
            {
                'macro_id': macro.id,
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
                'macro_id': macro.id,
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
                'macro_id': macro.id,
                'start_time': datetime.now() - timedelta(days=3, hours=2),
                'end_time': datetime.now() - timedelta(days=3, hours=2, minutes=1),
                'status': 'failed',
                'original_sequence_duration': 45.0,
                'execution_duration': 12.3,
                'error_message': 'Target element not found',
                'execution_data': json.dumps({
                    'before_screenshot': 'data/screenshots/email_before_failed.png',
                    'after_screenshot': 'data/screenshots/email_after_failed.png',
                    'diff_screenshot': 'data/screenshots/email_diff_failed.png',
                    'screen_change_percentage': 2.1,
                    'warning': 'Minimal screen change detected (2.1%). The macro might not have completed its intended actions.'
                })
            },
            {
                'macro_id': macro.id,
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
            
        db_session.commit()
        print(f"Added {len(executions)} demo executions with screenshot data")
        
    except Exception as e:
        db_session.rollback()
        print(f"Error adding demo execution data: {e}")

if __name__ == "__main__":
    add_demo_executions()