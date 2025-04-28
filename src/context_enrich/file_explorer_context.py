"""
File Explorer context enrichment module for BettermanAI.
Captures file paths from Explorer (Windows), Finder (macOS), or File Managers (Linux).
"""
import logging
import os
import platform
import subprocess
import time
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class FileExplorerContextEnricher:
    """
    Class to capture file explorer context information.
    Uses platform-specific methods to retrieve information about open/selected files.
    """
    
    def __init__(self):
        """Initialize the file explorer context enricher."""
        self.system = platform.system()
        
    def get_active_explorer_windows(self) -> List[Dict[str, str]]:
        """
        Get information about active file explorer windows.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        if self.system == 'Windows':
            windows = self._get_windows_explorer_info()
        elif self.system == 'Darwin':
            windows = self._get_macos_finder_info()
        elif self.system == 'Linux':
            windows = self._get_linux_filemanager_info()
            
        return windows
    
    def _get_windows_explorer_info(self) -> List[Dict[str, str]]:
        """
        Get information about Windows Explorer windows.
        Uses PowerShell to get data from COM objects.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # PowerShell script to get Explorer window paths
            ps_script = """
            Add-Type -AssemblyName Microsoft.VisualBasic
            $windows = [Microsoft.VisualBasic.Interaction]::GetObject("Shell.Application").Windows()
            $explorerWindows = @()
            
            foreach ($window in $windows) {
                try {
                    if ($window.Name -eq "File Explorer") {
                        $info = @{
                            "path" = $window.Document.Folder.Self.Path;
                            "title" = $window.LocationName;
                            "selected" = @();
                        }
                        
                        # Get selected items
                        foreach ($item in $window.Document.SelectedItems()) {
                            $info.selected += $item.Path
                        }
                        
                        $explorerWindows += $info | ConvertTo-Json -Compress
                    }
                } catch {}
            }
            
            $explorerWindows -join "|"
            """
            
            # Execute the PowerShell script
            process = subprocess.Popen(
                ['powershell', '-Command', ps_script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout:
                # Parse JSON results
                import json
                for window_json in stdout.decode('utf-8').strip().split('|'):
                    if window_json:
                        try:
                            window_info = json.loads(window_json)
                            windows.append({
                                'type': 'explorer',
                                'path': window_info.get('path', ''),
                                'title': window_info.get('title', ''),
                                'selected_files': window_info.get('selected', [])
                            })
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse Explorer window JSON: {window_json}")
        except Exception as e:
            logger.error(f"Error getting Windows Explorer info: {e}")
            
        return windows
    
    def _get_macos_finder_info(self) -> List[Dict[str, str]]:
        """
        Get information about macOS Finder windows.
        Uses AppleScript to retrieve window information.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # AppleScript to get Finder window information
            finder_script = """
            tell application "Finder"
                set finderInfo to {}
                
                repeat with w in windows
                    set windowInfo to {path:"", title:"", selected:{}}
                    
                    try
                        set windowInfo's path to POSIX path of (target of w as text)
                        set windowInfo's title to name of w
                        
                        set selectedItems to {}
                        set sel to selection of w
                        repeat with i in sel
                            set selectedItems to selectedItems & (POSIX path of (i as text))
                        end repeat
                        
                        set windowInfo's selected to selectedItems
                        set finderInfo to finderInfo & windowInfo
                    end try
                end repeat
                
                return finderInfo as text
            end tell
            """
            
            # Execute the AppleScript
            process = subprocess.Popen(
                ['osascript', '-e', finder_script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout:
                # Parse the AppleScript result
                import json
                try:
                    result = stdout.decode('utf-8').strip()
                    if result:
                        # Convert AppleScript record format to JSON-like format
                        result = result.replace('{', '[').replace('}', ']')
                        result = result.replace('path:', '"path":').replace('title:', '"title":').replace('selected:', '"selected":')
                        result = json.loads(result)
                        
                        for window in result:
                            windows.append({
                                'type': 'finder',
                                'path': window.get('path', ''),
                                'title': window.get('title', ''),
                                'selected_files': window.get('selected', [])
                            })
                except Exception as e:
                    logger.warning(f"Failed to parse Finder results: {e}")
        except Exception as e:
            logger.error(f"Error getting macOS Finder info: {e}")
            
        return windows
    
    def _get_linux_filemanager_info(self) -> List[Dict[str, str]]:
        """
        Get information about Linux file manager windows.
        Attempts to use DBus or other Linux-specific methods.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # Try different file managers
            
            # 1. Nautilus (GNOME Files)
            if self._is_process_running('nautilus'):
                # Use DBus to communicate with Nautilus
                try:
                    import dbus
                    bus = dbus.SessionBus()
                    obj = bus.get_object('org.gnome.Nautilus', '/org/gnome/Nautilus')
                    nautilus = dbus.Interface(obj, 'org.gnome.Nautilus')
                    
                    # Get active windows
                    active_windows = nautilus.GetActiveWindows()
                    
                    for window_path in active_windows:
                        windows.append({
                            'type': 'nautilus',
                            'path': window_path,
                            'title': os.path.basename(window_path),
                            'selected_files': []  # No easy way to get selected files via DBus
                        })
                except Exception as e:
                    logger.debug(f"Error getting Nautilus info via DBus: {e}")
            
            # 2. Dolphin (KDE)
            if self._is_process_running('dolphin'):
                # Try to use KDE DBus service
                try:
                    import dbus
                    bus = dbus.SessionBus()
                    obj = bus.get_object('org.kde.dolphin', '/dolphin/Dolphin_1')
                    dolphin = dbus.Interface(obj, 'org.kde.dolphin')
                    
                    # Get current URL
                    current_url = dolphin.currentUrl()
                    
                    # Convert KDE URL to path
                    if current_url.startswith('file://'):
                        path = current_url[7:]
                        windows.append({
                            'type': 'dolphin',
                            'path': path,
                            'title': os.path.basename(path),
                            'selected_files': []  # Difficult to get via DBus
                        })
                except Exception as e:
                    logger.debug(f"Error getting Dolphin info via DBus: {e}")
            
            # 3. Fallback: use xdotool to get window titles
            try:
                # Get window titles
                process = subprocess.Popen(
                    ['xdotool', 'search', '--class', '--name', 'nautilus|dolphin|thunar|pcmanfm', 'getwindowname'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()
                
                if process.returncode == 0 and stdout:
                    lines = stdout.decode('utf-8').strip().split('\n')
                    for line in lines:
                        # Try to extract path from window title
                        if line and ' - ' in line:
                            title = line
                            path = line.split(' - ')[-1]
                            
                            # Verify this is a valid path
                            if os.path.exists(path):
                                windows.append({
                                    'type': 'file_manager',
                                    'path': path,
                                    'title': title,
                                    'selected_files': []
                                })
            except Exception as e:
                logger.debug(f"Error getting file manager info via xdotool: {e}")
                
        except Exception as e:
            logger.error(f"Error getting Linux file manager info: {e}")
            
        return windows
    
    def _is_process_running(self, process_name: str) -> bool:
        """
        Check if a process is running.
        
        Args:
            process_name: Name of the process to check
            
        Returns:
            True if process is running, False otherwise
        """
        try:
            # Different commands for different platforms
            if self.system == 'Windows':
                cmd = ['tasklist', '/FI', f"IMAGENAME eq {process_name}.exe"]
            elif self.system in ['Darwin', 'Linux']:
                cmd = ['pgrep', process_name]
                
            # Run the command
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            # Check if process is running
            if self.system == 'Windows':
                return process_name.lower() in stdout.decode('utf-8').lower()
            else:
                return bool(stdout.strip())
        except Exception as e:
            logger.debug(f"Error checking if process {process_name} is running: {e}")
            return False
    
    def get_file_explorer_context(self) -> Dict[str, Union[str, List[str]]]:
        """
        Get file explorer context data.
        
        Returns:
            Dictionary containing file explorer context information
        """
        context = {
            'explorer_path': '',
            'explorer_selected_files': []
        }
        
        # Get window information
        windows = self.get_active_explorer_windows()
        
        # Use information from the most recently active window
        if windows:
            context['explorer_path'] = windows[0].get('path', '')
            context['explorer_selected_files'] = windows[0].get('selected_files', [])
            
        return context

# Standalone test function
def test_file_explorer_context():
    """Test the file explorer context enricher."""
    logging.basicConfig(level=logging.INFO)
    enricher = FileExplorerContextEnricher()
    context = enricher.get_file_explorer_context()
    print("File Explorer Context:")
    print(f"Current Path: {context['explorer_path']}")
    print("Selected Files:")
    for file in context['explorer_selected_files']:
        print(f"  - {file}")

if __name__ == "__main__":
    test_file_explorer_context()