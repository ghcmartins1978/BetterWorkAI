/**
 * KPI Cards Manager - Updates the KPI cards at the bottom of the screen with real-time data
 */
document.addEventListener('DOMContentLoaded', function() {
    // Only run if KPI cards are present on the page
    if (document.getElementById('events-today-count')) {
        // Initial load
        updateKPICards();
        
        // Set up periodic refresh every 30 seconds
        setInterval(updateKPICards, 30000);
    }
});

/**
 * Updates all KPI cards with fresh data from the API
 */
function updateKPICards() {
    fetch('/api/kpi-metrics')
        .then(response => response.json())
        .then(data => {
            // Update each KPI card
            updateKPICard('events-today-count', data.events_today || 0);
            updateKPICard('hours-saved-count', formatHours(data.hours_saved || 0));
            updateKPICard('macros-active-count', data.macros_active || 0);
            updateKPICard('success-rate-percent', formatPercent(data.success_rate || 0));
        })
        .catch(error => {
            console.error('Error updating KPI cards:', error);
        });
}

/**
 * Updates a single KPI card with new data
 */
function updateKPICard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        // Add a subtle animation when value changes
        if (element.textContent !== String(value)) {
            element.classList.add('highlight-change');
            setTimeout(() => {
                element.classList.remove('highlight-change');
            }, 1000);
        }
        element.textContent = value;
    }
}

/**
 * Formats hours with one decimal place
 */
function formatHours(hours) {
    return parseFloat(hours).toFixed(1);
}

/**
 * Formats percent as whole number with % sign
 */
function formatPercent(percent) {
    return Math.round(percent) + '%';
}