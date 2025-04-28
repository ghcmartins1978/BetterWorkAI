/**
 * BettermanAI Sidebar Navigation
 * Handles collapsible sidebar navigation groups with user preference persistence
 */
document.addEventListener('DOMContentLoaded', function() {
    // Toggle submenu when nav group title is clicked
    const navGroupTitles = document.querySelectorAll('.nav-group-title[data-bs-toggle="collapse"]');
    
    navGroupTitles.forEach(title => {
        // Get the submenu ID from the data-bs-target attribute
        const targetId = title.getAttribute('data-bs-target').substring(1);
        const submenu = document.getElementById(targetId);
        
        // Load saved state
        const savedState = localStorage.getItem(`sidebar_${targetId}`) || 'expanded';
        
        // Apply saved state
        if (savedState === 'collapsed') {
            title.classList.add('collapsed');
            submenu.classList.add('collapsed');
        }
        
        // Add click event listener
        title.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Toggle collapsed state
            title.classList.toggle('collapsed');
            submenu.classList.toggle('collapsed');
            
            // Save state to localStorage
            const newState = title.classList.contains('collapsed') ? 'collapsed' : 'expanded';
            localStorage.setItem(`sidebar_${targetId}`, newState);
        });
    });
    
    // Highlight active menu item based on current URL
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    
    navLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        
        // Exact match
        if (linkPath === currentPath) {
            link.classList.add('active');
            
            // Expand parent submenu if it exists
            const parentSubmenu = link.closest('.submenu');
            if (parentSubmenu) {
                parentSubmenu.classList.remove('collapsed');
                
                // Make sure the title is also not collapsed
                const navGroupTitle = document.querySelector(`[data-bs-target="#${parentSubmenu.id}"]`);
                if (navGroupTitle) {
                    navGroupTitle.classList.remove('collapsed');
                }
            }
        }
    });
});