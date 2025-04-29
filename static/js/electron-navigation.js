/**
 * BettermanAI Electron Navigation Integration
 * This script provides enhanced navigation controls for Electron mode
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if running in Electron
    const isElectron = typeof window !== 'undefined' && 
                      typeof window.electron !== 'undefined';
    
    if (!isElectron) {
        console.log('Not running in Electron mode, navigation enhancements disabled');
        return;
    }
    
    console.log('Initializing Electron navigation enhancements');
    
    // Add navigation buttons to the header if they don't exist
    const navbar = document.querySelector('.navbar-nav');
    if (navbar) {
        // Create navigation controls container
        const navControls = document.createElement('li');
        navControls.className = 'nav-item d-flex me-2';
        
        // Back button
        const backBtn = document.createElement('button');
        backBtn.className = 'btn btn-sm btn-outline-secondary me-1';
        backBtn.innerHTML = '<i class="bi bi-arrow-left"></i>';
        backBtn.id = 'electron-back-btn';
        backBtn.title = 'Go Back';
        backBtn.onclick = function() {
            window.electron.goBack();
        };
        
        // Forward button
        const forwardBtn = document.createElement('button');
        forwardBtn.className = 'btn btn-sm btn-outline-secondary me-1';
        forwardBtn.innerHTML = '<i class="bi bi-arrow-right"></i>';
        forwardBtn.id = 'electron-forward-btn';
        forwardBtn.title = 'Go Forward';
        forwardBtn.onclick = function() {
            window.electron.goForward();
        };
        
        // Reload button
        const reloadBtn = document.createElement('button');
        reloadBtn.className = 'btn btn-sm btn-outline-secondary';
        reloadBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
        reloadBtn.id = 'electron-reload-btn';
        reloadBtn.title = 'Reload App';
        reloadBtn.onclick = function() {
            window.electron.reloadApp();
        };
        
        // Append buttons to nav controls
        navControls.appendChild(backBtn);
        navControls.appendChild(forwardBtn);
        navControls.appendChild(reloadBtn);
        
        // Insert at beginning of navbar
        navbar.insertBefore(navControls, navbar.firstChild);
    }
    
    // Add database connection status indicator
    function checkDatabaseConnection() {
        fetch('/healthz')
            .then(response => response.json())
            .then(data => {
                const statusIndicator = document.getElementById('db-status-indicator');
                if (!statusIndicator) return;
                
                if (data.status === 'healthy') {
                    statusIndicator.className = 'badge bg-success';
                    statusIndicator.textContent = 'DB Connected';
                } else {
                    statusIndicator.className = 'badge bg-danger';
                    statusIndicator.textContent = 'DB Error';
                }
            })
            .catch(error => {
                console.error('Error checking database status:', error);
                const statusIndicator = document.getElementById('db-status-indicator');
                if (statusIndicator) {
                    statusIndicator.className = 'badge bg-warning';
                    statusIndicator.textContent = 'DB Unknown';
                }
            });
    }
    
    // Add database status indicator to footer
    const footer = document.querySelector('.footer .container');
    if (footer) {
        const dbStatus = document.createElement('span');
        dbStatus.className = 'ms-2';
        dbStatus.innerHTML = '<span id="db-status-indicator" class="badge bg-secondary">Checking DB...</span>';
        footer.appendChild(dbStatus);
        
        // Check database connection
        checkDatabaseConnection();
        
        // Schedule periodic checks
        setInterval(checkDatabaseConnection, 60000); // Check every minute
    }
    
    // Enhance all forms with confirmation before submission
    document.querySelectorAll('form').forEach(form => {
        // Skip forms with data-no-confirm attribute
        if (form.getAttribute('data-no-confirm')) return;
        
        // Add form submission handler for important actions
        if (form.querySelector('button[type="submit"].btn-danger, button[type="submit"].btn-warning')) {
            form.addEventListener('submit', function(event) {
                const submitBtn = form.querySelector('button[type="submit"]');
                const actionText = submitBtn.textContent.trim();
                
                if (!confirm(`Are you sure you want to ${actionText.toLowerCase()}? This action cannot be undone.`)) {
                    event.preventDefault();
                    return false;
                }
                return true;
            });
        }
    });
    
    // Add error handling for broken image links
    document.querySelectorAll('img').forEach(img => {
        img.onerror = function() {
            this.src = '/static/img/missing-image.svg';
            this.alt = 'Image not found';
        };
    });
});