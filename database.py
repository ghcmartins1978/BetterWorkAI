import os
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(database_url)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

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
        
        logger.info("Database schema update complete")
        return True
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        return False
