// BettermanAI Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Set up notifications
    setupNotifications();
    
    // Set up charts if they exist on the page
    setupCharts();
});

// CSRF Token handling
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Notification system
function setupNotifications() {
    // Create toast container if it doesn't exist
    if (!document.querySelector('.toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
}

function showNotification(title, message, type = 'info', duration = 5000) {
    const toastContainer = document.querySelector('.toast-container');
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast bg-${type} bg-opacity-10 border-${type} show`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Toast content
    toast.innerHTML = `
        <div class="toast-header bg-${type} bg-opacity-10">
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Attach close button handler
    toast.querySelector('.btn-close').addEventListener('click', function() {
        toast.remove();
    });
    
    // Auto-remove after duration
    setTimeout(() => {
        toast.remove();
    }, duration);
}

// Form validation
function validateForm(form) {
    let valid = true;
    
    // Check required fields
    form.querySelectorAll('[required]').forEach(element => {
        if (!element.value.trim()) {
            element.classList.add('is-invalid');
            valid = false;
        } else {
            element.classList.remove('is-invalid');
        }
    });
    
    return valid;
}

// Utility functions
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds} seconds`;
    } else if (seconds < 3600) {
        return `${Math.floor(seconds / 60)} minutes ${seconds % 60} seconds`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours} hours ${minutes} minutes`;
    }
}

// Chart initialization
function setupCharts() {
    // Activity chart
    const activityChartElem = document.getElementById('activityChart');
    if (activityChartElem) {
        const chartData = JSON.parse(activityChartElem.getAttribute('data-chart'));
        new Chart(activityChartElem, {
            type: 'line',
            data: {
                labels: chartData.map(item => item.hour),
                datasets: [{
                    label: 'Activity',
                    data: chartData.map(item => item.count),
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Event types chart
    const eventTypesChartElem = document.getElementById('eventTypesChart');
    if (eventTypesChartElem) {
        const chartData = JSON.parse(eventTypesChartElem.getAttribute('data-chart'));
        new Chart(eventTypesChartElem, {
            type: 'doughnut',
            data: {
                labels: chartData.labels,
                datasets: [{
                    data: chartData.data,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Pattern status chart
    const patternStatusChartElem = document.getElementById('patternStatusChart');
    if (patternStatusChartElem) {
        const chartData = JSON.parse(patternStatusChartElem.getAttribute('data-chart'));
        new Chart(patternStatusChartElem, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Patterns',
                    data: chartData.data,
                    backgroundColor: [
                        'rgba(220, 53, 69, 0.7)',
                        'rgba(255, 193, 7, 0.7)',
                        'rgba(40, 167, 69, 0.7)',
                        'rgba(108, 117, 125, 0.7)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
}

// Macro recording functions
function startRecording(macroId) {
    // Hide record button and show recording UI
    document.getElementById('recordBtn').classList.add('d-none');
    document.getElementById('recordingUI').classList.remove('d-none');
    
    // Send AJAX request to start recording
    fetch(`/macro/${macroId}/record`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            showNotification('Error', data.error || 'Failed to start recording', 'danger');
            document.getElementById('recordBtn').classList.remove('d-none');
            document.getElementById('recordingUI').classList.add('d-none');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error', 'Failed to start recording', 'danger');
        document.getElementById('recordBtn').classList.remove('d-none');
        document.getElementById('recordingUI').classList.add('d-none');
    });
}

function stopRecording(macroId) {
    // Send AJAX request to stop recording
    fetch(`/macro/${macroId}/stop`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Success', 'Recording stopped and saved', 'success');
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }
        } else {
            showNotification('Error', data.error || 'Failed to stop recording', 'danger');
            document.getElementById('recordBtn').classList.remove('d-none');
            document.getElementById('recordingUI').classList.add('d-none');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error', 'Failed to stop recording', 'danger');
    });
}

// Macro execution
function executeMacro(macroId) {
    // Confirm before executing
    if (!confirm('Are you sure you want to execute this macro? Make sure your windows are positioned correctly.')) {
        return;
    }
    
    showNotification('Executing Macro', 'The automation is now running...', 'info');
    
    // Send AJAX request to execute macro
    fetch(`/macro/${macroId}/execute`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Success', 'Macro executed successfully', 'success');
            // Reload to update execution count
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showNotification('Error', data.error || 'Failed to execute macro', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error', 'Failed to execute macro', 'danger');
    });
}

// Suggestion handling
function handleSuggestionAction(suggestionId, action) {
    // Send AJAX request to accept/reject suggestion
    fetch(`/suggestion/${suggestionId}/action`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `action=${action}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (action === 'accept') {
                showNotification('Suggestion Accepted', 'Automation has been created', 'success');
            } else {
                showNotification('Suggestion Rejected', 'Suggestion has been rejected', 'info');
            }
            
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }
        } else {
            showNotification('Error', data.error || 'Failed to process suggestion', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error', 'Failed to process suggestion', 'danger');
    });
}

// Settings update
function updateSetting(name, value) {
    // Send AJAX request to update setting
    fetch('/settings/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `name=${name}&value=${value}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Settings Updated', 'Your settings have been saved', 'success');
        } else {
            showNotification('Error', data.error || 'Failed to update settings', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error', 'Failed to update settings', 'danger');
    });
}