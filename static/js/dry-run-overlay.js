/**
 * Dry-Run Overlay for BettermanAI
 * 
 * This module provides a visual overlay for displaying what's happening during
 * macro execution in dry-run mode, without actually performing the actions.
 */

class DryRunOverlay {
    constructor() {
        this.isActive = false;
        this.overlay = null;
        this.actionDisplay = null;
        this.logDisplay = null;
        this.closeButton = null;
        this.actions = [];
        this.currentActionIndex = -1;
        this.pollingInterval = null;
        this.logUpdateInterval = null;
        this.macroId = null;
        this.logPath = null;
    }

    /**
     * Initialize the overlay
     */
    init() {
        if (this.overlay) {
            return; // Already initialized
        }

        // Create overlay container
        this.overlay = document.createElement('div');
        this.overlay.className = 'dry-run-overlay';
        this.overlay.style.display = 'none';
        
        // Create header
        const header = document.createElement('div');
        header.className = 'dry-run-header';
        
        const title = document.createElement('h3');
        title.textContent = 'Dry Run Mode';
        title.className = 'dry-run-title';
        
        this.closeButton = document.createElement('button');
        this.closeButton.innerHTML = '&times;';
        this.closeButton.className = 'dry-run-close-btn';
        this.closeButton.addEventListener('click', () => this.hide());
        
        header.appendChild(title);
        header.appendChild(this.closeButton);
        
        // Create content container
        const content = document.createElement('div');
        content.className = 'dry-run-content';
        
        // Create action display
        this.actionDisplay = document.createElement('div');
        this.actionDisplay.className = 'dry-run-action';
        
        // Create progress container
        const progressContainer = document.createElement('div');
        progressContainer.className = 'dry-run-progress-container';
        
        this.progressBar = document.createElement('div');
        this.progressBar.className = 'dry-run-progress-bar';
        this.progressBar.style.width = '0%';
        
        progressContainer.appendChild(this.progressBar);
        
        // Create log display
        this.logDisplay = document.createElement('pre');
        this.logDisplay.className = 'dry-run-log';
        
        // Assemble the overlay
        content.appendChild(this.actionDisplay);
        content.appendChild(progressContainer);
        content.appendChild(this.logDisplay);
        
        this.overlay.appendChild(header);
        this.overlay.appendChild(content);
        
        // Add to document
        document.body.appendChild(this.overlay);
        
        // Add CSS
        this.addStyles();
    }

