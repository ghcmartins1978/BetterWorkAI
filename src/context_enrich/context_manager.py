"""
Context Manager for BettermanAI.
Coordinates the various context enrichment modules and provides a unified context interface.
"""
import logging
import threading
import time
from typing import Dict, List, Optional, Any

from src.context_enrich.browser_context import BrowserContextEnricher
from src.context_enrich.file_explorer_context import FileExplorerContextEnricher
from src.context_enrich.office_context import OfficeContextEnricher
from src.context_enrich.clipboard_context import ClipboardContextEnricher

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Class to manage and coordinate context enrichment.
    Provides a unified interface to access all types of context information.
    """
    
    def __init__(self, settings=None):
        """
        Initialize the context manager.
        
        Args:
            settings: Optional application settings object
        """
        self.settings = settings
        self.context_cache = {}
        self.cache_timestamp = 0
        self.cache_lifetime = 10  # Cache lifetime in seconds
        self.enrichers = {}
        self.lock = threading.Lock()
        
        # Initialize enrichers
        self._init_enrichers()
        
    def _init_enrichers(self):
        """Initialize all context enrichers."""
        try:
            self.enrichers['browser'] = BrowserContextEnricher()
            self.enrichers['explorer'] = FileExplorerContextEnricher()
            self.enrichers['office'] = OfficeContextEnricher()
            self.enrichers['clipboard'] = ClipboardContextEnricher(max_length=200)
            logger.info("Context enrichers initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing context enrichers: {e}")
    
    def is_enricher_enabled(self, enricher_name: str) -> bool:
        """
        Check if a specific enricher is enabled in settings.
        
        Args:
            enricher_name: Name of the enricher to check
            
        Returns:
            True if enricher is enabled, False otherwise
        """
        if not self.settings:
            # Default to enabled if no settings object
            return True
            
        setting_name = f"context_enricher_{enricher_name}_enabled"
        return self.settings.get_setting(setting_name, default=True)
    
    def refresh_context(self, force: bool = False) -> Dict[str, Any]:
        """
        Refresh the context information.
        
        Args:
            force: Force refresh even if cache is valid
            
        Returns:
            Dictionary containing all context information
        """
        current_time = time.time()
        
        # Check if cache is still valid
        if not force and self.cache_timestamp > 0:
            if current_time - self.cache_timestamp < self.cache_lifetime:
                return self.context_cache
        
        # Lock to prevent concurrent updates
        with self.lock:
            # Initialize new context
            context = {
                'timestamp': current_time,
                'context_source': 'BettermanAI Context Manager'
            }
            
            # Collect context from each enabled enricher
            if self.is_enricher_enabled('browser'):
                try:
                    browser_context = self.enrichers['browser'].get_browser_context_data()
                    context.update(browser_context)
                except Exception as e:
                    logger.error(f"Error getting browser context: {e}")
            
            if self.is_enricher_enabled('explorer'):
                try:
                    explorer_context = self.enrichers['explorer'].get_file_explorer_context()
                    context.update(explorer_context)
                except Exception as e:
                    logger.error(f"Error getting file explorer context: {e}")
            
            if self.is_enricher_enabled('office'):
                try:
                    office_context = self.enrichers['office'].get_office_context()
                    context.update(office_context)
                except Exception as e:
                    logger.error(f"Error getting office context: {e}")
            
            if self.is_enricher_enabled('clipboard'):
                try:
                    clipboard_context = self.enrichers['clipboard'].get_clipboard_context()
                    context.update(clipboard_context)
                except Exception as e:
                    logger.error(f"Error getting clipboard context: {e}")
            
            # Update cache
            self.context_cache = context
            self.cache_timestamp = current_time
            
            return context
    
    def get_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get the current context information.
        
        Args:
            force_refresh: Force context refresh
            
        Returns:
            Dictionary containing all context information
        """
        return self.refresh_context(force=force_refresh)
    
    def get_context_summary(self) -> str:
        """
        Get a human-readable summary of the current context.
        
        Returns:
            String containing a summary of the current context
        """
        context = self.get_context()
        summary_lines = ["Context Summary:"]
        
        # Browser context
        if context.get('browser_url'):
            summary_lines.append(f"Browser: {context['browser_title']} ({context['browser_domain']})")
        
        # File explorer context
        if context.get('explorer_path'):
            summary_lines.append(f"Explorer: {context['explorer_path']}")
            if context.get('explorer_selected_files'):
                files = ", ".join([f.split('/')[-1] for f in context['explorer_selected_files']])
                summary_lines.append(f"Selected: {files}")
        
        # Office context
        if context.get('office_application'):
            summary_lines.append(
                f"Office: {context['office_application']} - {context['office_document']}"
            )
            if context.get('office_details'):
                summary_lines.append(f"Details: {context['office_details']}")
        
        # Clipboard context
        if context.get('clipboard_text'):
            clipboard_preview = context['clipboard_text']
            if len(clipboard_preview) > 50:
                clipboard_preview = clipboard_preview[:47] + "..."
            summary_lines.append(f"Clipboard: {clipboard_preview}")
        
        return "\n".join(summary_lines)

# Standalone test function
def test_context_manager():
    """Test the context manager."""
    logging.basicConfig(level=logging.INFO)
    manager = ContextManager()
    
    print("Getting context information...")
    context = manager.get_context()
    
    print("\nContext Summary:")
    print(manager.get_context_summary())
    
    print("\nRaw Context Data:")
    for key, value in context.items():
        # Skip timestamp and source
        if key in ['timestamp', 'context_source']:
            continue
        
        # Truncate long values
        if isinstance(value, str) and len(value) > 100:
            value = value[:97] + "..."
        elif isinstance(value, list) and len(value) > 3:
            value = value[:3] + ["..."]
            
        print(f"{key}: {value}")

if __name__ == "__main__":
    test_context_manager()