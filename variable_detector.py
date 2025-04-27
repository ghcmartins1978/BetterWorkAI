"""
Variable detection and management for automation macros.
This module identifies potential variables in macro steps and provides utilities
to extract, replace, and manage them during execution.
"""
import json
import re
import logging
from typing import Dict, List, Any, Set, Tuple, Optional, Union
from datetime import datetime
from models import Macro, MacroStep, MacroVariable
from database import db_session

logger = logging.getLogger(__name__)

# Variable placeholder pattern {{variable_name}}
VARIABLE_PATTERN = r'{{([A-Za-z0-9_]+)}}'


def detect_variables_in_macro(macro_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Detect all variables used in the steps of a macro.
    This function scans each step in the macro and identifies text strings that
    match the variable pattern {{variable_name}}.
    
    Args:
        macro_id: ID of the macro to analyze
        
    Returns:
        Dictionary with variable names as keys and lists of occurrences as values
    """
    macro = db_session.query(Macro).get(macro_id)
    if not macro:
        logger.error(f"Macro with ID {macro_id} not found")
        return {}
    
    steps = db_session.query(MacroStep).filter_by(macro_id=macro.id).order_by(MacroStep.step_number).all()
    if not steps:
        logger.info(f"No steps found for macro {macro_id}")
        return {}
    
    variables = {}
    
    for step in steps:
        try:
            # Parse the step parameters
            params = json.loads(step.parameters)
            
            # Find variables in each parameter value
            for param_name, param_value in params.items():
                if isinstance(param_value, str):
                    matches = re.findall(VARIABLE_PATTERN, param_value)
                    for var_name in matches:
                        if var_name not in variables:
                            variables[var_name] = []
                        
                        variables[var_name].append({
                            'step_id': step.id,
                            'step_number': step.step_number,
                            'action_type': step.action_type,
                            'parameter_name': param_name,
                            'parameter_value': param_value
                        })
        except json.JSONDecodeError:
            logger.error(f"Failed to parse parameters for step {step.id} in macro {macro_id}")
        except Exception as e:
            logger.error(f"Error analyzing step {step.id} in macro {macro_id}: {str(e)}")
    
    return variables


def register_variables_for_macro(macro_id: int) -> List[Dict[str, Any]]:
    """
    Register detected variables in the database.
    This function detects all variables in a macro, creates MacroVariable records for them
    if they don't already exist, and returns information about all variables.
    
    Args:
        macro_id: ID of the macro to register variables for
        
    Returns:
        List of dictionaries with variable information
    """
    # Detect all variables in the macro
    variables = detect_variables_in_macro(macro_id)
    if not variables:
        return []
    
    # Get existing variables for this macro
    existing_variables = db_session.query(MacroVariable).filter_by(macro_id=macro_id).all()
    existing_var_names = {v.name for v in existing_variables}
    
    # Register new variables
    var_info = []
    for var_name, occurrences in variables.items():
        if var_name not in existing_var_names:
            # Create a new variable record
            var = MacroVariable(
                macro_id=macro_id,
                name=var_name,
                description=f"Automatically detected in {len(occurrences)} step(s)",
                default_value="",
                current_value="",
                variable_type="string",
                is_required=1
            )
            db_session.add(var)
            
            # Infer variable type from its usages
            var.variable_type = _infer_variable_type(occurrences)
            
            var_info.append({
                'name': var_name,
                'description': var.description,
                'type': var.variable_type,
                'is_new': True,
                'occurrences': occurrences
            })
        else:
            # Variable already exists, add information to the result
            var = next((v for v in existing_variables if v.name == var_name), None)
            if var:  # Ensure var is not None
                var_info.append({
                    'name': var_name,
                    'description': var.description or f"Variable {var_name}",
                    'default_value': var.default_value or "",
                    'current_value': var.current_value or "",
                    'type': var.variable_type or "string",
                    'is_required': var.is_required == 1 if var.is_required is not None else True,
                    'is_new': False,
                    'occurrences': occurrences
                })
    
    # Commit changes to the database
    try:
        db_session.commit()
        logger.info(f"Registered {len(var_info)} variables for macro {macro_id}")
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error registering variables for macro {macro_id}: {str(e)}")
    
    return var_info


def _infer_variable_type(occurrences: List[Dict[str, Any]]) -> str:
    """
    Infer the likely type of a variable based on its usage.
    
    Args:
        occurrences: List of dictionaries with information about variable occurrences
        
    Returns:
        Inferred variable type ('string', 'number', 'boolean', etc.)
    """
    # Default to string
    inferred_type = "string"
    
    for occurrence in occurrences:
        param_name = occurrence.get('parameter_name', '')
        action_type = occurrence.get('action_type', '')
        
        # Coordinate parameters are likely numbers
        if param_name in ['x', 'y'] and action_type in ['mouse_move', 'mouse_click']:
            return "number"
        
        # Seconds or delay are likely numbers
        if param_name in ['seconds', 'delay', 'timeout']:
            return "number"
        
        # Button type might be a choice from limited options
        if param_name == 'button' and action_type == 'mouse_click':
            return "choice"
    
    return inferred_type


def replace_variables_in_params(params: Dict[str, Any], variables: Dict[str, str]) -> Dict[str, Any]:
    """
    Replace variable placeholders in parameters with their values.
    
    Args:
        params: Dictionary of parameters
        variables: Dictionary mapping variable names to their values
        
    Returns:
        Dictionary with variables replaced by their values
    """
    result = {}
    
    for key, value in params.items():
        if isinstance(value, str):
            # Replace all variables in the string
            new_value = value
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                new_value = new_value.replace(placeholder, str(var_value))
            
            # Try to convert to number if it looks like one
            if new_value.isdigit():
                new_value = int(new_value)
            elif _is_float(new_value):
                new_value = float(new_value)
                
            result[key] = new_value
        else:
            # Non-string values don't contain variables
            result[key] = value
    
    return result


def _is_float(value: str) -> bool:
    """Check if a string can be converted to a float."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def get_variables_for_macro(macro_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Get all variables for a macro with their current values.
    
    Args:
        macro_id: ID of the macro to get variables for
        
    Returns:
        Dictionary mapping variable names to their information
    """
    variables = db_session.query(MacroVariable).filter_by(macro_id=macro_id).all()
    return {
        var.name: {
            'id': var.id,
            'name': var.name,
            'description': var.description or f"Variable {var.name}",
            'default_value': var.default_value or "",
            'current_value': var.current_value or var.default_value or '',
            'type': var.variable_type or "string",
            'is_required': var.is_required == 1 if var.is_required is not None else True
        }
        for var in variables
    }


def update_variable_value(variable_id: int, value: str) -> bool:
    """
    Update the current value of a variable.
    
    Args:
        variable_id: ID of the variable to update
        value: New value for the variable
        
    Returns:
        True if successful, False otherwise
    """
    try:
        variable = db_session.query(MacroVariable).get(variable_id)
        if not variable:
            logger.error(f"Variable with ID {variable_id} not found")
            return False
        
        variable.current_value = value
        variable.updated_at = datetime.now()
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating variable {variable_id}: {str(e)}")
        return False