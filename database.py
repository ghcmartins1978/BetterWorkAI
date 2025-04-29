import os
import logging
import threading
import queue
import time
import random
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError, PendingRollbackError

logger = logging.getLogger(__name__)

# Set a default SQLite database path if DATABASE_URL is not provided
default_db_path = os.path.join(os.getcwd(), 'data', 'betterman.db')
os.makedirs(os.path.dirname(default_db_path), exist_ok=True)

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    database_url = f"sqlite:///{default_db_path}"
    logger.info(f"DATABASE_URL not set, using default SQLite database: {default_db_path}")

# Configure SQLAlchemy engine with improved connection pooling settings
connect_args = {}
if database_url.startswith('sqlite'):
    # SQLite connect_args - these vary by SQLite version
    try:
        # Try with check_same_thread for most SQLite versions
        connect_args = {"check_same_thread": False}
    except:
        # Fallback with no special args
        connect_args = {}

engine = create_engine(
    database_url, 
    pool_recycle=1800,      # Recycle connections after 30 minutes idle
    pool_pre_ping=True,     # Check connection validity before using
    pool_size=10,           # Maximum number of connections to keep
    max_overflow=20,        # Maximum overflow connections
    connect_args=connect_args
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a scoped session for backward compatibility
db_session = scoped_session(SessionLocal)

Base = declarative_base()
Base.query = db_session.query_property()

# Context manager for database sessions
@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.
    This ensures that sessions are properly closed and rolled back in case of errors.
    
    Usage:
        with session_scope() as db:
            result = db.query(Model).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Connection pool event listeners (to be registered AFTER initialization)
def register_connection_events():
    """Register listeners for connection events (used after initialization)"""
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        """Listener for connection events to log when connections are created"""
        logger.debug("Database connection created")

    @event.listens_for(engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        """Listener for connection checkout events to ensure the connection is still alive"""
        # This is handled by pool_pre_ping=True but adding extra logging for visibility
        logger.debug("Database connection checked out from pool")

    # Only ping at checkout time, not on engine_connect which conflicts with DDL operations
    if engine.dialect.name == 'postgresql':
        @event.listens_for(engine, "connect")
        def ping_postgresql_connection(dbapi_connection, connection_record):
            """Ping the database at connection creation time to verify it's responsive"""
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                logger.debug("Database ping successful (PostgreSQL)")
            except Exception as e:
                logger.warning(f"Database ping failed (PostgreSQL): {e}")
                # Let pool_pre_ping handle reconnection

# Async database writer class
class AsyncDatabaseWriter:
    """
    Asynchronous database writer that handles database operations in a separate thread.
    This prevents the application from blocking while writing to the database.
    """
    def __init__(self):
        self.queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        self._retry_delay = 1  # Initial retry delay in seconds
        self._max_retry_delay = 60  # Maximum retry delay in seconds
        self._max_retries = 5  # Maximum number of retries per operation
        
    def start(self):
        """Start the async database writer thread"""
        if self.running:
            return
            
        logger.info("Starting async database writer")
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
    def stop(self):
        """Stop the async database writer thread"""
        logger.info("Stopping async database writer")
        self.running = False
        # Add a None task to ensure the worker exits if blocked on queue.get()
        self.queue.put(None)
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
    def add_task(self, func, *args, **kwargs):
        """
        Add a database task to the queue
        
        Args:
            func: Function to call
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        """
        if not self.running:
            logger.warning("AsyncDatabaseWriter is not running, but task was added to queue")
            
        logger.info(f"Adding task to database queue: {func.__name__}")
        self.queue.put((func, args, kwargs))
        
    def _worker_loop(self):
        """Worker thread function to process database tasks"""
        logger.info("Database writer worker loop started")
        while self.running:
            try:
                task = self.queue.get(timeout=1)
                if task is None:
                    logger.info("Received shutdown signal in worker loop")
                    break
                
                func, args, kwargs = task
                logger.info(f"Executing database task: {func.__name__}")
                self._execute_task(func, args, kwargs)
                self.queue.task_done()
                logger.info(f"Database task completed: {func.__name__}")
                
            except queue.Empty:
                # No tasks available, continue waiting
                continue
                
            except Exception as e:
                logger.error(f"Error in database writer worker loop: {e}")
        
        logger.info("Database writer worker loop exited")
                
    def _execute_task(self, func, args, kwargs):
        """Execute a database task with retry logic"""
        retries = 0
        delay = self._retry_delay
        
        while retries < self._max_retries:
            try:
                # Create a new session for this task
                session = db_session()
                try:
                    # Execute the function
                    result = func(session, *args, **kwargs)
                    
                    # Commit changes
                    session.commit()
                    
                    # Reset retry delay on success
                    delay = self._retry_delay
                    return result
                    
                except Exception as e:
                    # Rollback the session on error
                    session.rollback()
                    raise e
                    
                finally:
                    # Close the session
                    session.close()
                    
            except Exception as e:
                retries += 1
                logger.error(f"Database operation failed (attempt {retries}/{self._max_retries}): {e}")
                
                if retries >= self._max_retries:
                    logger.error(f"Maximum retries exceeded for database operation")
                    return None
                    
                # Exponential backoff with jitter
                jitter = random.uniform(0.8, 1.2)
                sleep_time = min(delay * jitter, self._max_retry_delay)
                time.sleep(sleep_time)
                delay = min(delay * 2, self._max_retry_delay)

# Create the async database writer instance
async_db_writer = AsyncDatabaseWriter()

# Import random for jitter calculation in retry logic
import random

def init_db():
    """Initialize the database, creating tables if needed"""
    try:
        logger.info("Initializing database")
        
        # Import models so they are registered with SQLAlchemy
        import models
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Initialize settings if needed
        from settings import Settings
        settings = Settings()
        settings.initialize_defaults()
        
        # Register connection event listeners AFTER initialization 
        # to avoid transaction conflicts during table creation
        register_connection_events()
        
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def check_and_update_schema():
    """Check if the database schema needs to be updated and perform migrations if needed"""
    try:
        logger.info("Checking database schema for updates...")
        
        # Import models
        import models
        import sqlalchemy as sa
        from sqlalchemy import inspect
        
        # Get inspector
        inspector = inspect(engine)
        
        # Check if events table exists and has the required columns
        if 'events' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('events')]
            if 'has_screenshot' not in columns:
                # Add has_screenshot column
                logger.info("Adding has_screenshot column to events table")
                with engine.begin() as conn:
                    conn.execute(sa.text(
                        "ALTER TABLE events ADD COLUMN has_screenshot INTEGER DEFAULT 0"
                    ))
            
            if 'analysis_report_id' not in columns:
                # Add analysis_report_id column
                logger.info("Adding analysis_report_id column to events table")
                with engine.begin() as conn:
                    conn.execute(sa.text(
                        "ALTER TABLE events ADD COLUMN analysis_report_id INTEGER"
                    ))
        
        # Check if ai_analysis_reports table exists
        if 'ai_analysis_reports' not in inspector.get_table_names():
            # Create ai_analysis_reports table
            logger.info("Creating ai_analysis_reports table")
            models.AIAnalysisReport.__table__.create(engine)
            
        # Check if macro_executions table exists and has the required columns
        if 'macro_executions' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('macro_executions')]
            if 'execution_data' not in columns:
                # Add execution_data column
                logger.info("Adding execution_data column to macro_executions table")
                with engine.begin() as conn:
                    conn.execute(sa.text(
                        "ALTER TABLE macro_executions ADD COLUMN execution_data TEXT"
                    ))
        
        logger.info("Database schema update complete")
        return True
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False
