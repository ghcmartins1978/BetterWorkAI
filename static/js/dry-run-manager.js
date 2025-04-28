/**
 * Dry-Run Manager
 * 
 * This module provides a bridge between the DryRunOverlay and the macro execution API.
 * It handles the execution of macros in dry-run mode, simulating the execution visually.
 */

class DryRunManager {
    constructor() {
        this.running = false;
        this.overlay = null;
        
        // Defer overlay creation until needed to ensure DOM is ready
        this._initializeOverlay();
    }
    
    /**
     * Initialize the overlay when needed
     * This helps avoid DOM-related errors during page load
     */
    _initializeOverlay() {
        const initWhenDomReady = () => {
            try {
                if (!this.overlay) {
                    this.overlay = new DryRunOverlay();
                    console.log('Dry run overlay initialized successfully');
                }
                return this.overlay;
            } catch (error) {
                console.error('Failed to initialize dry run overlay:', error);
                return null;
            }
        };
        
        // Only initialize when DOM is ready
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            return initWhenDomReady();
        } else {
            // Schedule initialization for when DOM is ready
            window.addEventListener('DOMContentLoaded', () => {
                initWhenDomReady();
            });
            return null;
        }
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
        
        const executeWithSteps = (stepsToExecute) => {
            // Ensure we have a valid overlay
            if (!this.overlay) {
                this.overlay = this._initializeOverlay();
            }
            
            // If overlay is still not initialized, try one last time
            if (!this.overlay) {
                try {
                    this.overlay = new DryRunOverlay();
                } catch (e) {
                    console.error('Final attempt to create overlay failed:', e);
                    alert('Could not initialize the dry run visualization. Please try again or refresh the page.');
                    this.running = false;
                    return;
                }
            }
            
            this.running = true;
            this._executeDryRun(stepsToExecute);
        };
        
        // If steps are provided, use them
        if (steps && Array.isArray(steps)) {
            executeWithSteps(steps);
        } else {
            // Fetch the macro steps from the server
            fetch(`/api/automation/macros/${macroId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        executeWithSteps(data.macro.steps);
                    } else {
                        console.error('Failed to load macro:', data.message);
                        alert('Failed to load macro details. Please try again.');
                        this.running = false;
                    }
                })
                .catch(error => {
                    console.error('Error loading macro:', error);
                    alert('Error communicating with the server. Please try again.');
                    this.running = false;
                });
        }
    }
    
    /**
     * Stop the current dry run
     */
    stop() {
        if (!this.running) return;
        
        // Check if overlay exists before trying to stop it
        if (this.overlay) {
            this.overlay.stop();
        } else {
            console.warn('Tried to stop dry run but overlay is not initialized');
        }
        
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