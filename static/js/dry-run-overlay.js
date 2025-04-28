/**
 * Dry-Run Overlay
 * 
 * This module provides visual feedback during macro execution in dry-run mode.
 * It displays overlays that indicate mouse movements, clicks, keyboard input, etc.
 */

class DryRunOverlay {
    constructor(options = {}) {
        // Default options
        this.options = {
            containerId: 'dry-run-overlay-container',
            zIndex: 9999,
            mouseIndicatorSize: 20,
            mouseIndicatorColor: '#FF5722',
            clickRippleColor: '#FF5722',
            clickRippleDuration: 1000,
            keyboardIndicatorDuration: 2000,
            showCoordinates: true,
            ...options
        };
        
        this.initialize();
    }
    
    /**
     * Initialize the overlay
     */
    initialize() {
        // Defer initialization until the DOM is fully loaded
        const ensureDomReady = () => {
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                this._createContainer();
            } else {
                // Wait for the DOM to be ready
                document.addEventListener('DOMContentLoaded', () => {
                    this._createContainer();
                });
            }
        };
        
        ensureDomReady();
    }
    
    /**
     * Create the container for the overlay elements
     * Private method called by initialize
     */
    _createContainer() {
        // Create the container if it doesn't exist
        if (!document.getElementById(this.options.containerId)) {
            try {
                const container = document.createElement('div');
                container.id = this.options.containerId;
                container.style.position = 'fixed';
                container.style.top = '0';
                container.style.left = '0';
                container.style.width = '100%';
                container.style.height = '100%';
                container.style.pointerEvents = 'none'; // Allow clicks to pass through
                container.style.zIndex = this.options.zIndex;
                container.style.overflow = 'hidden';
                container.style.display = 'none'; // Initially hidden
                
                document.body.appendChild(container);
                this.container = container;
                this._setupOverlayElements();
                return true;
            } catch (error) {
                console.error('Error creating dry-run overlay container:', error);
                return false;
            }
        } else {
            this.container = document.getElementById(this.options.containerId);
            this._setupOverlayElements();
            return true;
        }
    }
    
    /**
     * Set up the overlay elements inside the container
     * Private method called by initialize
     */
    _setupOverlayElements() {
        if (!this.container) return;
        
        // Create the mouse indicator
        this.mouseIndicator = document.createElement('div');
        this.mouseIndicator.className = 'dry-run-mouse-indicator';
        this.mouseIndicator.style.position = 'absolute';
        this.mouseIndicator.style.width = `${this.options.mouseIndicatorSize}px`;
        this.mouseIndicator.style.height = `${this.options.mouseIndicatorSize}px`;
        this.mouseIndicator.style.borderRadius = '50%';
        this.mouseIndicator.style.backgroundColor = this.options.mouseIndicatorColor;
        this.mouseIndicator.style.transform = 'translate(-50%, -50%)';
        this.mouseIndicator.style.opacity = '0.7';
        this.mouseIndicator.style.display = 'none';
        this.mouseIndicator.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
        this.mouseIndicator.style.transition = 'all 0.2s ease-out';
        this.container.appendChild(this.mouseIndicator);
        
        // Create the coordinates display
        if (this.options.showCoordinates) {
            this.coordinatesDisplay = document.createElement('div');
            this.coordinatesDisplay.className = 'dry-run-coordinates';
            this.coordinatesDisplay.style.position = 'absolute';
            this.coordinatesDisplay.style.backgroundColor = 'rgba(0,0,0,0.7)';
            this.coordinatesDisplay.style.color = 'white';
            this.coordinatesDisplay.style.padding = '5px';
            this.coordinatesDisplay.style.borderRadius = '3px';
            this.coordinatesDisplay.style.fontSize = '12px';
            this.coordinatesDisplay.style.fontFamily = 'monospace';
            this.coordinatesDisplay.style.display = 'none';
            this.container.appendChild(this.coordinatesDisplay);
        }
        
        // Create the keyboard indicator
        this.keyboardIndicator = document.createElement('div');
        this.keyboardIndicator.className = 'dry-run-keyboard-indicator';
        this.keyboardIndicator.style.position = 'fixed';
        this.keyboardIndicator.style.bottom = '20px';
        this.keyboardIndicator.style.left = '50%';
        this.keyboardIndicator.style.transform = 'translateX(-50%)';
        this.keyboardIndicator.style.backgroundColor = 'rgba(0,0,0,0.8)';
        this.keyboardIndicator.style.color = 'white';
        this.keyboardIndicator.style.padding = '10px 20px';
        this.keyboardIndicator.style.borderRadius = '5px';
        this.keyboardIndicator.style.fontFamily = 'monospace';
        this.keyboardIndicator.style.fontSize = '16px';
        this.keyboardIndicator.style.maxWidth = '80%';
        this.keyboardIndicator.style.textAlign = 'center';
        this.keyboardIndicator.style.display = 'none';
        this.keyboardIndicator.style.zIndex = this.options.zIndex + 1;
        this.container.appendChild(this.keyboardIndicator);
        
        // Create the step indicator
        this.stepIndicator = document.createElement('div');
        this.stepIndicator.className = 'dry-run-step-indicator';
        this.stepIndicator.style.position = 'fixed';
        this.stepIndicator.style.top = '20px';
        this.stepIndicator.style.right = '20px';
        this.stepIndicator.style.backgroundColor = 'rgba(0,0,0,0.8)';
        this.stepIndicator.style.color = 'white';
        this.stepIndicator.style.padding = '10px 15px';
        this.stepIndicator.style.borderRadius = '5px';
        this.stepIndicator.style.fontFamily = 'sans-serif';
        this.stepIndicator.style.fontSize = '14px';
        this.stepIndicator.style.display = 'none';
        this.stepIndicator.style.zIndex = this.options.zIndex + 1;
        this.container.appendChild(this.stepIndicator);
        
        // Initialize active flag
        this.active = false;
    }
    
    /**
     * Start the overlay
     */
    start() {
        this.container.style.display = 'block';
        this.active = true;
        this.showStepIndicator('Starting Dry Run Simulation', 'info');
        return this;
    }
    
    /**
     * Stop the overlay
     */
    stop() {
        this.hideMouseIndicator();
        this.hideKeyboardIndicator();
        this.hideStepIndicator();
        setTimeout(() => {
            this.container.style.display = 'none';
            this.active = false;
        }, 1000);
        return this;
    }
    
    /**
     * Simulate moving the mouse to a position
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     * @param {number} duration - Duration of the movement in milliseconds
     */
    moveMouse(x, y, duration = 500) {
        if (!this.active) return this;
        
        this.mouseIndicator.style.display = 'block';
        
        // Create a smooth animation to the target position
        const start = {
            x: parseInt(this.mouseIndicator.style.left) || 0,
            y: parseInt(this.mouseIndicator.style.top) || 0
        };
        
        const end = { x, y };
        const startTime = performance.now();
        
        const updatePosition = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (ease-out cubic)
            const easeOut = (t) => 1 - Math.pow(1 - t, 3);
            const easedProgress = easeOut(progress);
            
            const currentX = start.x + (end.x - start.x) * easedProgress;
            const currentY = start.y + (end.y - start.y) * easedProgress;
            
            this.mouseIndicator.style.left = `${currentX}px`;
            this.mouseIndicator.style.top = `${currentY}px`;
            
            if (this.options.showCoordinates) {
                this.coordinatesDisplay.textContent = `X: ${Math.round(currentX)}, Y: ${Math.round(currentY)}`;
                this.coordinatesDisplay.style.display = 'block';
                this.coordinatesDisplay.style.left = `${currentX + 20}px`;
                this.coordinatesDisplay.style.top = `${currentY}px`;
            }
            
            if (progress < 1) {
                requestAnimationFrame(updatePosition);
            }
        };
        
        requestAnimationFrame(updatePosition);
        return this;
    }
    
    /**
     * Simulate a mouse click
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     * @param {string} button - Mouse button ('left', 'right', 'middle')
     */
    clickMouse(x, y, button = 'left') {
        if (!this.active) return this;
        
        // Move the mouse to the click position
        this.moveMouse(x, y, 300);
        
        // Create a ripple effect
        setTimeout(() => {
            const ripple = document.createElement('div');
            ripple.className = 'dry-run-click-ripple';
            ripple.style.position = 'absolute';
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            ripple.style.width = '0';
            ripple.style.height = '0';
            ripple.style.borderRadius = '50%';
            ripple.style.backgroundColor = this.options.clickRippleColor;
            ripple.style.transform = 'translate(-50%, -50%)';
            ripple.style.opacity = '0.7';
            ripple.style.transition = `all ${this.options.clickRippleDuration / 1000}s ease-out`;
            this.container.appendChild(ripple);
            
            // Show different styles for different buttons
            let borderColor;
            if (button === 'right') {
                borderColor = '#2196F3'; // Blue for right click
                this.showStepIndicator('Right Click', 'action');
            } else if (button === 'middle') {
                borderColor = '#4CAF50'; // Green for middle click
                this.showStepIndicator('Middle Click', 'action');
            } else {
                borderColor = '#FF5722'; // Orange for left click
                this.showStepIndicator('Left Click', 'action');
            }
            
            // Highlight the mouse indicator
            this.mouseIndicator.style.borderColor = borderColor;
            this.mouseIndicator.style.borderWidth = '2px';
            this.mouseIndicator.style.borderStyle = 'solid';
            this.mouseIndicator.style.transform = 'translate(-50%, -50%) scale(1.2)';
            
            // Animate the ripple
            setTimeout(() => {
                ripple.style.width = '50px';
                ripple.style.height = '50px';
                ripple.style.opacity = '0';
                
                // Reset the mouse indicator
                setTimeout(() => {
                    this.mouseIndicator.style.borderWidth = '0';
                    this.mouseIndicator.style.transform = 'translate(-50%, -50%)';
                    
                    // Remove the ripple
                    setTimeout(() => {
                        this.container.removeChild(ripple);
                    }, 100);
                }, 300);
            }, 10);
        }, 300); // Wait for the mouse to move
        
        return this;
    }
    
    /**
     * Simulate keyboard input
     * @param {string} text - Text or key to display
     * @param {string} type - Type of keyboard input ('text', 'key')
     */
    simulateKeyboard(text, type = 'text') {
        if (!this.active) return this;
        
        // Format the text for display
        let displayText = text;
        if (type === 'key') {
            // Format special keys
            const keyMap = {
                'enter': '⏎ Enter',
                'tab': '⇥ Tab',
                'space': '␣ Space',
                'backspace': '⌫ Backspace',
                'escape': 'Esc',
                'up': '↑ Up',
                'down': '↓ Down',
                'left': '← Left',
                'right': '→ Right',
            };
            
            displayText = keyMap[text.toLowerCase()] || text;
        }
        
        // Display the keyboard indicator
        this.keyboardIndicator.textContent = type === 'text' ? `Typing: "${displayText}"` : `Pressing: ${displayText}`;
        this.keyboardIndicator.style.display = 'block';
        
        // Show step indicator
        this.showStepIndicator(type === 'text' ? `Typing text` : `Pressing ${displayText}`, 'action');
        
        // Auto-hide after a delay
        clearTimeout(this.keyboardTimeout);
        this.keyboardTimeout = setTimeout(() => {
            this.hideKeyboardIndicator();
        }, this.options.keyboardIndicatorDuration);
        
        return this;
    }
    
    /**
     * Simulate waiting
     * @param {number} seconds - Seconds to wait
     */
    simulateWait(seconds) {
        if (!this.active) return this;
        
        this.showStepIndicator(`Waiting for ${seconds} second${seconds !== 1 ? 's' : ''}`, 'wait');
        
        return this;
    }
    
    /**
     * Show a step indicator
     * @param {string} text - Text to display
     * @param {string} type - Type of step ('info', 'action', 'wait', 'error')
     */
    showStepIndicator(text, type = 'info') {
        if (!this.active) return this;
        
        // Style based on type
        let bgColor, icon;
        switch (type) {
            case 'action':
                bgColor = 'rgba(33, 150, 243, 0.9)'; // Blue
                icon = '▶';
                break;
            case 'wait':
                bgColor = 'rgba(255, 152, 0, 0.9)'; // Orange
                icon = '⏱';
                break;
            case 'error':
                bgColor = 'rgba(244, 67, 54, 0.9)'; // Red
                icon = '⚠';
                break;
            case 'info':
            default:
                bgColor = 'rgba(0, 0, 0, 0.8)'; // Black
                icon = 'ℹ';
                break;
        }
        
        this.stepIndicator.style.backgroundColor = bgColor;
        this.stepIndicator.innerHTML = `<span style="margin-right: 8px;">${icon}</span> ${text}`;
        this.stepIndicator.style.display = 'block';
        
        // Animate in
        this.stepIndicator.style.opacity = '0';
        this.stepIndicator.style.transform = 'translateY(-20px)';
        this.stepIndicator.style.transition = 'all 0.3s ease-out';
        
        setTimeout(() => {
            this.stepIndicator.style.opacity = '1';
            this.stepIndicator.style.transform = 'translateY(0)';
        }, 10);
        
        return this;
    }
    
    /**
     * Hide the mouse indicator
     */
    hideMouseIndicator() {
        this.mouseIndicator.style.display = 'none';
        if (this.options.showCoordinates) {
            this.coordinatesDisplay.style.display = 'none';
        }
        return this;
    }
    
    /**
     * Hide the keyboard indicator
     */
    hideKeyboardIndicator() {
        this.keyboardIndicator.style.display = 'none';
        return this;
    }
    
    /**
     * Hide the step indicator
     */
    hideStepIndicator() {
        // Animate out
        this.stepIndicator.style.opacity = '0';
        this.stepIndicator.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            this.stepIndicator.style.display = 'none';
        }, 300);
        
        return this;
    }
}

// Make available globally
window.DryRunOverlay = DryRunOverlay;