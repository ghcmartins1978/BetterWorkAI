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
