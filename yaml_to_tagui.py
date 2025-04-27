"""
YAML to TagUI compiler for BettermanAI.

This module converts YAML-based automation descriptions to TagUI script format.
Part of Ticket A2 - YAML DSL Compiler implementation.
"""

import os
import re
import yaml
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YAMLToTagUICompiler:
    """
    Compiler that converts YAML-based automation descriptions to TagUI script format.
    """
    
    def __init__(self):
        """Initialize the compiler with default settings."""
        # Definition of TagUI commands and their YAML equivalents
        self.command_mapping = {
            "click": {"tagui": "click", "params": ["target", "button"]},
            "hover": {"tagui": "hover", "params": ["target"]},
            "type": {"tagui": "type", "params": ["target", "value"]},
            "keyboard": {"tagui": "keyboard", "params": ["keys"]},
            "wait": {"tagui": "wait", "params": ["seconds"]},
            "focus": {"tagui": "focus", "params": ["window"]},
            "snap": {"tagui": "snap", "params": ["target", "filename"]},
            "echo": {"tagui": "echo", "params": ["message"]},
            "check": {"tagui": "check", "params": ["condition", "message"]},
            "assign": {"tagui": "", "params": ["variable", "value"]},  # Special case, handled differently
            "read": {"tagui": "read", "params": ["target", "to"]},
            "select": {"tagui": "select", "params": ["target", "option"]},
            "url": {"tagui": "https://", "params": ["address"]},  # Special case
            "js": {"tagui": "js", "params": ["code"]},
            "run": {"tagui": "run", "params": ["command"]},
            "if": {"tagui": "if", "params": ["condition"]},  # Special case
            "else": {"tagui": "else", "params": []},  # Special case
            "for": {"tagui": "for", "params": ["variable", "from", "to"]},  # Special case
            "break": {"tagui": "break", "params": []},
            "continue": {"tagui": "continue", "params": []},
        }
        
        # Valid mouse button options
        self.valid_buttons = ["left", "right", "middle"]
        
        # Tracks indentation level for control structures
        self.indent_level = 0
        
        # Track variables for substitution
        self.variables = {}
        
    def compile(self, yaml_file: str, output_file: Optional[str] = None) -> str:
        """
        Compile a YAML file to TagUI script.
        
        Args:
            yaml_file: Path to the YAML file
            output_file: Optional path to output file. If not provided, a path will be generated
                      based on the input file name
                      
        Returns:
            Path to the compiled TagUI script
        """
        # Load YAML data
        try:
            with open(yaml_file, "r") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading YAML file: {e}")
            raise
        
        # Generate output file path if not provided
        if output_file is None:
            output_dir = os.path.dirname(yaml_file)
            base_name = os.path.splitext(os.path.basename(yaml_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}.tag")
        
        # Generate the TagUI script
        script = self._generate_script(data)
        
        # Write the script to file
        try:
            with open(output_file, "w") as f:
                f.write(script)
            logger.info(f"Compiled TagUI script written to {output_file}")
        except Exception as e:
            logger.error(f"Error writing TagUI script: {e}")
            raise
        
        return output_file
    
    def _generate_script(self, data: Dict[str, Any]) -> str:
        """
        Generate a TagUI script from the parsed YAML data.
        
        Args:
            data: Parsed YAML data
            
        Returns:
            Complete TagUI script as a string
            
        Raises:
            ValueError: If the YAML data is missing required fields or has invalid structure
        """
        # Validate the YAML structure
        if not isinstance(data, dict):
            error_msg = f"Invalid YAML structure, expected dictionary but got {type(data)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Check for the required "steps" section
        if "steps" not in data:
            error_msg = "YAML is missing required 'steps' section"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Validate steps is a list
        if not isinstance(data.get("steps"), list):
            error_msg = f"Invalid steps format, expected list but got {type(data.get('steps'))}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Reset indentation and variables
        self.indent_level = 0
        self.variables = {}
        
        # Extract metadata and variables
        metadata = data.get("metadata", {})
        variables = data.get("variables", {})
        
        # Validate metadata is a dictionary
        if not isinstance(metadata, dict):
            error_msg = f"Invalid metadata format, expected dictionary but got {type(metadata)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Validate variables is a dictionary
        if not isinstance(variables, dict):
            error_msg = f"Invalid variables format, expected dictionary but got {type(variables)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Store variables for substitution
        self.variables = variables
        
        # Generate script header with metadata
        header = self._generate_header(metadata)
        
        # Generate variable declarations
        var_declarations = self._generate_variable_declarations(variables)
        
        # Generate steps
        steps = ""
        for i, step in enumerate(data.get("steps", [])):
            # Validate step is a dictionary
            if not isinstance(step, dict):
                error_msg = f"Invalid step format at index {i}, expected dictionary but got {type(step)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Validate step has an "action" field
            if "action" not in step:
                error_msg = f"Step at index {i} is missing required 'action' field"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            step_text = self._process_step(step)
            if step_text:
                steps += step_text + "\n"
        
        # Check if we have any steps
        if not steps.strip():
            logger.warning("No valid steps found in the YAML")
        
        # Combine all parts
        script = header + "\n" + var_declarations + "\n" + steps
        
        return script
    
    def _generate_header(self, metadata: Dict[str, Any]) -> str:
        """
        Generate the header section of the TagUI script with metadata.
        
        Args:
            metadata: Metadata dictionary from YAML
            
        Returns:
            Header section as a string
        """
        header = "// TagUI script generated by BettermanAI YAML DSL Compiler\n"
        header += "// " + "=" * 70 + "\n"
        
        # Add metadata as comments
        if metadata:
            header += "// Metadata:\n"
            for key, value in metadata.items():
                if key == "tags" and isinstance(value, list):
                    header += f"// {key}: {', '.join(value)}\n"
                else:
                    header += f"// {key}: {value}\n"
        
        header += "// " + "=" * 70 + "\n"
        return header
    
    def _generate_variable_declarations(self, variables: Dict[str, Any]) -> str:
        """
        Generate variable declarations for the TagUI script.
        
        Args:
            variables: Dictionary of variables from YAML
            
        Returns:
            Variable declarations section as a string
        """
        if not variables:
            return "// No variables defined"
        
        var_section = "// Variable declarations\n"
        
        for name, value in variables.items():
            if isinstance(value, str):
                # Escape quotes in string values
                escaped_value = value.replace('"', '\\"')
                var_section += f'{name} = "{escaped_value}"\n'
            else:
                var_section += f"{name} = {value}\n"
        
        return var_section
    
    def _process_step(self, step: Dict[str, Any]) -> str:
        """
        Process a single step and convert it to TagUI script.
        
        Args:
            step: Step dictionary from YAML
            
        Returns:
            TagUI command for this step
        """
        # Get action type
        action = step.get("action", "")
        if not action:
            logger.warning("Step missing action field, skipping")
            return ""
        
        # Check if this action is supported
        if action not in self.command_mapping:
            logger.warning(f"Unsupported action: {action}, skipping")
            return ""
        
        # Handle special control structure cases
        if action in ["if", "else", "for"]:
            return self._handle_control_structure(action, step)
        
        # Handle normal commands
        command_info = self.command_mapping[action]
        tagui_command = command_info["tagui"]
        params = command_info["params"]
        
        # Special case for URL
        if action == "url":
            if "address" in step:
                return f"{tagui_command}{step['address']}"
            else:
                logger.warning("URL step missing address, skipping")
                return ""
        
        # Special case for variable assignment
        if action == "assign":
            if "variable" in step and "value" in step:
                var_name = step["variable"]
                value = step["value"]
                if isinstance(value, str):
                    # Escape quotes in string values
                    escaped_value = value.replace('"', '\\"')
                    return f'{var_name} = "{escaped_value}"'
                else:
                    return f"{var_name} = {value}"
            else:
                logger.warning("Assign step missing variable or value, skipping")
                return ""
        
        # Process coordinates in target for click and hover
        if action in ["click", "hover"] and "target" in step:
            target = step["target"]
            if isinstance(target, str) and "," in target:
                # Check if it's an x,y coordinate pair
                try:
                    x, y = map(int, target.split(","))
                    # For coordinates, format as (x,y)
                    step["target"] = f"({x},{y})"
                except (ValueError, TypeError):
                    # Not a coordinate pair, leave as is
                    pass
        
        # Build the command with parameters
        command = tagui_command
        
        # Handle each parameter
        param_strings = []
        for param in params:
            if param in step:
                value = step[param]
                
                # Replace variables in string values
                if isinstance(value, str):
                    value = self._substitute_variables(value)
                
                # Handle different parameter types
                if param == "target":
                    param_strings.append(f"{value}")
                elif param == "button" and action == "click":
                    # Validate button value
                    if value not in self.valid_buttons:
                        logger.warning(f"Invalid button value: {value}, using 'left'")
                        value = "left"
                    param_strings.append(f"{value}")
                elif param == "condition" and action in ["if", "check"]:
                    param_strings.append(f"{value}")
                elif param == "message" and action in ["echo", "check"]:
                    param_strings.append(f'"{value}"')
                elif param == "code" and action == "js":
                    param_strings.append(f"{value}")
                elif param == "seconds" and action == "wait":
                    param_strings.append(f"{value}")
                elif param == "keys" and action == "keyboard":
                    param_strings.append(f'"{value}"')
                elif param == "value" and action == "type":
                    param_strings.append(f'"{value}"')
                elif param == "option" and action == "select":
                    param_strings.append(f'"{value}"')
                else:
                    # Default case
                    if isinstance(value, str):
                        param_strings.append(f'"{value}"')
                    else:
                        param_strings.append(f"{value}")
        
        # Add indentation based on control structures
        indent = "    " * self.indent_level
        
        # Different actions have different parameter formats
        if action == "type":
            return f"{indent}{command} {param_strings[0]} as {param_strings[1]}"
        elif action == "select":
            return f"{indent}{command} {param_strings[0]} as {param_strings[1]}"
        elif action == "read":
            return f"{indent}{command} {param_strings[0]} to {param_strings[1]}"
        elif action == "check":
            return f"{indent}{command} {param_strings[0]} | {param_strings[1]}"
        elif action == "js":
            return f"{indent}{command} {param_strings[0]}"
        elif action == "keyboard":
            return f"{indent}{command} {param_strings[0]}"
        elif action == "echo":
            return f"{indent}{command} {param_strings[0]}"
        elif action == "wait":
            return f"{indent}{command} {param_strings[0]}"
        elif action == "run":
            return f"{indent}{command} {param_strings[0]}"
        elif action == "click" and len(param_strings) > 1:
            return f"{indent}{command} {param_strings[0]} {param_strings[1]}"
        else:
            # Default format for other commands
            return f"{indent}{command} {' '.join(param_strings)}"
    
    def _handle_control_structure(self, action: str, step: Dict[str, Any]) -> str:
        """
        Handle special control structure commands (if, else, for).
        
        Args:
            action: Action type
            step: Step dictionary from YAML
            
        Returns:
            TagUI command for this control structure
        """
        indent = "    " * self.indent_level
        
        if action == "if":
            condition = step.get("condition", "")
            if not condition:
                logger.warning("If statement missing condition, skipping")
                return ""
            
            # Substitute variables in condition
            condition = self._substitute_variables(condition)
            
            # For if statements, we increase the indent level for subsequent steps
            self.indent_level += 1
            return f"{indent}if ({condition})"
        
        elif action == "else":
            # For else statements, indent level remains the same
            return f"{indent}else"
        
        elif action == "for":
            variable = step.get("variable", "")
            from_val = step.get("from", "")
            to_val = step.get("to", "")
            
            if not variable or from_val == "" or to_val == "":
                logger.warning("For loop missing parameters, skipping")
                return ""
            
            # Substitute variables
            from_val = self._substitute_variables(str(from_val))
            to_val = self._substitute_variables(str(to_val))
            
            # For for loops, we increase the indent level for subsequent steps
            self.indent_level += 1
            return f"{indent}for ({variable} = {from_val}; {variable} <= {to_val}; {variable}++)"
        
        return ""
    
    def _substitute_variables(self, text: str) -> str:
        """
        Substitute variables in text using the ${var} syntax.
        
        Args:
            text: Text containing variable references
            
        Returns:
            Text with variables substituted
        """
        # Check if there are any variable references
        if "${" not in text:
            return text
        
        # Find all variable references ${var}
        pattern = r'\${([a-zA-Z0-9_]+)}'
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.variables:
                return str(self.variables[var_name])
            else:
                logger.warning(f"Variable {var_name} not found, leaving as is")
                return match.group(0)
        
        # Replace all variable references
        result = re.sub(pattern, replace_var, text)
        return result


def compile_yaml_to_tagui(yaml_file: str, output_file: Optional[str] = None) -> str:
    """
    Compile a YAML file to TagUI script.
    
    Args:
        yaml_file: Path to the YAML file
        output_file: Optional path to output file
        
    Returns:
        Path to the compiled TagUI script
        
    Raises:
        FileNotFoundError: If the YAML file does not exist
        yaml.YAMLError: If the YAML file is invalid
        ValueError: If the YAML content is missing required sections
        IOError: If the output file cannot be written
    """
    # Check if the YAML file exists
    if not os.path.isfile(yaml_file):
        error_msg = f"YAML file not found: {yaml_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Check if the output directory exists (if output_file is provided)
    if output_file:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Created output directory: {output_dir}")
            except Exception as e:
                error_msg = f"Could not create output directory {output_dir}: {e}"
                logger.error(error_msg)
                raise IOError(error_msg)
    
    # Compile the YAML to TagUI
    try:
        compiler = YAMLToTagUICompiler()
        result = compiler.compile(yaml_file, output_file)
        
        # Double check the output file exists
        if output_file and not os.path.isfile(output_file):
            error_msg = f"Output file was not created: {output_file}"
            logger.error(error_msg)
            raise IOError(error_msg)
            
        return result
    except yaml.YAMLError as e:
        error_msg = f"Invalid YAML in {yaml_file}: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Error compiling {yaml_file}: {e}"
        logger.error(error_msg)
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python yaml_to_tagui.py <yaml_file> [output_file]")
        sys.exit(1)
    
    yaml_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        compiled_file = compile_yaml_to_tagui(yaml_file, output_file)
        print(f"Compiled {yaml_file} to {compiled_file}")
    except Exception as e:
        print(f"Error compiling {yaml_file}: {e}")
        sys.exit(1)