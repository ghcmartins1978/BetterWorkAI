import logging
import json
import time
import threading
from datetime import datetime
import pyautogui
import webbrowser
import re
import tkinter as tk
from tkinter import simpledialog

from database import db_session
from models import Macro, MacroStep, Suggestion, MacroVariable
import variable_detector

logger = logging.getLogger(__name__)

class AutomationExecutor:
    """
    Executes recorded macros and handles user notifications
    """
    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.notification_thread = None
        self.notification_check_interval = 60  # Check for notifications every minute
        self.currently_executing = False
        self.abort_requested = False
        
        # Configure pyautogui
        pyautogui.FAILSAFE = True  # Move mouse to upper-left corner to abort
        
    def start(self):
        """Start the automation executor service"""
        if self.running:
            return
            
        logger.info("Starting automation executor")
        self.running = True
        
        # Start notification thread
        self.notification_thread = threading.Thread(target=self._notification_loop, daemon=True)
        self.notification_thread.start()
        
    def stop(self):
        """Stop the automation executor service"""
        logger.info("Stopping automation executor")
        self.running = False
        
        # Abort any running execution
        self.abort_requested = True
        
    def execute_macro(self, macro_id):
        """
        Execute a recorded macro
        
        Args:
            macro_id: Database ID of the macro to execute
            
        Returns:
            True if execution completed successfully, False otherwise
        """
        if self.currently_executing:
            logger.warning("Another macro is currently executing")
            return False
            
        logger.info(f"Executing macro {macro_id}")
        self.currently_executing = True
        self.abort_requested = False
        result = False
        
        try:
            # Get macro from database
            macro = db_session.query(Macro).get(macro_id)
            
            if not macro or macro.status not in ['recorded', 'verified']:
                logger.error(f"Cannot execute macro {macro_id}: invalid status")
                return False
                
            # Update macro status
            macro.status = 'executing'
            macro.last_execution_time = datetime.now()
            db_session.commit()
            
            # Get steps
            steps = db_session.query(MacroStep).filter(
                MacroStep.macro_id == macro_id
            ).order_by(MacroStep.step_number).all()
            
            if not steps:
                logger.warning(f"Macro {macro_id} has no steps")
                macro.status = 'recorded'  # Reset status
                db_session.commit()
                return False
            
            # Get variables for this macro
            variable_values = self._get_variable_values(macro_id)
            logger.info(f"Using variables: {json.dumps(variable_values)}")
                
            # Show countdown if configured
            if self.settings.get_setting('show_execution_countdown'):
                self._show_countdown(3)
                
            # Execute each step
            for step in steps:
                if self.abort_requested:
                    logger.info("Macro execution aborted by user")
                    break
                    
                # Apply delay
                delay = max(0, step.delay_before)
                if delay > 0:
                    time.sleep(delay)
                    
                # Parse parameters
                params = json.loads(step.parameters)
                
                # Replace variables in parameters
                params_with_vars = self._replace_variables_in_params(params, variable_values)
                
                # Execute step based on type
                success = self._execute_step(step.action_type, params_with_vars)
                
                if not success:
                    logger.error(f"Failed to execute step {step.step_number} of macro {macro_id}")
                    break
                    
            # Update macro status
            if not self.abort_requested:
                macro.status = 'recorded'  # Reset to recorded state
                macro.execution_count = (macro.execution_count or 0) + 1
                db_session.commit()
                result = True
            else:
                macro.status = 'recorded'  # Reset to recorded state
                db_session.commit()
                result = False
                
        except Exception as e:
            logger.error(f"Error executing macro {macro_id}: {e}")
            
            # Update macro status on error
            try:
                macro = db_session.query(Macro).get(macro_id)
                macro.status = 'recorded'  # Reset to recorded state
                db_session.commit()
            except:
                pass
                
        finally:
            self.currently_executing = False
            self.abort_requested = False
            
        return result
    
    def notify_suggestion(self, suggestion_id):
        """
        Notify the user about a new automation suggestion
        
        Args:
            suggestion_id: Database ID of the suggestion
        """
        try:
            # Get suggestion from database
            suggestion = db_session.query(Suggestion).get(suggestion_id)
            
            if not suggestion or suggestion.status != 'pending':
                return
                
            # Update notification time
            suggestion.notification_time = datetime.now()
            db_session.commit()
            
            # Check if notifications are enabled
            if not self.settings.get_setting('enable_notifications'):
                return
                
            # Display notification using PyAutoGUI
            message = f"BettermanAI found a new automation: {suggestion.title}"
            self._show_notification(message, "Open settings page to review")
            
        except Exception as e:
            logger.error(f"Error notifying about suggestion {suggestion_id}: {e}")
    
    def _notification_loop(self):
        """Thread function to periodically check for pending notifications"""
        while self.running:
            try:
                # Check for pending suggestions
                if self.settings.get_setting('enable_notifications'):
                    pending_suggestions = db_session.query(Suggestion).filter(
                        Suggestion.status == 'pending',
                        Suggestion.notification_time.is_(None)
                    ).all()
                    
                    for suggestion in pending_suggestions:
                        self.notify_suggestion(suggestion.id)
                        time.sleep(5)  # Delay between notifications
                        
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                
            # Sleep until next check
            time.sleep(self.notification_check_interval)
            
    def _execute_step(self, action_type, params):
        """
        Execute a single macro step
        
        Args:
            action_type: Type of action (mouse_move, mouse_click, etc.)
            params: Dictionary of parameters for the action
            
        Returns:
            True if execution succeeded, False otherwise
        """
        try:
            if action_type == 'mouse_move':
                x = params.get('x', 0)
                y = params.get('y', 0)
                pyautogui.moveTo(x, y)
                
            elif action_type == 'mouse_click':
                x = params.get('x', 0)
                y = params.get('y', 0)
                button = params.get('button', 'left')
                pyautogui.click(x, y, button=button)
                
            elif action_type == 'mouse_scroll':
                x = params.get('x', 0)
                y = params.get('y', 0)
                dx = params.get('dx', 0)
                dy = params.get('dy', 0)
                clicks = int(dy * 10)  # Convert to scroll clicks
                pyautogui.scroll(clicks, x=x, y=y)
                
            elif action_type == 'key_press':
                key = params.get('key', '')
                if key:
                    # Handle special keys
                    if len(key) > 1 and not key.startswith('\''):
                        # It's a special key like 'shift' or 'ctrl'
                        pyautogui.press(key)
                    else:
                        # It's a regular character
                        pyautogui.press(key)
                        
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error executing step {action_type}: {e}")
            return False
            
    def _show_countdown(self, seconds):
        """Show a countdown before executing a macro"""
        try:
            # Get screen size
            width, height = pyautogui.size()
            center_x, center_y = width // 2, height // 2
            
            for i in range(seconds, 0, -1):
                # Draw a simple text overlay
                message = f"Executing macro in {i}..."
                
                # We can't directly draw, so we'll simulate a notification
                self._show_notification(message, "", timeout=0.8)
                time.sleep(0.2)
                
        except Exception as e:
            logger.error(f"Error displaying countdown: {e}")
            
    def _show_notification(self, title, message="", timeout=5):
        """
        Show a notification to the user
        
        This is a simple implementation using PyAutoGUI.
        In a full implementation, this would use system notifications.
        """
        try:
            # For cross-platform compatibility, we create a simple alert
            # This is not ideal but works for demonstration
            # In a real implementation, we'd use platform-specific notification APIs
            
            # Due to limitations of the current implementation, we'll just
            # create a text file with the notification for now
            notification_path = "notification.txt"
            with open(notification_path, 'w') as f:
                f.write(f"{title}\n\n{message}")
                
            # In a real implementation, we'd use:
            # - On Windows: win32api or Windows Toast Notifications
            # - On macOS: AppleScript or NSUserNotification
            # - On Linux: notify-send or libnotify
            
            logger.info(f"Notification: {title} - {message}")
            
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
            
    def _get_variable_values(self, macro_id):
        """
        Get the current values of all variables for a macro.
        
        Args:
            macro_id: ID of the macro
            
        Returns:
            Dictionary mapping variable names to their values
        """
        try:
            # First, make sure all variables are registered
            variable_detector.register_variables_for_macro(macro_id)
            
            # Get all variables for this macro
            variables = db_session.query(MacroVariable).filter_by(macro_id=macro_id).all()
            
            # Create a dictionary of variable values
            variable_values = {}
            missing_required_vars = []
            
            for var in variables:
                # Use current value if available, otherwise default value
                value = var.current_value or var.default_value or ""
                
                # Check if this is a required variable with no value
                if var.is_required and not value:
                    missing_required_vars.append(var.name)
                
                # Convert value to appropriate type
                if var.variable_type == 'number':
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except (ValueError, TypeError):
                        # Keep as string if conversion fails
                        pass
                elif var.variable_type == 'boolean':
                    value = value.lower() in ('true', 'yes', '1', 'y')
                
                variable_values[var.name] = value
            
            # If there are required variables with no values, prompt the user
            if missing_required_vars and self.settings.get_setting('prompt_for_required_variables', default=True):
                self._prompt_for_variables(macro_id, missing_required_vars)
                # Recursively call to get updated values
                return self._get_variable_values(macro_id)
                
            return variable_values
            
        except Exception as e:
            logger.error(f"Error getting variable values for macro {macro_id}: {e}")
            return {}
            
    def _prompt_for_variables(self, macro_id, variable_names):
        """
        Prompt the user to enter values for required variables.
        
        Args:
            macro_id: ID of the macro
            variable_names: List of variable names to prompt for
        """
        logger.info(f"Prompting for variables: {variable_names}")
        
        try:
            # Get the macro name for the dialog
            macro = db_session.query(Macro).get(macro_id)
            if not macro:
                return
                
            macro_name = macro.name
            
            # Get the variables
            variables = db_session.query(MacroVariable).filter(
                MacroVariable.macro_id == macro_id,
                MacroVariable.name.in_(variable_names)
            ).all()
            
            if not variables:
                return
                
            # Show a dialog for each variable
            for var in variables:
                description = var.description or f"Enter value for {var.name}"
                prompt_text = f"Macro '{macro_name}' requires a value for '{var.name}':\n{description}"
                
                # Use PyAutoGUI prompt or OS-specific dialog
                value = pyautogui.prompt(
                    text=prompt_text,
                    title="Variable Required",
                    default=var.default_value or ""
                )
                
                # Update the variable if a value was provided
                if value is not None:  # None means the user clicked Cancel
                    var.current_value = value
                    db_session.commit()
                else:
                    # User cancelled, abort execution
                    self.abort_requested = True
                    logger.info("Variable prompt cancelled by user, aborting execution")
                    break
                    
        except Exception as e:
            logger.error(f"Error prompting for variables: {e}")
            
    def _replace_variables_in_params(self, params, variable_values):
        """
        Replace variable placeholders in parameters with their values.
        
        Args:
            params: Dictionary of parameters
            variable_values: Dictionary mapping variable names to their values
            
        Returns:
            Dictionary with variables replaced by their values
        """
        result = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Replace all variables in the string
                new_value = value
                
                # First check for complex expressions with formatting like {{variable:format}}
                formatted_matches = re.finditer(r'{{(\w+):(.*?)}}', new_value)
                for match in formatted_matches:
                    full_placeholder = match.group(0)
                    var_name = match.group(1)
                    format_spec = match.group(2)
                    
                    if var_name in variable_values:
                        var_value = variable_values[var_name]
                        
                        try:
                            # Handle different format types
                            if format_spec == 'upper':
                                replacement = str(var_value).upper()
                            elif format_spec == 'lower':
                                replacement = str(var_value).lower()
                            elif format_spec == 'title':
                                replacement = str(var_value).title()
                            elif format_spec.startswith('pad'):
                                # Padding format: pad:10:0 (pad to 10 characters with 0)
                                parts = format_spec.split(':')
                                if len(parts) >= 3:
                                    width = int(parts[1])
                                    char = parts[2]
                                    replacement = str(var_value).rjust(width, char)
                                else:
                                    replacement = str(var_value)
                            elif format_spec.startswith('calc'):
                                # Calculate with expression: calc:+10 or calc:*2
                                parts = format_spec.split(':')
                                if len(parts) >= 2:
                                    operator = parts[1][0]  # First character is the operator
                                    operand = float(parts[1][1:])
                                    
                                    # Convert var_value to number if needed
                                    if isinstance(var_value, str):
                                        if var_value.isdigit():
                                            var_value = int(var_value)
                                        elif self._is_float(var_value):
                                            var_value = float(var_value)
                                    
                                    if operator == '+':
                                        replacement = str(var_value + operand)
                                    elif operator == '-':
                                        replacement = str(var_value - operand)
                                    elif operator == '*':
                                        replacement = str(var_value * operand)
                                    elif operator == '/':
                                        replacement = str(var_value / operand)
                                    else:
                                        replacement = str(var_value)
                                else:
                                    replacement = str(var_value)
                            else:
                                # Try to use as Python format specifier
                                try:
                                    replacement = format(var_value, format_spec)
                                except (ValueError, TypeError):
                                    replacement = str(var_value)
                        except Exception as e:
                            logger.error(f"Error formatting variable {var_name}: {e}")
                            replacement = str(var_value)
                            
                        logger.info(f"Replacing {full_placeholder} with {replacement}")
                        new_value = new_value.replace(full_placeholder, replacement)
                
                # Now handle simple variable replacements {{variable}}
                for var_name, var_value in variable_values.items():
                    placeholder = f"{{{{{var_name}}}}}"
                    if placeholder in new_value:
                        logger.info(f"Replacing {placeholder} with {var_value}")
                        new_value = new_value.replace(placeholder, str(var_value))
                
                # Handle conditional expressions {{if:variable:then:else}}
                conditional_matches = re.finditer(r'{{if:(\w+):([^:]*):([^}]*)}}', new_value)
                for match in conditional_matches:
                    full_placeholder = match.group(0)
                    var_name = match.group(1)
                    then_value = match.group(2)
                    else_value = match.group(3)
                    
                    if var_name in variable_values:
                        var_value = variable_values[var_name]
                        # Convert to boolean for condition check
                        if isinstance(var_value, str):
                            var_value = var_value.lower() in ('true', 'yes', '1', 'y', 't')
                        elif isinstance(var_value, (int, float)):
                            var_value = var_value != 0
                            
                        replacement = then_value if var_value else else_value
                        logger.info(f"Conditional {full_placeholder} evaluates to {replacement}")
                        new_value = new_value.replace(full_placeholder, replacement)
                
                # Try to convert to number if it looks like one
                if new_value.isdigit():
                    new_value = int(new_value)
                elif self._is_float(new_value):
                    new_value = float(new_value)
                    
                result[key] = new_value
            else:
                # Non-string values don't contain variables
                result[key] = value
        
        return result
        
    def _is_float(self, value):
        """Check if a string can be converted to a float."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
