/**
 * Dry-Run Manager
 * 
 * This module provides a bridge between the DryRunOverlay and the macro execution API.
 * It handles the execution of macros in dry-run mode, simulating the execution visually.
 */

class DryRunManager {
    constructor() {
        // Create a DryRunOverlay instance
        this.overlay = new DryRunOverlay();
        this.running = false;
    }
    
    /**
     * Start a dry run for a macro
     * @param {string} macroId - ID of the macro to run
     * @param {Array} steps - Array of step objects (optional, will be fetched from server if not provided)
     */
    start(macroId, steps = null) {
        if (this.running) {
            console.warn('A dry run is already in progress');
            return;
        }
        
        this.running = true;
        
        // If steps are provided, use them
        if (steps && Array.isArray(steps)) {
            this._executeDryRun(steps);
        } else {
            // Fetch the macro steps from the server
            fetch(`/api/automation/macros/${macroId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        this._executeDryRun(data.macro.steps);
                    } else {
                        console.error('Failed to load macro:', data.message);
                        this.running = false;
                    }
                })
                .catch(error => {
                    console.error('Error loading macro:', error);
                    this.running = false;
                });
        }
    }
    
    /**
     * Stop the current dry run
     */
    stop() {
        if (!this.running) return;
        
        this.overlay.stop();
        this.running = false;
    }
    
    /**
     * Execute the dry run with the given steps
     * @param {Array} steps - Array of step objects
     */
    _executeDryRun(steps) {
        // Start the overlay
        this.overlay.start();
        
        // Process each step with a delay
        let totalDelay = 1000; // Start with an initial delay
        const stepDelays = {
            'mouse_move': 1000,
            'mouse_click': 1500,
            'keyboard_type': 2000,
            'keyboard_press': 1000,
            'wait': 1000,
            'focus_window': 1000
        };
        
        // Convert the steps to a format suitable for visualization
        steps.forEach(step => {
            // Get step parameters, handling both string and object formats
            const params = typeof step.parameters === 'string' 
                         ? JSON.parse(step.parameters) 
                         : step.parameters;
            
            // Add delay before each step
            const stepDelay = (step.delay_before || 0) * 1000;
            totalDelay += stepDelay;
            
            switch (step.action_type) {
                case 'mouse_move':
                    setTimeout(() => {
                        this.overlay.moveMouse(params.x, params.y);
                        this.overlay.showStepIndicator(`Move mouse to (${params.x}, ${params.y})`, 'action');
                    }, totalDelay);
                    break;
                    
                case 'mouse_click':
                    setTimeout(() => {
                        this.overlay.clickMouse(params.x || 100, params.y || 100, params.button || 'left');
                        this.overlay.showStepIndicator(`Click ${params.button || 'left'} at (${params.x || 100}, ${params.y || 100})`, 'action');
                    }, totalDelay);
                    break;
                    
                case 'keyboard_type':
                    setTimeout(() => {
                        this.overlay.simulateKeyboard(params.text || '');
                        this.overlay.showStepIndicator(`Type: "${params.text || ''}"`, 'action');
                    }, totalDelay);
                    break;
                    
                case 'keyboard_press':
                    setTimeout(() => {
                        this.overlay.simulateKeyboard(params.key || 'enter', 'key');
                        this.overlay.showStepIndicator(`Press: ${params.key || 'enter'}`, 'action');
                    }, totalDelay);
                    break;
                    
                case 'wait':
                    setTimeout(() => {
                        this.overlay.simulateWait(params.seconds || 1);
                    }, totalDelay);
                    break;
                    
                case 'focus_window':
                    setTimeout(() => {
                        this.overlay.showStepIndicator(`Focus window: ${params.title || 'unknown'}`, 'action');
                    }, totalDelay);
                    break;
                    
                default:
                    setTimeout(() => {
                        this.overlay.showStepIndicator(`Unknown step: ${step.action_type}`, 'info');
                    }, totalDelay);
                    break;
            }
            
            // Add the step's execution time
            totalDelay += stepDelays[step.action_type] || 1000;
        });
        
        // Show completion and close after all steps
        setTimeout(() => {
            this.overlay.showStepIndicator('Macro execution completed', 'info');
            
            setTimeout(() => {
                this.overlay.stop();
                this.running = false;
            }, 2000);
        }, totalDelay + 1000);
    }
}

// Create a global instance
window.dryRunManager = new DryRunManager();