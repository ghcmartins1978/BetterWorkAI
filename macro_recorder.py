import logging
import json
import time
import threading
from datetime import datetime
import os
import pyautogui
from pynput import mouse, keyboard

from database import db_session
from models import Macro, MacroStep

logger = logging.getLogger(__name__)

class MacroRecorder:
    """
    Records user actions for automation playback
    """
    def __init__(self, settings):
        self.settings = settings
        self.recording = False
        self.recorded_steps = []
        self.start_time = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.current_window = None
        self.last_event_time = None
        self.macro_id = None
        
        # Configure pyautogui
        pyautogui.FAILSAFE = True  # Move mouse to upper-left corner to abort
        pyautogui.PAUSE = 0.1  # Add small delays between actions
        
    def start_recording(self, macro_name=None, description=None):
        """Start recording a new macro"""
        if self.recording:
            logger.warning("Already recording a macro")
            return False
            
        logger.info("Starting macro recording")
        self.recording = True
        self.recorded_steps = []
        self.start_time = datetime.now()
        self.last_event_time = time.time()
        
        # Create macro in database
        try:
            from models import Macro
            macro = Macro(
                name=macro_name or f"Macro {self.start_time.strftime('%Y%m%d-%H%M%S')}",
                description=description or "Recorded macro",
                creation_time=self.start_time,
                status="recording"
            )
            db_session.add(macro)
            db_session.commit()
            self.macro_id = macro.id
        except Exception as e:
            logger.error(f"Error creating macro record: {e}")
            self.macro_id = None
            
        # Start mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()
        
        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()
        
        return True
        
    def stop_recording(self):
        """Stop recording and save the macro"""
        if not self.recording:
            logger.warning("Not currently recording a macro")
            return None
            
        logger.info("Stopping macro recording")
        self.recording = False
        
        # Stop listeners
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
            
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
            
        # Process recorded steps
        if not self.recorded_steps:
            logger.warning("No steps were recorded in the macro")
            
            # Update macro status
            if self.macro_id:
                try:
                    macro = db_session.query(Macro).get(self.macro_id)
                    if macro:
                        macro.status = "empty"
                        db_session.commit()
                except Exception as e:
                    logger.error(f"Error updating macro status: {e}")
                    
            return None
            
        # Save steps to database
        if self.macro_id:
            try:
                # Update macro status
                macro = db_session.query(Macro).get(self.macro_id)
                if macro:
                    macro.status = "recorded"
                    macro.step_count = len(self.recorded_steps)
                    db_session.commit()
                    
                    # Save steps
                    for i, step in enumerate(self.recorded_steps):
                        macro_step = MacroStep(
                            macro_id=self.macro_id,
                            step_number=i,
                            action_type=step['type'],
                            parameters=json.dumps(step['params']),
                            delay_before=step.get('delay', 0)
                        )
                        db_session.add(macro_step)
                        
                    db_session.commit()
                    logger.info(f"Saved macro with {len(self.recorded_steps)} steps")
                    
                    return self.macro_id
            except Exception as e:
                logger.error(f"Error saving macro steps: {e}")
                
        return None
        
    def _on_mouse_move(self, x, y):
        """Record mouse movement"""
        if not self.recording:
            return
            
        # Skip recording every mouse move to avoid too many events
        # Instead, record mouse positions periodically
        now = time.time()
        if hasattr(self, '_last_move_time') and now - self._last_move_time < 0.3:
            return
            
        self._last_move_time = now
        
        # Calculate delay since last event
        delay = now - self.last_event_time if self.last_event_time else 0
        self.last_event_time = now
        
        # Record the mouse position
        self.recorded_steps.append({
            'type': 'mouse_move',
            'params': {'x': x, 'y': y},
            'delay': delay
        })
        
    def _on_mouse_click(self, x, y, button, pressed):
        """Record mouse click"""
        if not self.recording:
            return
            
        # Only record press events
        if not pressed:
            return
            
        # Calculate delay since last event
        now = time.time()
        delay = now - self.last_event_time if self.last_event_time else 0
        self.last_event_time = now
        
        # Record the click
        button_str = 'left'
        if button == mouse.Button.right:
            button_str = 'right'
        elif button == mouse.Button.middle:
            button_str = 'middle'
            
        self.recorded_steps.append({
            'type': 'mouse_click',
            'params': {'x': x, 'y': y, 'button': button_str},
            'delay': delay
        })
        
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Record mouse scroll"""
        if not self.recording:
            return
            
        # Calculate delay since last event
        now = time.time()
        delay = now - self.last_event_time if self.last_event_time else 0
        self.last_event_time = now
        
        # Record the scroll
        self.recorded_steps.append({
            'type': 'mouse_scroll',
            'params': {'x': x, 'y': y, 'dx': dx, 'dy': dy},
            'delay': delay
        })
        
    def _on_key_press(self, key):
        """Record key press"""
        if not self.recording:
            return
            
        # Calculate delay since last event
        now = time.time()
        delay = now - self.last_event_time if self.last_event_time else 0
        self.last_event_time = now
        
        # Convert key to string representation
        try:
            if hasattr(key, 'char'):
                key_str = key.char
            else:
                key_str = str(key).replace('Key.', '')
        except:
            key_str = str(key).replace('Key.', '')
            
        # Record the key press
        self.recorded_steps.append({
            'type': 'key_press',
            'params': {'key': key_str},
            'delay': delay
        })
        
    def _on_key_release(self, key):
        """Record key release"""
        if not self.recording:
            return
            
        # We don't need to record key releases for most automation purposes
        pass
