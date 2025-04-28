import logging
import json
import time
import threading
import os
from datetime import datetime, timedelta
import pyautogui
import webbrowser
import re
import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageChops
import numpy as np
import io

from database import db_session
from models import Macro, MacroStep, Suggestion, MacroVariable, MacroExecution, Metric
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
        before_img = None
        after_img = None
        screenshot_dir = "logs/screenshots"
        
        # Ensure screenshot directory exists
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Create a new execution record
        execution = MacroExecution(
            macro_id=macro_id,
            start_time=datetime.now(),
            status='running'
        )
        db_session.add(execution)
        db_session.commit()
        execution_id = execution.id
        
        start_time = time.time()
        
        try:
            # Get macro from database
            macro = db_session.query(Macro).get(macro_id)
            
            if not macro or macro.status not in ['recorded', 'verified']:
                logger.error(f"Cannot execute macro {macro_id}: invalid status")
                self._update_execution_record(execution_id, 'failed', error_message="Invalid macro status")
                return False
                
            # Update macro status
            macro.status = 'executing'
            macro.last_execution_time = datetime.now()
            
            # Update execution record with original duration
            if macro.original_sequence_duration:
                execution.original_sequence_duration = macro.original_sequence_duration
            db_session.commit()
            
            # Get steps
            steps = db_session.query(MacroStep).filter(
                MacroStep.macro_id == macro_id
            ).order_by(MacroStep.step_number).all()
            
            if not steps:
                logger.warning(f"Macro {macro_id} has no steps")
                macro.status = 'recorded'  # Reset status
                self._update_execution_record(execution_id, 'failed', error_message="No steps to execute")
                db_session.commit()
                return False
            
            # Get variables for this macro
            variable_values = self._get_variable_values(macro_id)
            logger.info(f"Using variables: {json.dumps(variable_values)}")
                
            # Show countdown if configured
            if self.settings.get_setting('show_execution_countdown'):
                self._show_countdown(3)
            
            # Take screenshot before execution (after countdown)
            before_img = pyautogui.screenshot()
            before_img_path = f"{screenshot_dir}/macro_{macro_id}_before_{int(time.time())}.png"
            before_img.save(before_img_path)
            logger.info(f"Saved before-execution screenshot to {before_img_path}")
                
            # Execute each step
            all_steps_successful = True
            for step in steps:
                if self.abort_requested:
                    logger.info("Macro execution aborted by user")
                    all_steps_successful = False
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
                    all_steps_successful = False
                    break
            
            # Take screenshot after execution
            after_img = pyautogui.screenshot()
            after_img_path = f"{screenshot_dir}/macro_{macro_id}_after_{int(time.time())}.png"
            after_img.save(after_img_path)
            logger.info(f"Saved after-execution screenshot to {after_img_path}")
            
            # Calculate execution time and time saved
            end_time = time.time()
            execution_duration = end_time - start_time
            
            # Compare before and after screenshots if both exist
            if before_img and after_img:
                logger.info("Comparing before and after screenshots")
                diff_percentage, diff_img = self._compare_screenshots(before_img, after_img)
                
                # Initialize diff_img_path
                diff_img_path = None
                
                # Save the diff image for reference
                if diff_img:
                    diff_img_path = f"{screenshot_dir}/macro_{macro_id}_diff_{int(time.time())}.png"
                    diff_img.save(diff_img_path)
                    logger.info(f"Saved screenshot diff to {diff_img_path}")
                
                # Always store screenshot and diff data in execution_data
                execution_data = {
                    "screen_change_percentage": diff_percentage,
                    "before_screenshot": before_img_path,
                    "after_screenshot": after_img_path,
                    "diff_screenshot": diff_img_path
                }
                
                # If less than 3% of the screen changed, add a warning
                if diff_percentage < 3.0:
                    warning_message = f"Warning: Screen changed only {diff_percentage:.2f}% after execution. Automation may not have had the expected effect."
                    logger.warning(warning_message)
                    
                    # Add warning to execution data
                    execution_data["warning"] = warning_message
                    
                    # Show a notification about the warning
                    self._show_notification(
                        "Automation Warning", 
                        f"Macro '{macro.name}' completed, but screen changed only {diff_percentage:.2f}%"
                    )
                
                # Store the execution data
                execution.execution_data = json.dumps(execution_data)
                db_session.commit()
            
            # Update macro status and metrics
            if all_steps_successful and not self.abort_requested:
                macro.status = 'recorded'  # Reset to recorded state
                macro.execution_count = (macro.execution_count or 0) + 1
                macro.success_count = (macro.success_count or 0) + 1
                
                # Calculate time saved - if original duration is not set, use a default estimate
                # based on the number of steps (e.g., 5 seconds per step)
                if macro.original_sequence_duration is None:
                    estimated_duration = len(steps) * 5.0  # 5 seconds per step
                    macro.original_sequence_duration = estimated_duration
                    
                time_saved = macro.original_sequence_duration - execution_duration
                if time_saved < 0:
                    time_saved = 0
                    
                macro.total_time_saved = (macro.total_time_saved or 0.0) + time_saved
                
                # Update metrics
                self._update_time_saved_metrics(time_saved)
                
                # Update execution record
                self._update_execution_record(
                    execution_id, 
                    'success',
                    execution_duration=execution_duration,
                    time_saved=time_saved
                )
                
                result = True
            else:
                macro.status = 'recorded'  # Reset to recorded state
                macro.failure_count = (macro.failure_count or 0) + 1
                
                # Update execution record
                self._update_execution_record(
                    execution_id, 
                    'failed',
                    execution_duration=execution_duration,
                    error_message="Execution aborted or steps failed"
                )
                
                result = False
                
            db_session.commit()
            
            # Check if we need to trigger relearn prompt (Ticket A9)
            self._check_relearn_criteria(macro_id)
                
        except Exception as e:
            logger.error(f"Error executing macro {macro_id}: {e}")
            
            # Update macro status on error
            try:
                macro = db_session.query(Macro).get(macro_id)
                macro.status = 'recorded'  # Reset to recorded state
                macro.failure_count = (macro.failure_count or 0) + 1
                db_session.commit()
                
                # Update execution record
                end_time = time.time()
                execution_duration = end_time - start_time
                self._update_execution_record(
                    execution_id, 
                    'failed',
                    execution_duration=execution_duration,
                    error_message=str(e)
                )
            except Exception as inner_e:
                logger.error(f"Error updating macro status: {inner_e}")
                
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
                self._show_notification(message, "", timeout=1)
                time.sleep(0.2)
                
        except Exception as e:
            logger.error(f"Error displaying countdown: {e}")
            
    def _show_notification(self, title, message="", timeout=5):
        """
        Show a notification to the user
        
        This is a simple implementation using PyAutoGUI.
        In a full implementation, this would use system notifications.
        
        Args:
            title: Title of the notification
            message: Body message of the notification
            timeout: Timeout in seconds (integer)
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
        Uses a web-based form instead of a dialog for better user experience.
        
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
                
            # Get the variables
            variables = db_session.query(MacroVariable).filter(
                MacroVariable.macro_id == macro_id,
                MacroVariable.name.in_(variable_names)
            ).all()
            
            if not variables:
                return
                
            # Check if web-based prompting is enabled
            use_web_prompt = self.settings.get_setting('prompt_required_variables', default=True)
            prompt_timeout = int(self.settings.get_setting('variable_prompt_timeout', default=30))
                
            if use_web_prompt:
                # Get the variable data for the template
                variable_data = []
                for var in variables:
                    variable_data.append({
                        'id': var.id,
                        'name': var.name,
                        'description': var.description or f"Variable for {var.name}",
                        'type': var.variable_type or 'string',
                        'default_value': var.default_value or '',
                        'current_value': var.current_value or var.default_value or '',
                        'is_required': var.is_required == 1
                    })
                
                # Open a web page with a form for all variables
                # We'll store the variable data in a session or temporary file
                import json
                import os
                import webbrowser
                from tempfile import gettempdir
                import time
                
                # Create a temporary file to store the variable data
                temp_dir = gettempdir()
                temp_file = os.path.join(temp_dir, f"betterman_vars_{macro_id}.json")
                
                with open(temp_file, 'w') as f:
                    json.dump({
                        'macro_id': macro_id,
                        'macro_name': macro.name,
                        'variables': variable_data,
                        'timeout': prompt_timeout
                    }, f)
                
                # Open the variable prompt in the default browser
                # In a real implementation, we would have a proper endpoint for this
                # For now, we'll simulate with a basic HTML form
                import urllib.parse
                query_params = urllib.parse.urlencode({
                    'macro_id': macro_id,
                    'temp_file': temp_file,
                    't': int(time.time())  # Cache buster
                })
                webbrowser.open(f"http://localhost:5000/variable_prompt?{query_params}")
                
                # Wait for user input with timeout
                start_time = time.time()
                while True:
                    # Check if the temporary file has been updated with user input
                    if os.path.exists(temp_file + '.response'):
                        # Load the response
                        try:
                            with open(temp_file + '.response', 'r') as f:
                                response = json.load(f)
                                
                            # Update the variables with the user's values
                            for var_id, value in response.items():
                                # Find the variable by ID
                                var = next((v for v in variables if str(v.id) == var_id), None)
                                if var:
                                    var.current_value = value
                            
                            # Commit the changes
                            db_session.commit()
                            
                            # Clean up
                            try:
                                os.remove(temp_file + '.response')
                            except:
                                pass
                                
                            break
                        except Exception as e:
                            logger.error(f"Error loading variable response: {e}")
                            break
                    
                    # Check if we've timed out
                    if time.time() - start_time > prompt_timeout:
                        logger.info(f"Variable prompt timed out after {prompt_timeout} seconds")
                        break
                        
                    # Sleep a bit to avoid hammering the CPU
                    time.sleep(0.5)
                
                # Clean up the temporary file
                try:
                    os.remove(temp_file)
                except:
                    pass
            else:
                # Fall back to the old tkinter dialog for each variable
                for var in variables:
                    description = var.description or f"Enter value for {var.name}"
                    prompt_text = f"Macro '{macro.name}' requires a value for '{var.name}':\n{description}"
                    
                    # Use tkinter dialog for better cross-platform compatibility
                    root = tk.Tk()
                    root.withdraw()  # Hide the main window
                    
                    # Make sure it appears on top
                    root.attributes("-topmost", True)
                    
                    # Show the dialog
                    value = simpledialog.askstring(
                        title="Variable Required",
                        prompt=prompt_text,
                        initialvalue=var.default_value or ""
                    )
                    
                    # Clean up
                    root.destroy()
                    
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
        Uses the enhanced variable_detector module for more advanced variable handling.
        
        Args:
            params: Dictionary of parameters
            variable_values: Dictionary mapping variable names to their values
            
        Returns:
            Dictionary with variables replaced by their values
        """
        # Get variable handling settings
        allow_formatting = self.settings.get_setting('allow_variable_formatting', 'true') == 'true'
        allow_conditionals = self.settings.get_setting('allow_conditional_variables', 'true') == 'true'
        
        # Pass settings to the variable detector
        settings = {
            'allow_variable_formatting': allow_formatting,
            'allow_conditional_variables': allow_conditionals
        }
        
        # Use the enhanced variable_detector module
        try:
            result = variable_detector.replace_variables_in_params(params, variable_values, settings)
            return result
        except Exception as e:
            logger.error(f"Error replacing variables: {e}")
            # Fall back to the basic replacement method below
        
        # Basic replacement fallback
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
            
    def _compare_screenshots(self, before_img, after_img):
        """
        Compare two screenshots and calculate the percentage of difference.
        
        Args:
            before_img: PIL Image of the screen before macro execution
            after_img: PIL Image of the screen after macro execution
            
        Returns:
            Tuple containing (difference_percentage, diff_image)
        """
        try:
            # Ensure images are the same size
            if before_img.size != after_img.size:
                logger.warning("Screenshot sizes don't match, resizing for comparison")
                after_img = after_img.resize(before_img.size)
                
            # Convert images to same mode if needed
            if before_img.mode != after_img.mode:
                after_img = after_img.convert(before_img.mode)
                
            # Calculate difference image
            diff_img = ImageChops.difference(before_img, after_img)
            
            # Convert to numpy array for calculations
            diff_array = np.array(diff_img)
            
            # Calculate percentage of non-zero (changed) pixels
            total_pixels = diff_array.size / 3  # Divide by 3 for RGB channels
            changed_pixels = np.count_nonzero(diff_array) / 3
            
            diff_percentage = (changed_pixels / total_pixels) * 100
            
            logger.info(f"Screenshot comparison: {diff_percentage:.2f}% pixels changed")
            
            return diff_percentage, diff_img
            
        except Exception as e:
            logger.error(f"Error comparing screenshots: {e}")
            return 100.0, None  # Return 100% difference on error to avoid false positives
            
    def _update_execution_record(self, execution_id, status, execution_duration=None, time_saved=None, error_message=None):
        """
        Update a macro execution record with results
        
        Args:
            execution_id: ID of the execution record
            status: New status (success, failed, timeout)
            execution_duration: Duration of execution in seconds
            time_saved: Time saved in seconds (original_duration - execution_duration)
            error_message: Error message if any
        """
        try:
            execution = db_session.query(MacroExecution).get(execution_id)
            if not execution:
                logger.error(f"Execution record {execution_id} not found")
                return
                
            execution.status = status
            execution.end_time = datetime.now()
            
            if execution_duration is not None:
                execution.execution_duration = execution_duration
                
            if time_saved is not None:
                execution.time_saved = time_saved
                
            if error_message:
                execution.error_message = error_message
                
            db_session.commit()
            logger.info(f"Updated execution record {execution_id} with status {status}")
            
        except Exception as e:
            logger.error(f"Error updating execution record: {e}")
            
    def _update_time_saved_metrics(self, time_saved_seconds):
        """
        Update metrics with time saved
        
        Args:
            time_saved_seconds: Time saved in seconds
        """
        try:
            # Convert seconds to hours
            hours_saved = time_saved_seconds / 3600.0
            
            # Get current hours_saved_total metric
            hours_saved_metric = db_session.query(Metric).filter(Metric.name == 'hours_saved_total').first()
            
            if not hours_saved_metric:
                # Create it if it doesn't exist
                hours_saved_metric = Metric(
                    name='hours_saved_total',
                    value=hours_saved,
                    notes='Total hours saved by all macro executions'
                )
                db_session.add(hours_saved_metric)
            else:
                # Update existing metric
                hours_saved_metric.value = hours_saved_metric.value + hours_saved
                hours_saved_metric.timestamp = datetime.now()
                
            db_session.commit()
            logger.info(f"Updated hours_saved_total metric: {hours_saved_metric.value} hours")
            
        except Exception as e:
            logger.error(f"Error updating time saved metrics: {e}")
            
    def _check_relearn_criteria(self, macro_id):
        """
        Check if a macro needs relearning based on failure rate
        
        Args:
            macro_id: ID of the macro to check
        """
        try:
            macro = db_session.query(Macro).get(macro_id)
            if not macro:
                return
                
            # Only check if the macro has been executed multiple times
            if macro.execution_count < 10:
                return
                
            # Calculate failure rate
            failure_rate = macro.failure_count / macro.execution_count
            
            # Check if failure rate exceeds threshold (10%)
            if failure_rate > 0.1:
                
                # Check if user has already been prompted recently
                if macro.relearn_prompt_time:
                    # Don't prompt again if user was prompted recently (within 7 days)
                    time_since_prompt = datetime.now() - macro.relearn_prompt_time
                    if time_since_prompt.days < 7:
                        return
                
                # User hasn't been prompted recently or has never been prompted
                # and hasn't selected 'never' as relearn_status
                if macro.relearn_status != 'never':
                    self._prompt_relearn(macro_id, failure_rate)
                    
        except Exception as e:
            logger.error(f"Error checking relearn criteria: {e}")
            
    def _prompt_relearn(self, macro_id, failure_rate):
        """
        Prompt user to relearn a macro due to high failure rate
        
        Args:
            macro_id: ID of the macro 
            failure_rate: Current failure rate (0.0-1.0)
        """
        try:
            macro = db_session.query(Macro).get(macro_id)
            if not macro:
                return
                
            # Update the prompt time
            macro.relearn_prompt_time = datetime.now()
            db_session.commit()
            
            # Format the failure percentage
            failure_percent = int(failure_rate * 100)
            
            # Create a notification with a link to a relearn prompt page
            title = f"Automation '{macro.name}' is failing {failure_percent}% of the time"
            message = "This macro needs to be re-recorded for better reliability."
            
            # We'll show a notification that directs to a dedicated page with options
            notification_message = f"{message} Click to view options."
            
            # Create a suggestion entry for the relearn prompt
            suggestion = Suggestion(
                pattern_id=None,  # Not based on a pattern
                title=title,
                description=f"Macro ID {macro_id} has a failure rate of {failure_percent}%. Consider re-recording it for better reliability.",
                status='relearn_prompt',  # Special status for relearn prompts
                macro_id=macro_id
            )
            db_session.add(suggestion)
            db_session.commit()
            
            # In a production environment, we would:
            # 1. Add a "relearn_suggestions" table to track these specifically
            # 2. Make the notification clickable to open the web UI with options
            
            # Add suggestion ID to the notification so it can be tracked
            self._show_relearn_notification(
                title, 
                notification_message,
                suggestion.id,
                macro_id
            )
            logger.info(f"User prompted to relearn macro {macro_id} (failure rate: {failure_percent}%)")
            
        except Exception as e:
            logger.error(f"Error prompting relearn: {e}")
