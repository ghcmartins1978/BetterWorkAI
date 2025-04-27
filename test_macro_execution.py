"""
Test script for macro execution.
This script tests the fixes made to the macro execution process to ensure
that temporary files are handled correctly and the compilation process is robust.
"""

import os
import time
from automation_macros import execute_macro, get_macro_status, get_log_content

def test_macro_execution():
    """Test macro execution with the fixed code."""
    # Create necessary directories
    os.makedirs("data/macros", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Macro ID from the test YAML file
    macro_id = "test_macro"  # This should match the file name in data/macros/
    
    # Execute the macro in dry-run mode
    print(f"Executing macro {macro_id} in dry-run mode...")
    result = execute_macro(macro_id, "dry-run")
    print(f"Execution result: {result}")
    
    # Wait for the macro to complete
    print("Waiting for macro to complete...")
    status = {}
    while True:
        status = get_macro_status(macro_id)
        print(f"Status: {status}")
        if status["status"] != "running":
            break
        time.sleep(1)
    
    # Get the log content
    if "log_path" in status:
        log_path = status["log_path"]
        print(f"Log file path: {log_path}")
        log_content = get_log_content(log_path)
        print(f"Log content:\n{log_content}")
        
        # Check for success indicators in the logs
        if log_content and "Script file not found" not in log_content:
            print("✅ Test PASSED: No 'Script file not found' error in logs.")
        else:
            print("❌ Test FAILED: Error in macro execution.")
    else:
        print("❌ Test FAILED: No log file path in status.")
    
    print("Test completed.")

if __name__ == "__main__":
    test_macro_execution()