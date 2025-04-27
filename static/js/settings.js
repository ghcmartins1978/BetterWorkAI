/**
 * JavaScript for the settings page.
 * Handles saving settings and UI interactions.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings UI
    initSettingsUI();
    
    // Set up form handlers
    setupFormHandlers();
});

/**
 * Initialize the settings UI elements.
 */
function initSettingsUI() {
    // Toggle visibility of variable prompt timeout setting based on checkbox
    const promptRequiredVariablesCheckbox = document.getElementById('promptRequiredVariables');
    const variablePromptTimeoutGroup = document.getElementById('variablePromptTimeout').parentNode;
    
    if (promptRequiredVariablesCheckbox) {
        promptRequiredVariablesCheckbox.addEventListener('change', function() {
            variablePromptTimeoutGroup.style.display = this.checked ? 'block' : 'none';
        });
        
        // Initial state
        variablePromptTimeoutGroup.style.display = promptRequiredVariablesCheckbox.checked ? 'block' : 'none';
    }
    
    // Toggle AI settings sections based on selected engine
    const aiEngineSelect = document.getElementById('aiEngine');
    const openaiSettingsDiv = document.getElementById('openaiSettingsDiv');
    const localLlmSettingsDiv = document.getElementById('localLlmSettingsDiv');
    
    if (aiEngineSelect) {
        aiEngineSelect.addEventListener('change', function() {
            openaiSettingsDiv.style.display = this.value === 'openai' ? 'block' : 'none';
            localLlmSettingsDiv.style.display = this.value === 'local' ? 'block' : 'none';
        });
    }
    
    // Toggle scheduled hours div based on monitoring mode
    const monitoringModeSelect = document.getElementById('monitoringMode');
    const scheduledHoursDiv = document.getElementById('scheduledHoursDiv');
    
    if (monitoringModeSelect) {
        monitoringModeSelect.addEventListener('change', function() {
            scheduledHoursDiv.style.display = this.value === 'scheduled' ? 'block' : 'none';
        });
    }
}

/**
 * Set up form submission handlers for all settings forms.
 */
function setupFormHandlers() {
    // General settings form
    setupFormSubmitHandler('generalSettingsForm');
    
    // Connection settings form
    setupFormSubmitHandler('connectionSettingsForm');
    
    // Automation settings form
    setupFormSubmitHandler('automationSettingsForm');
    
    // AI settings form
    setupFormSubmitHandler('aiSettingsForm');
    
    // Data settings form
    setupFormSubmitHandler('dataSettingsForm');
    
    // Set up test connection button
    const testConnectionButton = document.getElementById('testConnection');
    if (testConnectionButton) {
        testConnectionButton.addEventListener('click', testConnection);
    }
}

/**
 * Set up a form submission handler for the given form ID.
 * This converts form data to settings key-value pairs and submits them to the server.
 * 
 * @param {string} formId - The ID of the form element
 */
function setupFormSubmitHandler(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);
        const settings = {};
        
        // Convert form data to settings object
        for (const [name, value] of formData.entries()) {
            settings[name] = value;
        }
        
        // Add checkbox fields that might be unchecked (and thus not in the form data)
        for (const checkbox of form.querySelectorAll('input[type="checkbox"]')) {
            if (!formData.has(checkbox.name)) {
                settings[checkbox.name] = 'false';
            }
        }
        
        // Save all settings
        const savePromises = Object.entries(settings).map(([name, value]) => {
            return saveSetting(name, value);
        });
        
        Promise.all(savePromises)
            .then(() => {
                showToast('Settings saved successfully');
            })
            .catch(error => {
                showToast('Error saving settings: ' + error, 'error');
            });
    });
}

/**
 * Save a single setting to the server.
 * 
 * @param {string} name - Setting name
 * @param {string} value - Setting value
 * @returns {Promise} - Promise that resolves when the setting is saved
 */
function saveSetting(name, value) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('value', value);
        
        fetch('/settings/update', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resolve();
            } else {
                reject(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            reject(error);
        });
    });
}

/**
 * Test the connection to the automation server.
 */
function testConnection() {
    const serverUrl = document.getElementById('automationServerUrl').value;
    const connectionStatus = document.getElementById('connectionStatus');
    
    if (!serverUrl) {
        connectionStatus.innerHTML = `
            <div class="alert alert-warning d-flex align-items-center" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <div>Please enter a server URL to test</div>
            </div>
        `;
        connectionStatus.style.display = 'block';
        return;
    }
    
    // Show loading state
    connectionStatus.innerHTML = `
        <div class="alert alert-info d-flex align-items-center" role="alert">
            <div class="spinner-border spinner-border-sm me-2" role="status">
                <span class="visually-hidden">Testing connection...</span>
            </div>
            <div>Testing connection...</div>
        </div>
    `;
    connectionStatus.style.display = 'block';
    
    // Save the URL first
    saveSetting('automation_server_url', serverUrl)
        .then(() => {
            // Now test the connection
            return fetch('/test_connection');
        })
        .then(response => response.json())
        .then(data => {
            if (data.connected) {
                connectionStatus.innerHTML = `
                    <div class="alert alert-success d-flex align-items-center" role="alert">
                        <i class="bi bi-check-circle-fill me-2"></i>
                        <div>
                            Successfully connected to automation server
                            <small class="d-block text-muted">Screen size: ${data.screen_size.width}x${data.screen_size.height}</small>
                        </div>
                    </div>
                `;
                
                // Update the current connection status display
                const currentConnectionStatus = document.getElementById('currentConnectionStatus');
                if (currentConnectionStatus) {
                    currentConnectionStatus.innerHTML = connectionStatus.innerHTML;
                }
            } else {
                connectionStatus.innerHTML = `
                    <div class="alert alert-danger d-flex align-items-center" role="alert">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        <div>
                            Failed to connect to automation server
                            <small class="d-block">${data.error || 'Unknown error'}</small>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            connectionStatus.innerHTML = `
                <div class="alert alert-danger d-flex align-items-center" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <div>
                        Error testing connection
                        <small class="d-block">${error}</small>
                    </div>
                </div>
            `;
        });
}

/**
 * Show a toast notification.
 * 
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, warning, info)
 */
function showToast(message, type = 'success') {
    // Check if toast container exists, create if not
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.classList.add('toast-container', 'position-fixed', 'bottom-0', 'end-0', 'p-3');
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'error' ? 'bg-danger' : 
                   type === 'warning' ? 'bg-warning' : 
                   type === 'info' ? 'bg-info' : 'bg-success';
    
    const toastHtml = `
        <div id="${toastId}" class="toast ${bgClass} text-white" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">BettermanAI</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}