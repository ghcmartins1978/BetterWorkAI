import os
import logging

logger = logging.getLogger(__name__)

# Function to check if we're running inside Electron
def is_running_in_electron():
    """
    Detect if the application is running inside Electron.
    Returns True if running in Electron, False otherwise.
    """
    is_electron = False
    
    # Check environment variables set by our Electron app
    if os.environ.get('RUNNING_IN_ELECTRON') == '1':
        is_electron = True
    
    # Check parent process (may be electron on some platforms)
    try:
        import psutil
        current_process = psutil.Process()
        parent = current_process.parent()
        if parent and 'electron' in parent.name().lower():
            is_electron = True
    except (ImportError, Exception) as e:
        logger.debug(f"Error checking parent process: {e}")
    
    logger.info(f"Running in Electron: {is_electron}")
    return is_electron

# Function to adjust application settings for Electron
def configure_for_electron(app):
    """
    Configure Flask app for running inside Electron.
    
    Args:
        app: Flask application instance
    """
    if not is_running_in_electron():
        return
    
    logger.info("Configuring application for Electron environment")
    
    # No need for HTTPS in Electron (all local)
    app.config['PREFERRED_URL_SCHEME'] = 'http'
    
    # Use SQLite by default in Electron
    if 'DATABASE_URL' not in os.environ:
        # Make sure the data directory exists
        data_dir = os.path.join(os.getcwd(), 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        db_path = os.path.join(data_dir, 'betterman.db')
        os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"
        logger.info(f"Setting SQLite database path: {db_path}")
    
    # Set Helper URL for local connection
    if 'AUTOMATION_SERVER_URL' not in os.environ:
        os.environ['AUTOMATION_SERVER_URL'] = 'http://127.0.0.1:17400'
    
    # Disable certain web-specific security headers that aren't needed in Electron
    @app.after_request
    def remove_unnecessary_headers(response):
        headers_to_remove = ['X-Frame-Options', 'Content-Security-Policy']
        for header in headers_to_remove:
            if header in response.headers:
                del response.headers[header]
        return response