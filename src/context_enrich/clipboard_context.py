"""
Clipboard context enrichment module for BettermanAI.
Captures clipboard content with privacy filtering for sensitive information.
"""
import logging
import os
import platform
import re
import subprocess
import time
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class ClipboardContextEnricher:
    """
    Class to capture clipboard content with privacy filtering.
    Retrieves text from the system clipboard and filters out sensitive information.
    """
    
    def __init__(self, max_length=200):
        """
        Initialize the clipboard context enricher.
        
        Args:
            max_length: Maximum length of clipboard text to capture (default: 200)
        """
        self.system = platform.system()
        self.max_length = max_length
        
    def get_clipboard_text(self) -> str:
        """
        Get text from the system clipboard.
        
        Returns:
            String containing clipboard text or empty string if failed
        """
        clipboard_text = ""
        
        try:
            if self.system == 'Windows':
                clipboard_text = self._get_windows_clipboard()
            elif self.system == 'Darwin':
                clipboard_text = self._get_macos_clipboard()
            elif self.system == 'Linux':
                clipboard_text = self._get_linux_clipboard()
                
            # Truncate if too long
            if len(clipboard_text) > self.max_length:
                clipboard_text = clipboard_text[:self.max_length] + "..."
                
        except Exception as e:
            logger.error(f"Error getting clipboard text: {e}")
            
        return clipboard_text
    
    def _get_windows_clipboard(self) -> str:
        """
        Get clipboard contents on Windows.
        
        Returns:
            String containing clipboard text
        """
        try:
            # Use PowerShell to get clipboard
            ps_script = "Get-Clipboard -Format Text"
            
            process = subprocess.Popen(
                ['powershell', '-Command', ps_script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                return stdout.decode('utf-8', errors='replace').strip()
        except Exception as e:
            logger.debug(f"Error getting Windows clipboard: {e}")
            
        return ""
    
    def _get_macos_clipboard(self) -> str:
        """
        Get clipboard contents on macOS.
        
        Returns:
            String containing clipboard text
        """
        try:
            # Use pbpaste to get clipboard
            process = subprocess.Popen(
                ['pbpaste'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                return stdout.decode('utf-8', errors='replace').strip()
        except Exception as e:
            logger.debug(f"Error getting macOS clipboard: {e}")
            
        return ""
    
    def _get_linux_clipboard(self) -> str:
        """
        Get clipboard contents on Linux.
        
        Returns:
            String containing clipboard text
        """
        try:
            # Try xclip first
            try:
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard', '-o'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    return stdout.decode('utf-8', errors='replace').strip()
            except Exception:
                pass
                
            # Try xsel if xclip failed
            try:
                process = subprocess.Popen(
                    ['xsel', '--clipboard', '--output'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    return stdout.decode('utf-8', errors='replace').strip()
            except Exception:
                pass
                
            # Try wl-paste for Wayland
            try:
                process = subprocess.Popen(
                    ['wl-paste'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    return stdout.decode('utf-8', errors='replace').strip()
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Error getting Linux clipboard: {e}")
            
        return ""
    
    def _filter_sensitive_info(self, text: str) -> str:
        """
        Filter out sensitive information from text.
        
        Args:
            text: Text to filter
            
        Returns:
            Filtered text with sensitive information redacted
        """
        if not text:
            return text
            
        filtered_text = text
        
        # Filter email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        filtered_text = re.sub(email_pattern, '[EMAIL]', filtered_text)
        
        # Filter phone numbers (various formats)
        phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
            r'\b\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1 123 456 7890
        ]
        for pattern in phone_patterns:
            filtered_text = re.sub(pattern, '[PHONE]', filtered_text)
        
        # Filter credit card numbers
        cc_pattern = r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        filtered_text = re.sub(cc_pattern, '[CREDIT_CARD]', filtered_text)
        
        # Filter social security numbers
        ssn_pattern = r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
        filtered_text = re.sub(ssn_pattern, '[SSN]', filtered_text)
        
        # Filter API keys and passwords
        api_key_patterns = [
            r'\b(?:api[_-]?key|key|token|secret)[_-]?(?:id)?[\s:=]+[\'"]?([a-zA-Z0-9_\-\.]{20,})[\'"]?',
            r'\b(?:password|passwd)[\s:=]+[\'"]?([^\'"\s]{8,})[\'"]?',
        ]
        for pattern in api_key_patterns:
            filtered_text = re.sub(pattern, r'\1 [REDACTED]', filtered_text, flags=re.IGNORECASE)
        
        return filtered_text
    
    def get_clipboard_context(self) -> Dict[str, str]:
        """
        Get clipboard context with privacy filtering.
        
        Returns:
            Dictionary containing clipboard text
        """
        context = {
            'clipboard_text': ''
        }
        
        # Get raw clipboard text
        raw_text = self.get_clipboard_text()
        
        # Apply privacy filtering
        if raw_text:
            filtered_text = self._filter_sensitive_info(raw_text)
            context['clipboard_text'] = filtered_text
            
        return context

# Standalone test function
def test_clipboard_context():
    """Test the clipboard context enricher."""
    logging.basicConfig(level=logging.INFO)
    enricher = ClipboardContextEnricher(max_length=200)
    
    print("Clipboard Context:")
    
    # Raw clipboard
    raw_text = enricher.get_clipboard_text()
    print(f"Raw clipboard ({len(raw_text)} chars):")
    print(f"  {raw_text}")
    
    # Filtered clipboard
    context = enricher.get_clipboard_context()
    print(f"Filtered clipboard ({len(context['clipboard_text'])} chars):")
    print(f"  {context['clipboard_text']}")

if __name__ == "__main__":
    test_clipboard_context()