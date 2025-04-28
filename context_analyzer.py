"""
Context Analyzer - collects and manages context from various modules for automation enhancement
"""

import importlib
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Global cache for context data to avoid constant refreshing
_context_cache = {}
_last_cache_update = 0

def get_current_context(refresh: bool = False, cache_lifetime_seconds: int = 10) -> Dict[str, Any]:
    """
    Get the current context from all enabled context enrichers
    
    Args:
        refresh: Whether to force refreshing the cache
        cache_lifetime_seconds: Lifetime of cached data in seconds
        
    Returns:
        Dictionary containing all context data
    """
    global _context_cache, _last_cache_update
    
    # Use cache if available and not expired, unless forced refresh
    current_time = time.time()
    if not refresh and _context_cache and current_time - _last_cache_update < cache_lifetime_seconds:
        logger.debug("Using cached context data")
        return _context_cache
    
    # Import settings here to avoid circular imports
    try:
        from settings import get_setting, set_setting
    except ImportError:
        # Mock settings for development/testing
        def get_setting(name, default=None):
            return default
        def set_setting(name, value):
            pass
    
    # Check if context enrichment is enabled
    if get_setting('context_enrichment_enabled', 'true').lower() != 'true':
        logger.info("Context enrichment is disabled in settings")
        return {}
    
    # Get cache lifetime from settings
    cache_lifetime = int(get_setting('context_cache_lifetime', '10'))
    
    # Dictionary to store all context data
    context_data = {}
    
    # Load browser context if enabled
    if get_setting('context_enricher_browser_enabled', 'true').lower() == 'true':
        try:
            browser_context = _get_browser_context()
            if browser_context:
                context_data.update(browser_context)
        except Exception as e:
            logger.error(f"Error getting browser context: {e}")
    
    # Load file explorer context if enabled
    if get_setting('context_enricher_explorer_enabled', 'true').lower() == 'true':
        try:
            explorer_context = _get_explorer_context()
            if explorer_context:
                context_data.update(explorer_context)
        except Exception as e:
            logger.error(f"Error getting explorer context: {e}")
    
    # Load office context if enabled
    if get_setting('context_enricher_office_enabled', 'true').lower() == 'true':
        try:
            office_context = _get_office_context()
            if office_context:
                context_data.update(office_context)
        except Exception as e:
            logger.error(f"Error getting office context: {e}")
    
    # Load clipboard context if enabled
    if get_setting('context_enricher_clipboard_enabled', 'true').lower() == 'true':
        try:
            clipboard_context = _get_clipboard_context()
            if clipboard_context:
                context_data.update(clipboard_context)
        except Exception as e:
            logger.error(f"Error getting clipboard context: {e}")
    
    # Update cache
    _context_cache = context_data
    _last_cache_update = current_time
    
    return context_data

def _get_browser_context() -> Dict[str, Any]:
    """
    Get context from browser
    
    Returns:
        Dictionary with browser context data
    """
    # In a real implementation, this would import and use the browser context module
    # For now, return placeholder data
    return {
        'browser_url': 'https://example.com/document',
        'browser_title': 'Example Document - Sample Website',
        'browser_domain': 'example.com'
    }

def _get_explorer_context() -> Dict[str, Any]:
    """
    Get context from file explorer
    
    Returns:
        Dictionary with file explorer context data
    """
    # In a real implementation, this would import and use the file explorer context module
    # For now, return placeholder data
    return {
        'explorer_path': 'C:/Users/username/Documents',
        'explorer_selected_files': ['report.docx', 'data.xlsx', 'presentation.pptx']
    }

def _get_office_context() -> Dict[str, Any]:
    """
    Get context from office applications
    
    Returns:
        Dictionary with office application context data
    """
    # In a real implementation, this would import and use the office context module
    # For now, return placeholder data
    return {
        'office_application': 'Microsoft Word',
        'office_document': 'Annual Report 2025.docx',
        'office_filepath': 'C:/Users/username/Documents/Annual Report 2025.docx',
        'office_details': 'Document with 15 pages, last edited 2 hours ago'
    }

def _get_clipboard_context() -> Dict[str, Any]:
    """
    Get context from clipboard
    
    Returns:
        Dictionary with clipboard context data
    """
    # Get max length from settings
    try:
        from settings import get_setting
    except ImportError:
        # Mock settings for development/testing
        def get_setting(name, default=None):
            return default
    
    # Get max length from settings
    max_length = int(get_setting('clipboard_max_length', '200'))
    
    # In a real implementation, this would import and use the clipboard context module
    # with privacy filtering applied
    # For now, return placeholder data
    clipboard_text = "The quarterly revenue increased by 15% compared to the previous year."
    
    # Truncate if needed
    if len(clipboard_text) > max_length:
        clipboard_text = clipboard_text[:max_length] + "..."
    
    return {
        'clipboard_text': clipboard_text
    }

def summarize_context(context_data: Dict[str, Any]) -> str:
    """
    Create a human-readable summary of the context data
    
    Args:
        context_data: Dictionary containing context data
        
    Returns:
        String with summarized context information
    """
    summary_parts = []
    
    # Browser context
    if 'browser_url' in context_data or 'browser_title' in context_data:
        browser_info = "Browser: "
        if 'browser_title' in context_data:
            browser_info += f"'{context_data['browser_title']}'"
        if 'browser_url' in context_data:
            browser_info += f" ({context_data['browser_url']})"
        summary_parts.append(browser_info)
    
    # File explorer context
    if 'explorer_path' in context_data:
        explorer_info = f"Explorer: {context_data['explorer_path']}"
        if 'explorer_selected_files' in context_data and context_data['explorer_selected_files']:
            file_count = len(context_data['explorer_selected_files'])
            explorer_info += f" ({file_count} files selected)"
        summary_parts.append(explorer_info)
    
    # Office context
    if 'office_application' in context_data and 'office_document' in context_data:
        office_info = f"{context_data['office_application']}: {context_data['office_document']}"
        summary_parts.append(office_info)
    
    # Clipboard context
    if 'clipboard_text' in context_data:
        text = context_data['clipboard_text']
        if len(text) > 50:
            text = text[:47] + "..."
        clipboard_info = f"Clipboard: \"{text}\""
        summary_parts.append(clipboard_info)
    
    # Join all parts
    if summary_parts:
        return " | ".join(summary_parts)
    else:
        return "No context information available"

def enrich_macro_with_context(macro_id: int, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Add context information to a macro
    
    Args:
        macro_id: ID of the macro to enrich
        context_data: Optional context data to use (if None, will fetch current context)
        
    Returns:
        Dictionary with enrichment results
    """
    if context_data is None:
        context_data = get_current_context()
    
    if not context_data:
        return {
            'success': False,
            'message': 'No context data available'
        }
    
    # Import here to avoid circular imports
    from database import session_scope
    from models import MacroContext
    
    try:
        with session_scope() as db:
            # Create a new context record
            ctx = MacroContext(
                macro_id=macro_id,
                context_data=json.dumps(context_data),
                context_summary=summarize_context(context_data)
            )
            db.add(ctx)
            
            return {
                'success': True,
                'message': 'Context added to macro',
                'context_summary': ctx.context_summary
            }
    except Exception as e:
        logger.error(f"Error enriching macro with context: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }