import logging
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

logger = logging.getLogger(__name__)

class AIAnalysisReport(Base):
    """
    Represents an AI analysis report of a screenshot, pattern, or macro
    """
    __tablename__ = 'ai_analysis_reports'
    
    id = Column(Integer, primary_key=True)
    report_type = Column(String(20), nullable=False)  # screenshot, pattern, macro
    source_id = Column(Integer)  # ID of the related object (event, pattern, macro)
    source_path = Column(String(255))  # File path if applicable (for screenshots)
    timestamp = Column(DateTime, default=datetime.now)
    analysis_data = Column(Text)  # JSON string of AI analysis results
    summary = Column(Text)  # Human-readable summary
    insights = Column(Text)  # Key insights
    automation_potential = Column(Float, default=0.0)  # Score from 0-1
    application_context = Column(String(255))  # Application or context that was analyzed

class Event(Base):
    """
    Represents a user input event (mouse, keyboard, window)
    """
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    type = Column(String(20), nullable=False)  # mouse_move, key_press, etc.
    data = Column(Text, nullable=False)  # JSON string of event data
    timestamp = Column(DateTime, default=datetime.now)
    has_screenshot = Column(Integer, default=0)  # Whether this event has an associated screenshot
    analysis_report_id = Column(Integer, ForeignKey('ai_analysis_reports.id'), nullable=True)

class EventSequence(Base):
    """
    Represents a sequence of related events
    """
    __tablename__ = 'event_sequences'
    
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    event_count = Column(Integer, default=0)
    meta_data = Column(Text)  # JSON string of metadata (windows, activities, etc.)
    data = Column(Text)  # JSON string of events in the sequence

class Pattern(Base):
    """
    Represents a detected pattern of repetitive behavior
    """
    __tablename__ = 'patterns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    sequence_ids = Column(Text)  # JSON array of sequence IDs
    detection_time = Column(DateTime, default=datetime.now)
    last_match_time = Column(DateTime)
    score = Column(Float, default=0.0)  # Pattern confidence score
    status = Column(String(20), default='detected')  # detected, evaluating, approved, rejected, error
    evaluation_notes = Column(Text)
    
    # Relationship to suggestions
    suggestions = relationship('Suggestion', back_populates='pattern')

class Suggestion(Base):
    """
    Represents an automation suggestion based on a pattern
    """
    __tablename__ = 'suggestions'
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(Integer, ForeignKey('patterns.id'))
    title = Column(String(100), nullable=False)
    description = Column(Text)
    steps = Column(Text)  # JSON array of steps
    creation_time = Column(DateTime, default=datetime.now)
    notification_time = Column(DateTime)
    action_time = Column(DateTime)
    status = Column(String(20), default='pending')  # pending, accepted, rejected
    macro_id = Column(Integer, ForeignKey('macros.id'), nullable=True)
    
    # Relationships
    pattern = relationship('Pattern', back_populates='suggestions')
    macro = relationship('Macro', back_populates='suggestion')

class Macro(Base):
    """
    Represents a recorded macro for automation
    """
    __tablename__ = 'macros'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    creation_time = Column(DateTime, default=datetime.now)
    last_execution_time = Column(DateTime)
    execution_count = Column(Integer, default=0)
    step_count = Column(Integer, default=0)
    status = Column(String(20), default='created')  # created, recording, recorded, executing, verified, empty
    
    # Relationships
    steps = relationship('MacroStep', back_populates='macro', cascade='all, delete-orphan')
    suggestion = relationship('Suggestion', back_populates='macro')

class MacroStep(Base):
    """
    Represents a single step in a macro
    """
    __tablename__ = 'macro_steps'
    
    id = Column(Integer, primary_key=True)
    macro_id = Column(Integer, ForeignKey('macros.id'), nullable=False)
    step_number = Column(Integer, nullable=False)
    action_type = Column(String(20), nullable=False)  # mouse_move, key_press, etc.
    parameters = Column(Text, nullable=False)  # JSON string of parameters
    delay_before = Column(Float, default=0.0)  # Delay in seconds before this step
    
    # Relationship to macro
    macro = relationship('Macro', back_populates='steps')

class Setting(Base):
    """
    Represents a system setting
    """
    __tablename__ = 'settings'
    
    name = Column(String(50), primary_key=True)
    value = Column(Text)
    value_type = Column(String(10))  # string, boolean, number, json
    description = Column(Text)