    /**
     * Add CSS styles for the overlay
     */
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .dry-run-overlay {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 400px;
                max-height: 80vh;
                background-color: rgba(33, 37, 41, 0.95);
                border-radius: 8px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
                z-index: 9999;
                color: white;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .dry-run-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 15px;
                background-color: rgba(25, 135, 84, 0.8);
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            
            .dry-run-title {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }
            
            .dry-run-close-btn {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0 5px;
            }
            
            .dry-run-content {
                padding: 15px;
                overflow-y: auto;
                max-height: calc(80vh - 50px);
                display: flex;
                flex-direction: column;
                gap: 15px;
            }
            
            .dry-run-action {
                background-color: rgba(13, 110, 253, 0.2);
                padding: 10px;
                border-radius: 5px;
                min-height: 60px;
                display: flex;
                align-items: center;
                font-family: monospace;
            }
            
            .dry-run-progress-container {
                height: 8px;
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                overflow: hidden;
            }
            
            .dry-run-progress-bar {
                height: 100%;
                background-color: #0d6efd;
                transition: width 0.3s ease;
            }
            
            .dry-run-log {
                background-color: rgba(0, 0, 0, 0.3);
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
                overflow-y: auto;
                max-height: 200px;
                white-space: pre-wrap;
                margin: 0;
            }
            
            .action-highlight {
                animation: highlight 2s ease;
            }
            
            @keyframes highlight {
                0%, 100% { background-color: rgba(13, 110, 253, 0.2); }
                50% { background-color: rgba(13, 110, 253, 0.5); }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Start the dry run with the given macro ID
     * 
     * @param {string} macroId - ID of the macro to execute
     * @param {Array} steps - Array of steps in the macro
     */
    start(macroId, steps) {
        this.init();
        this.macroId = macroId;
        this.actions = steps;
        this.currentActionIndex = -1;
        
        // Execute the macro in dry-run mode
        fetch(`/api/automation/macros/${macroId}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mode: 'dry-run' }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'running') {
                this.isActive = true;
                this.logPath = data.log_path;
                
                // Show the overlay
                this.show();
                
                // Start polling for status and log updates
                this.startPolling();
            } else {
                console.error('Failed to start macro in dry-run mode:', data);
                alert('Failed to start dry-run mode: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error starting dry-run:', error);
            alert('Error starting dry-run: ' + error.message);
        });
    }

    /**
     * Show the overlay
     */
    show() {
        if (!this.overlay) {
            this.init();
        }
        this.overlay.style.display = 'flex';
    }

    /**
     * Hide the overlay
     */
    hide() {
        if (this.overlay) {
            this.overlay.style.display = 'none';
        }
        
        // Stop polling
        this.stopPolling();
        
        // If macro is still running, try to stop it
        if (this.isActive && this.macroId) {
            fetch(`/api/automation/macros/${this.macroId}/stop`, {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                console.log('Stopped macro:', data);
            })
            .catch(error => {
                console.error('Error stopping macro:', error);
            });
        }
        
        this.isActive = false;
    }

    /**
     * Start polling for status and log updates
     */
    startPolling() {
        // Poll for status every 500ms
        this.pollingInterval = setInterval(() => {
            fetch(`/api/automation/macros/${this.macroId}/status`)
                .then(response => response.json())
                .then(data => {
                    // Update progress based on execution status
                    this.updateExecution(data);
                    
                    // If execution is complete, stop polling
                    if (data.status !== 'running') {
                        setTimeout(() => {
                            if (this.isActive) {
                                // Show completion message
                                this.actionDisplay.innerHTML = `
                                    <div>
                                        <span class="badge bg-${data.status === 'completed' ? 'success' : 'danger'} me-2">
                                            ${data.status === 'completed' ? 'Completed' : 'Failed'}
                                        </span>
                                        <span>Macro execution ${data.status === 'completed' ? 'completed successfully' : 'failed'}</span>
                                    </div>
                                `;
                                this.progressBar.style.width = '100%';
                                
                                // Stop polling after a delay
                                setTimeout(() => this.stopPolling(), 5000);
                            }
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error polling macro status:', error);
                });
        }, 500);
        
        // Update logs every 1s
        this.logUpdateInterval = setInterval(() => {
            if (this.logPath) {
                fetch(`/api/automation/logs/${this.logPath}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            this.updateLogs(data.content);
                            
                            // Try to determine current action from logs
                            this.determineCurrentAction(data.content);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching logs:', error);
                    });
            }
        }, 1000);
    }

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        
        if (this.logUpdateInterval) {
            clearInterval(this.logUpdateInterval);
            this.logUpdateInterval = null;
        }
    }

    /**
     * Update execution progress based on status data
     * 
     * @param {Object} statusData - Status data from API
     */
    updateExecution(statusData) {
        // Display runtime
        const runtime = statusData.runtime ? Math.round(statusData.runtime) : 0;
        const runtimeDisplay = document.createElement('div');
        runtimeDisplay.className = 'mt-2 text-muted';
        runtimeDisplay.innerHTML = `Runtime: ${runtime}s`;
        
        // Update progress if we have a new action
        if (this.currentActionIndex >= 0 && this.currentActionIndex < this.actions.length) {
            const progress = ((this.currentActionIndex + 1) / this.actions.length) * 100;
            this.progressBar.style.width = `${progress}%`;
        }
    }

    /**
     * Update the log display
     * 
     * @param {string} logContent - Content of the log
     */
    updateLogs(logContent) {
        // Split log content into lines for better formatting
        const logLines = logContent.split('\n');
        
        // Take last 20 lines
        const lastLines = logLines.slice(-20);
        
        // Update log display
        this.logDisplay.textContent = lastLines.join('\n');
        
        // Scroll to bottom
        this.logDisplay.scrollTop = this.logDisplay.scrollHeight;
    }

    /**
     * Determine the current action from log content
     * 
     * @param {string} logContent - Content of the log
     */
    determineCurrentAction(logContent) {
        // Look for execution markers in the log
        // This is a simple heuristic and might need to be adjusted based on actual log format
        
        // Increment action index if we find a marker for the next action
        // For now, just increment periodically to simulate action progression
        
        // If we don't have a reliable way to determine the current action from logs,
        // we might need to modify the TagUI wrapper to output structured logs
        
        const nextIndex = this.currentActionIndex + 1;
        if (nextIndex < this.actions.length) {
            // Move to next action (in a real implementation, this would be based on log content)
            this.currentActionIndex = nextIndex;
            this.showAction(this.actions[nextIndex]);
        }
    }

    /**
     * Show an action in the action display
     * 
     * @param {Object} action - Action to display
     */
    showAction(action) {
        // Create action display
        let actionHtml = '';
        
        // Format based on action type
        switch (action.type) {
            case 'mouse_click':
                actionHtml = `
                    <div>
                        <span class="badge bg-primary me-2">Click</span>
                        <span>Position: (${action.params.x}, ${action.params.y})</span>
                        <span class="ms-2 badge bg-secondary">${action.params.button} button</span>
                    </div>
                `;
                break;
                
            case 'mouse_move':
                actionHtml = `
                    <div>
                        <span class="badge bg-info me-2">Move</span>
                        <span>Position: (${action.params.x}, ${action.params.y})</span>
                    </div>
                `;
                break;
                
            case 'keyboard_type':
                actionHtml = `
                    <div>
                        <span class="badge bg-success me-2">Type</span>
                        <span>"${action.params.text}"</span>
                    </div>
                `;
                break;
                
            case 'keyboard_press':
                actionHtml = `
                    <div>
                        <span class="badge bg-warning me-2">Press</span>
                        <span>Key: ${action.params.key}</span>
                    </div>
                `;
                break;
                
            case 'wait':
                actionHtml = `
                    <div>
                        <span class="badge bg-secondary me-2">Wait</span>
                        <span>${action.params.seconds} seconds</span>
                    </div>
                `;
                break;
                
            case 'window_focus':
                actionHtml = `
                    <div>
                        <span class="badge bg-dark me-2">Focus</span>
                        <span>Window: "${action.params.title}"</span>
                    </div>
                `;
                break;
                
            default:
                actionHtml = `
                    <div>
                        <span class="badge bg-secondary me-2">${action.type}</span>
                        <span>${JSON.stringify(action.params)}</span>
                    </div>
                `;
        }
        
        // Update display
        this.actionDisplay.innerHTML = actionHtml;
        
        // Add highlight animation
        this.actionDisplay.classList.remove('action-highlight');
        void this.actionDisplay.offsetWidth; // Trigger reflow
        this.actionDisplay.classList.add('action-highlight');
    }
}

// Create global instance
window.dryRunOverlay = new DryRunOverlay();