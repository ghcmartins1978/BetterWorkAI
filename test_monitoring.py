import os
import time
import json
from monitor_controller import MonitorController

# Create controller
controller = MonitorController()

# Check if we can connect
if controller.is_connected():
    print("Successfully connected to Rust helper!")
    
    # Get current status
    status = controller.get_status()
    print(f"Current status: {json.dumps(status, indent=2)}")
    
    # Start monitoring
    print("\nStarting monitoring...")
    result = controller.start_monitoring()
    print(f"Result: {json.dumps(result, indent=2)}")
    
    if result.get('success', False):
        print("\nMonitoring started successfully!")
        print("Now perform some actions on your computer (move mouse, type, change windows) for 10 seconds...")
        
        # Wait for some events to be generated
        time.sleep(10)
        
        # Get events
        print("\nRetrieving events...")
        events = controller.get_events(count=10)
        print(f"Retrieved {len(events)} events:")
        
        for i, event in enumerate(events):
            print(f"Event {i+1}: {event['type']} at {event['timestamp']}")
            if 'window' in event:
                print(f"  Window: {event['window']}")
            if 'x' in event and 'y' in event:
                print(f"  Position: ({event['x']}, {event['y']})")
            if 'key' in event:
                print(f"  Key: {event['key']}")
        
        # Stop monitoring
        print("\nStopping monitoring...")
        result = controller.stop_monitoring()
        print(f"Result: {json.dumps(result, indent=2)}")
    else:
        print(f"Failed to start monitoring: {result.get('error', 'Unknown error')}")
else:
    print("Failed to connect to Rust helper.")
    print("Make sure the local Rust helper is running and the URL is correct.")
    print(f"Current helper URL: {controller.server_url}")