"""
Automation macros module for BettermanAI.
This module provides functions to record, edit, and execute automation macros.
It serves as a bridge between the Python backend and the Rust-based TagUI wrapper.
"""

import json
import os
import subprocess
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import tempfile
import yaml

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MACRO_DIR = os.path.join("data", "macros")
LOGS_DIR = "logs"
TAGUI_WRAPPER = os.path.join("target", "release", "tagui_wrapper")
if os.name == "nt":  # Windows
    TAGUI_WRAPPER += ".exe"


class AutomationMacro:
    """Class representing an automation macro."""

    def __init__(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[Dict[str, Any]]] = None,
        macro_id: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        icon: str = "robot",
        color: str = "info",
        tags: Optional[List[str]] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ):
        """
        Initialize an automation macro.

        Args:
            name: Name of the macro
            description: Description of the macro
            steps: List of steps to execute
            macro_id: Unique ID for the macro (generated if not provided)
            variables: Dictionary of variables used in the macro
            icon: Icon to use for the macro
            color: Color to use for the macro
            tags: List of tags for the macro
            created_at: Timestamp when the macro was created
            updated_at: Timestamp when the macro was last updated
        """
        self.name = name
        self.description = description
        self.steps = steps or []
        self.macro_id = macro_id or str(uuid.uuid4())
        self.variables = variables or {}
        self.icon = icon
        self.color = color
        self.tags = tags or []
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert the macro to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "macro_id": self.macro_id,
            "variables": self.variables,
            "icon": self.icon,
            "color": self.color,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_yaml(self) -> str:
        """Convert the macro to YAML format."""
        # Convert the steps to a format compatible with TagUI
        tagui_steps = []
        for step in self.steps:
            tagui_step = self._convert_step_to_tagui(step)
            if tagui_step:
                tagui_steps.append(tagui_step)

        # Create the YAML structure
        yaml_data = {
            "metadata": {
                "name": self.name,
                "description": self.description,
                "id": self.macro_id,
                "tags": self.tags,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            },
            "variables": self.variables,
            "steps": tagui_steps,
        }

        return yaml.dump(yaml_data, default_flow_style=False)

    def _convert_step_to_tagui(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert a step to TagUI format.

        Args:
            step: Step to convert

        Returns:
            TagUI step in dictionary format, or None if the step is not supported
        """
        action_type = step.get("type", "")
        params = step.get("params", {})

        # Map our actions to TagUI actions
        if action_type == "mouse_click":
            return {
                "action": "click",
                "target": f"{params.get('x', 0)},{params.get('y', 0)}",
                "button": params.get("button", "left"),
            }
        elif action_type == "mouse_move":
            return {
                "action": "hover",
                "target": f"{params.get('x', 0)},{params.get('y', 0)}",
            }
        elif action_type == "keyboard_type":
            return {
                "action": "type",
                "target": "page",
                "value": params.get("text", ""),
            }
        elif action_type == "keyboard_press":
            return {
                "action": "keyboard",
                "keys": params.get("key", ""),
            }
        elif action_type == "wait":
            return {
                "action": "wait",
                "seconds": params.get("seconds", 1),
            }
        elif action_type == "window_focus":
            return {
                "action": "focus",
                "window": params.get("title", ""),
            }
        # Add more mappings as needed

        logger.warning(f"Unsupported action type: {action_type}")
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutomationMacro":
        """Create a macro from a dictionary."""
        return cls(
            name=data.get("name", "Unnamed Macro"),
            description=data.get("description", ""),
            steps=data.get("steps", []),
            macro_id=data.get("macro_id"),
            variables=data.get("variables", {}),
            icon=data.get("icon", "robot"),
            color=data.get("color", "info"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "AutomationMacro":
        """Create a macro from YAML content."""
        data = yaml.safe_load(yaml_content)
        metadata = data.get("metadata", {})
        steps = []

        # Convert TagUI steps to our format
        for step in data.get("steps", []):
            our_step = cls._convert_tagui_to_step(step)
            if our_step:
                steps.append(our_step)

        return cls(
            name=metadata.get("name", "Unnamed Macro"),
            description=metadata.get("description", ""),
            steps=steps,
            macro_id=metadata.get("id"),
            variables=data.get("variables", {}),
            tags=metadata.get("tags", []),
            created_at=metadata.get("created_at"),
            updated_at=metadata.get("updated_at"),
        )

    @staticmethod
    def _convert_tagui_to_step(tagui_step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert a TagUI step to our format.

        Args:
            tagui_step: TagUI step in dictionary format

        Returns:
            Step in our format, or None if the step is not supported
        """
        action = tagui_step.get("action", "")

        if action == "click":
            target = tagui_step.get("target", "0,0")
            try:
                x, y = map(int, target.split(","))
                return {
                    "type": "mouse_click",
                    "params": {
                        "x": x,
                        "y": y,
                        "button": tagui_step.get("button", "left"),
                    },
                }
            except ValueError:
                # Handle element selector clicks (not implemented in this example)
                return None
        elif action == "hover":
            target = tagui_step.get("target", "0,0")
            try:
                x, y = map(int, target.split(","))
                return {
                    "type": "mouse_move",
                    "params": {
                        "x": x,
                        "y": y,
                    },
                }
            except ValueError:
                # Handle element selector hovers (not implemented in this example)
                return None
        elif action == "type":
            return {
                "type": "keyboard_type",
                "params": {
                    "text": tagui_step.get("value", ""),
                },
            }
        elif action == "keyboard":
            return {
                "type": "keyboard_press",
                "params": {
                    "key": tagui_step.get("keys", ""),
                },
            }
        elif action == "wait":
            return {
                "type": "wait",
                "params": {
                    "seconds": tagui_step.get("seconds", 1),
                },
            }
        elif action == "focus":
            return {
                "type": "window_focus",
                "params": {
                    "title": tagui_step.get("window", ""),
                },
            }
        # Add more mappings as needed

        logger.warning(f"Unsupported TagUI action: {action}")
        return None


class AutomationMacroManager:
    """Manager for automation macros."""

    def __init__(self):
        """Initialize the manager."""
        # Ensure the macro and logs directories exist
        os.makedirs(MACRO_DIR, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)
        self.running_processes = {}

    def save_macro(self, macro: AutomationMacro) -> str:
        """
        Save a macro to disk.

        Args:
            macro: Macro to save

        Returns:
            Path to the saved macro file
        """
        # Update the updated_at timestamp
        macro.updated_at = time.time()

        # Create the macro file path
        file_path = os.path.join(MACRO_DIR, f"{macro.macro_id}.yaml")

        # Write the macro to disk in YAML format
        with open(file_path, "w") as f:
            f.write(macro.to_yaml())

        logger.info(f"Saved macro {macro.name} to {file_path}")
        return file_path

    def load_macro(self, macro_id: str) -> Optional[AutomationMacro]:
        """
        Load a macro from disk.

        Args:
            macro_id: ID of the macro to load

        Returns:
            Loaded macro, or None if the macro doesn't exist
        """
        file_path = os.path.join(MACRO_DIR, f"{macro_id}.yaml")
        if not os.path.exists(file_path):
            logger.warning(f"Macro with ID {macro_id} not found at {file_path}")
            return None

        try:
            with open(file_path, "r") as f:
                yaml_content = f.read()
            return AutomationMacro.from_yaml(yaml_content)
        except Exception as e:
            logger.error(f"Error loading macro {macro_id}: {e}")
            return None

    def list_macros(self) -> List[Dict[str, Any]]:
        """
        List all available macros.

        Returns:
            List of macro metadata dictionaries
        """
        macros = []
        for filename in os.listdir(MACRO_DIR):
            if filename.endswith(".yaml"):
                try:
                    macro_id = filename[:-5]  # Remove .yaml extension
                    macro = self.load_macro(macro_id)
                    if macro:
                        # Return only metadata, not the full macro with steps
                        macros.append({
                            "macro_id": macro.macro_id,
                            "name": macro.name,
                            "description": macro.description,
                            "icon": macro.icon,
                            "color": macro.color,
                            "tags": macro.tags,
                            "created_at": macro.created_at,
                            "updated_at": macro.updated_at,
                        })
                except Exception as e:
                    logger.error(f"Error loading macro from {filename}: {e}")
        return macros

    def delete_macro(self, macro_id: str) -> bool:
        """
        Delete a macro.

        Args:
            macro_id: ID of the macro to delete

        Returns:
            True if the macro was deleted, False otherwise
        """
        file_path = os.path.join(MACRO_DIR, f"{macro_id}.yaml")
        if not os.path.exists(file_path):
            logger.warning(f"Macro with ID {macro_id} not found at {file_path}")
            return False

        try:
            os.remove(file_path)
            logger.info(f"Deleted macro {macro_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting macro {macro_id}: {e}")
            return False

    def execute_macro(self, macro_id: str, mode: str = "normal") -> Dict[str, Any]:
        """
        Execute a macro using the TagUI wrapper.

        Args:
            macro_id: ID of the macro to execute
            mode: Execution mode (normal or dry-run)

        Returns:
            Dictionary with execution status and details
        """
        # Load the macro
        macro = self.load_macro(macro_id)
        if not macro:
            return {"status": "error", "message": f"Macro with ID {macro_id} not found"}

        # Prepare the command
        file_path = os.path.join(MACRO_DIR, f"{macro_id}.yaml")
        if not os.path.isfile(file_path):
            return {"status": "error", "message": f"Macro file {file_path} not found"}

        # For now, we're using a subprocess to call our TagUI wrapper
        # Later, this can be replaced with direct calls to the Rust library
        try:
            # Check if the binary exists
            tagui_binary = os.path.abspath(os.path.join("resources", "tagui", "src", "tagui"))
            if os.name == "nt":  # Windows
                tagui_binary = os.path.abspath(os.path.join("resources", "tagui", "tagui.exe"))

            if not os.path.isfile(tagui_binary):
                return {"status": "error", "message": f"TagUI binary not found at {tagui_binary}"}

            # Prepare the log file path
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_file_name = f"macro_{macro_id}_{timestamp}.log"
            log_path = os.path.join(LOGS_DIR, log_file_name)

            # Prepare the command
            cmd = [tagui_binary, file_path]
            if mode.lower() == "dry-run":
                cmd.append("-n")
            cmd.append("--nobrowser")  # For safety

            # Execute the command
            with open(log_path, "w") as log_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

            # Store the process and log info
            self.running_processes[macro_id] = {
                "process": process,
                "log_path": log_path,
                "start_time": time.time(),
            }

            return {
                "status": "running",
                "macro_id": macro_id,
                "pid": process.pid,
                "log_path": log_path,
            }

        except Exception as e:
            logger.error(f"Error executing macro {macro_id}: {e}")
            return {"status": "error", "message": str(e)}

    def get_macro_status(self, macro_id: str) -> Dict[str, Any]:
        """
        Get the status of a running macro.

        Args:
            macro_id: ID of the macro to check

        Returns:
            Dictionary with status information
        """
        if macro_id not in self.running_processes:
            return {"status": "not_running", "macro_id": macro_id}

        process_info = self.running_processes[macro_id]
        process = process_info["process"]

        # Check if the process is still running
        if process.poll() is None:
            # Process is still running
            return {
                "status": "running",
                "macro_id": macro_id,
                "pid": process.pid,
                "log_path": process_info["log_path"],
                "runtime": time.time() - process_info["start_time"],
            }
        else:
            # Process has finished
            exit_code = process.returncode
            status = "completed" if exit_code == 0 else "failed"

            # Clean up
            del self.running_processes[macro_id]

            return {
                "status": status,
                "macro_id": macro_id,
                "exit_code": exit_code,
                "log_path": process_info["log_path"],
                "runtime": time.time() - process_info["start_time"],
            }

    def stop_macro(self, macro_id: str) -> Dict[str, Any]:
        """
        Stop a running macro.

        Args:
            macro_id: ID of the macro to stop

        Returns:
            Dictionary with stop status
        """
        if macro_id not in self.running_processes:
            return {"status": "not_running", "macro_id": macro_id}

        process_info = self.running_processes[macro_id]
        process = process_info["process"]

        # Try to terminate the process
        try:
            process.terminate()
            # Give it some time to terminate gracefully
            for _ in range(10):
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            # If it's still running, kill it
            if process.poll() is None:
                process.kill()

            # Clean up
            del self.running_processes[macro_id]

            return {
                "status": "stopped",
                "macro_id": macro_id,
                "log_path": process_info["log_path"],
            }
        except Exception as e:
            logger.error(f"Error stopping macro {macro_id}: {e}")
            return {"status": "error", "message": str(e)}

    def get_log_content(self, log_path: str) -> Optional[str]:
        """
        Get the content of a log file.

        Args:
            log_path: Path to the log file

        Returns:
            Content of the log file, or None if the file doesn't exist
        """
        if not os.path.isfile(log_path):
            logger.warning(f"Log file {log_path} not found")
            return None

        try:
            with open(log_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading log file {log_path}: {e}")
            return None


# Create a global instance of the macro manager
macro_manager = AutomationMacroManager()


def list_macros() -> List[Dict[str, Any]]:
    """
    List all available macros.

    Returns:
        List of macro metadata dictionaries
    """
    return macro_manager.list_macros()


def get_macro(macro_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a macro by ID.

    Args:
        macro_id: ID of the macro to get

    Returns:
        Macro as a dictionary, or None if the macro doesn't exist
    """
    macro = macro_manager.load_macro(macro_id)
    if macro:
        return macro.to_dict()
    return None


def save_macro(macro_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a macro.

    Args:
        macro_data: Macro data as a dictionary

    Returns:
        Dictionary with save status and macro ID
    """
    try:
        macro = AutomationMacro.from_dict(macro_data)
        file_path = macro_manager.save_macro(macro)
        return {
            "status": "saved",
            "macro_id": macro.macro_id,
            "file_path": file_path,
        }
    except Exception as e:
        logger.error(f"Error saving macro: {e}")
        return {"status": "error", "message": str(e)}


def delete_macro(macro_id: str) -> Dict[str, Any]:
    """
    Delete a macro.

    Args:
        macro_id: ID of the macro to delete

    Returns:
        Dictionary with delete status
    """
    success = macro_manager.delete_macro(macro_id)
    if success:
        return {"status": "deleted", "macro_id": macro_id}
    return {"status": "error", "message": f"Failed to delete macro {macro_id}"}


def execute_macro(macro_id: str, mode: str = "normal") -> Dict[str, Any]:
    """
    Execute a macro.

    Args:
        macro_id: ID of the macro to execute
        mode: Execution mode (normal or dry-run)

    Returns:
        Dictionary with execution status and details
    """
    return macro_manager.execute_macro(macro_id, mode)


def get_macro_status(macro_id: str) -> Dict[str, Any]:
    """
    Get the status of a running macro.

    Args:
        macro_id: ID of the macro to check

    Returns:
        Dictionary with status information
    """
    return macro_manager.get_macro_status(macro_id)


def stop_macro(macro_id: str) -> Dict[str, Any]:
    """
    Stop a running macro.

    Args:
        macro_id: ID of the macro to stop

    Returns:
        Dictionary with stop status
    """
    return macro_manager.stop_macro(macro_id)


def get_log_content(log_path: str) -> Optional[str]:
    """
    Get the content of a log file.

    Args:
        log_path: Path to the log file

    Returns:
        Content of the log file, or None if the file doesn't exist
    """
    return macro_manager.get_log_content(log_path)


# Test function to create a sample macro
def create_sample_macro() -> str:
    """
    Create a sample macro for testing.

    Returns:
        ID of the created macro
    """
    macro = AutomationMacro(
        name="Sample Macro",
        description="A sample macro for testing",
        steps=[
            {
                "type": "window_focus",
                "params": {"title": "Notepad"},
            },
            {
                "type": "wait",
                "params": {"seconds": 1},
            },
            {
                "type": "mouse_click",
                "params": {"x": 100, "y": 100, "button": "left"},
            },
            {
                "type": "keyboard_type",
                "params": {"text": "Hello from BettermanAI!"},
            },
            {
                "type": "keyboard_press",
                "params": {"key": "enter"},
            },
        ],
        tags=["sample", "test"],
    )
    macro_manager.save_macro(macro)
    return macro.macro_id


if __name__ == "__main__":
    # Create the data directory if it doesn't exist
    os.makedirs(MACRO_DIR, exist_ok=True)

    # Create a sample macro
    macro_id = create_sample_macro()
    print(f"Created sample macro with ID: {macro_id}")

    # Test executing the macro
    result = execute_macro(macro_id, "dry-run")
    print(f"Execution result: {result}")

    # Wait for the macro to complete
    while True:
        status = get_macro_status(macro_id)
        print(f"Status: {status}")
        if status["status"] != "running":
            break
        time.sleep(1)

    # Get the log content
    if "log_path" in result:
        log_content = get_log_content(result["log_path"])
        print(f"Log content:\n{log_content}")