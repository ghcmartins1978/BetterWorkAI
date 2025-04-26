import logging
import json
from datetime import datetime
from database import db_session
from models import Setting

logger = logging.getLogger(__name__)

class Settings:
    """
    Manages application settings
    """
    def __init__(self):
        self.cache = {}
        self._load_settings()
        
    def _load_settings(self):
        """Load settings from database into cache"""
        try:
            settings = db_session.query(Setting).all()
            self.cache = {}
            
            for setting in settings:
                self.cache[setting.name] = self._convert_value(setting.value, setting.value_type)
                
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            
    def get_setting(self, name, default=None):
        """
        Get a setting value by name
        
        Args:
            name: Setting name
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value (converted to the appropriate type) or default
        """
        # Check cache first
        if name in self.cache:
            return self.cache[name]
            
        # Try to load from database
        try:
            setting = db_session.query(Setting).get(name)
            
            if setting:
                value = self._convert_value(setting.value, setting.value_type)
                self.cache[name] = value
                return value
                
        except Exception as e:
            logger.error(f"Error getting setting {name}: {e}")
            
        return default
        
    def set_setting(self, name, value):
        """
        Set a setting value
        
        Args:
            name: Setting name
            value: Setting value (will be converted to string for storage)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine value type
            value_type = self._get_value_type(value)
            value_str = self._value_to_string(value)
            
            # Update cache
            self.cache[name] = value
            
            # Update database
            setting = db_session.query(Setting).get(name)
            
            if setting:
                # Update existing setting
                setting.value = value_str
                setting.value_type = value_type
            else:
                # Create new setting
                setting = Setting(
                    name=name,
                    value=value_str,
                    value_type=value_type,
                    description=''
                )
                db_session.add(setting)
                
            db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error setting {name}={value}: {e}")
            db_session.rollback()
            return False
            
    def _convert_value(self, value_str, value_type):
        """Convert a string value to the appropriate type"""
        if value_str is None:
            return None
            
        try:
            if value_type == 'boolean':
                return value_str.lower() == 'true'
            elif value_type == 'number':
                if '.' in value_str:
                    return float(value_str)
                else:
                    return int(value_str)
            elif value_type == 'json':
                return json.loads(value_str)
            else:
                return value_str
        except Exception as e:
            logger.error(f"Error converting setting value {value_str} to {value_type}: {e}")
            return value_str
            
    def _get_value_type(self, value):
        """Determine the type of a value"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, (int, float)):
            return 'number'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'
            
    def _value_to_string(self, value):
        """Convert a value to a string for storage"""
        if value is None:
            return None
            
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        else:
            return str(value)
            
    def initialize_defaults(self):
        """Initialize default settings if not already set"""
        defaults = {
            'monitoring_enabled': False,
            'track_mouse_moves': True,
            'track_mouse_clicks': True,
            'track_mouse_scrolls': True,
            'track_keyboard': True,
            'track_windows': True,
            'enable_notifications': True,
            'show_execution_countdown': True,
            'monitoring_start_time': None,
            'privacy_level': 'medium',  # low, medium, high
            'log_retention_days': 7
        }
        
        # Set default settings if they don't exist
        for name, value in defaults.items():
            if self.get_setting(name) is None:
                self.set_setting(name, value)
