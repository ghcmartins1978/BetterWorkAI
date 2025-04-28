/**
 * BettermanAI KPI Cards 
 * Displays key performance indicators for automation metrics
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize and update KPI cards
    updateKPICards();
    
    // Update every 30 seconds
    setInterval(updateKPICards, 30000);
});

/**
 * Update KPI cards with latest data
 */
function updateKPICards() {
    // Find all KPI cards
    const kpiCards = document.querySelectorAll('.kpi-card');
    
    // If no KPI cards found, exit
    if (kpiCards.length === 0) {
        return;
    }
    
    // Fetch KPI metrics from API
    fetch('/api/kpi-metrics')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch KPI metrics');
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.error || 'Unknown error');
            }
            
            // Update each KPI card
            const metrics = data.kpi_metrics;
            
            // Update events today card
            const eventsCard = document.querySelector('.kpi-card[data-metric="events_today"]');
            if (eventsCard) {
                const valueEl = eventsCard.querySelector('.kpi-value');
                if (valueEl) {
                    valueEl.textContent = metrics.events_today.toLocaleString();
                }
            }
            
            // Update hours saved card
            const hoursCard = document.querySelector('.kpi-card[data-metric="hours_saved"]');
            if (hoursCard) {
                const valueEl = hoursCard.querySelector('.kpi-value');
                if (valueEl) {
                    valueEl.textContent = metrics.hours_saved.toLocaleString();
                }
            }
            
            // Update active macros card
            const macrosCard = document.querySelector('.kpi-card[data-metric="macros_active"]');
            if (macrosCard) {
                const valueEl = macrosCard.querySelector('.kpi-value');
                if (valueEl) {
                    valueEl.textContent = metrics.macros_active.toLocaleString();
                }
            }
            
            // Update success rate card
            const successCard = document.querySelector('.kpi-card[data-metric="success_rate"]');
            if (successCard) {
                const valueEl = successCard.querySelector('.kpi-value');
                if (valueEl) {
                    valueEl.textContent = metrics.success_rate.toFixed(1) + '%';
                    
                    // Add color classes based on success rate value
                    if (metrics.success_rate >= 95) {
                        valueEl.className = 'kpi-value text-success';
                    } else if (metrics.success_rate >= 80) {
                        valueEl.className = 'kpi-value text-info';
                    } else if (metrics.success_rate >= 60) {
                        valueEl.className = 'kpi-value text-warning';
                    } else {
                        valueEl.className = 'kpi-value text-danger';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error updating KPI cards:', error);
        });
}