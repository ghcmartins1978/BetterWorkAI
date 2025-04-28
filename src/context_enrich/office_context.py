"""
Office application context enrichment module for BettermanAI.
Captures context from Microsoft Office and similar productivity applications.
"""
import logging
import os
import platform
import subprocess
import time
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class OfficeContextEnricher:
    """
    Class to capture context from Office applications.
    Retrieves active document information from Word, Excel, PowerPoint, etc.
    """
    
    def __init__(self):
        """Initialize the Office context enricher."""
        self.system = platform.system()
        
    def get_active_office_windows(self) -> List[Dict[str, str]]:
        """
        Get information about active Office application windows.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        if self.system == 'Windows':
            windows = self._get_windows_office_info()
        elif self.system == 'Darwin':
            windows = self._get_macos_office_info()
        elif self.system == 'Linux':
            windows = self._get_linux_office_info()
            
        return windows
    
    def _get_windows_office_info(self) -> List[Dict[str, str]]:
        """
        Get information about Windows Office applications.
        Uses PowerShell to interact with Office applications via COM.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # PowerShell script to get Office window information
            ps_script = """
            function Get-WordInfo {
                try {
                    $word = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Word.Application")
                    $docs = @()
                    foreach ($doc in $word.Documents) {
                        $info = @{
                            "application" = "Microsoft Word";
                            "filename" = $doc.Name;
                            "filepath" = $doc.FullName;
                            "title" = $doc.FullName;
                            "active" = ($doc.FullName -eq $word.ActiveDocument.FullName);
                            "selection" = $word.Selection.Text;
                        }
                        $docs += $info | ConvertTo-Json -Compress
                    }
                    return $docs
                } catch {
                    return @()
                }
            }
            
            function Get-ExcelInfo {
                try {
                    $excel = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
                    $books = @()
                    foreach ($book in $excel.Workbooks) {
                        $info = @{
                            "application" = "Microsoft Excel";
                            "filename" = $book.Name;
                            "filepath" = $book.FullName;
                            "title" = $book.FullName;
                            "active" = ($book.FullName -eq $excel.ActiveWorkbook.FullName);
                            "sheet" = $excel.ActiveSheet.Name;
                            "selection" = $excel.Selection.Address;
                        }
                        $books += $info | ConvertTo-Json -Compress
                    }
                    return $books
                } catch {
                    return @()
                }
            }
            
            function Get-PowerPointInfo {
                try {
                    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject("PowerPoint.Application")
                    $presentations = @()
                    foreach ($pres in $ppt.Presentations) {
                        $info = @{
                            "application" = "Microsoft PowerPoint";
                            "filename" = $pres.Name;
                            "filepath" = $pres.FullName;
                            "title" = $pres.FullName;
                            "active" = ($pres.FullName -eq $ppt.ActivePresentation.FullName);
                            "slide" = $ppt.ActiveWindow.View.Slide.SlideIndex;
                        }
                        $presentations += $info | ConvertTo-Json -Compress
                    }
                    return $presentations
                } catch {
                    return @()
                }
            }
            
            $allInfo = @()
            $allInfo += Get-WordInfo
            $allInfo += Get-ExcelInfo
            $allInfo += Get-PowerPointInfo
            
            $allInfo -join "|"
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
                            app_type = window_info.get('application', '').lower()
                            
                            info = {
                                'type': app_type.replace('microsoft ', ''),
                                'filename': window_info.get('filename', ''),
                                'filepath': window_info.get('filepath', ''),
                                'title': window_info.get('title', ''),
                                'active': window_info.get('active', False)
                            }
                            
                            # Add application-specific details
                            if 'excel' in app_type:
                                info['sheet'] = window_info.get('sheet', '')
                                info['selection'] = window_info.get('selection', '')
                            elif 'word' in app_type:
                                info['selection'] = window_info.get('selection', '')
                            elif 'powerpoint' in app_type:
                                info['slide'] = window_info.get('slide', 1)
                                
                            windows.append(info)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse Office window JSON: {window_json}")
        except Exception as e:
            logger.error(f"Error getting Windows Office info: {e}")
            
        return windows
    
    def _get_macos_office_info(self) -> List[Dict[str, str]]:
        """
        Get information about macOS Office applications.
        Uses AppleScript to interact with Office applications.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # AppleScript to get Microsoft Word information
            word_script = """
            tell application "Microsoft Word"
                if it is running then
                    set wordInfo to {}
                    
                    repeat with doc in documents
                        set docInfo to {type:"word", filename:"", filepath:"", title:"", active:false, selection:""}
                        
                        try
                            set docInfo's filename to name of doc
                            set docInfo's filepath to path of doc
                            set docInfo's title to name of doc
                            set docInfo's active to (doc is active document)
                            
                            if doc is active document then
                                set docInfo's selection to content of selection as text
                            end if
                            
                            set wordInfo to wordInfo & docInfo
                        end try
                    end repeat
                    
                    return wordInfo as text
                end if
            end tell
            """
            
            # AppleScript to get Microsoft Excel information
            excel_script = """
            tell application "Microsoft Excel"
                if it is running then
                    set excelInfo to {}
                    
                    repeat with wb in workbooks
                        set wbInfo to {type:"excel", filename:"", filepath:"", title:"", active:false, sheet:"", selection:""}
                        
                        try
                            set wbInfo's filename to name of wb
                            set wbInfo's filepath to path of wb
                            set wbInfo's title to name of wb
                            set wbInfo's active to (wb is active workbook)
                            
                            if wb is active workbook then
                                set wbInfo's sheet to name of active sheet
                                set wbInfo's selection to address of selection
                            end if
                            
                            set excelInfo to excelInfo & wbInfo
                        end try
                    end repeat
                    
                    return excelInfo as text
                end if
            end tell
            """
            
            # AppleScript to get Microsoft PowerPoint information
            powerpoint_script = """
            tell application "Microsoft PowerPoint"
                if it is running then
                    set pptInfo to {}
                    
                    repeat with pres in presentations
                        set presInfo to {type:"powerpoint", filename:"", filepath:"", title:"", active:false, slide:0}
                        
                        try
                            set presInfo's filename to name of pres
                            set presInfo's filepath to path of pres
                            set presInfo's title to name of pres
                            set presInfo's active to (pres is active presentation)
                            
                            if pres is active presentation then
                                set presInfo's slide to slide number of slide of active window
                            end if
                            
                            set pptInfo to pptInfo & presInfo
                        end try
                    end repeat
                    
                    return pptInfo as text
                end if
            end tell
            """
            
            # Execute the AppleScripts and process results
            for script, app_name in [(word_script, "Word"), (excel_script, "Excel"), (powerpoint_script, "PowerPoint")]:
                process = subprocess.Popen(
                    ['osascript', '-e', script],
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
                            result = result.replace('type:', '"type":').replace('filename:', '"filename":')
                            result = result.replace('filepath:', '"filepath":').replace('title:', '"title":')
                            result = result.replace('active:', '"active":').replace('sheet:', '"sheet":')
                            result = result.replace('selection:', '"selection":').replace('slide:', '"slide":')
                            result = json.loads(result)
                            
                            for window in result:
                                windows.append(window)
                    except Exception as e:
                        logger.warning(f"Failed to parse {app_name} results: {e}")
        except Exception as e:
            logger.error(f"Error getting macOS Office info: {e}")
            
        return windows
    
    def _get_linux_office_info(self) -> List[Dict[str, str]]:
        """
        Get information about Office-like applications on Linux.
        Attempts to get information from LibreOffice.
        
        Returns:
            List of dictionaries containing window information
        """
        windows = []
        
        try:
            # Try to use LibreOffice UNO API
            try:
                # Check if LibreOffice is running
                process = subprocess.Popen(
                    ['ps', '-ef'], 
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate()
                
                if 'soffice' in stdout.decode('utf-8'):
                    # Try to get window titles via xdotool
                    process = subprocess.Popen(
                        ['xdotool', 'search', '--class', 'libreoffice', 'getwindowname'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0 and stdout:
                        window_titles = stdout.decode('utf-8').strip().split('\n')
                        
                        for title in window_titles:
                            if not title:
                                continue
                                
                            # Try to determine application type and filename
                            app_type = 'document'
                            filename = title
                            
                            if ' - LibreOffice ' in title:
                                parts = title.split(' - LibreOffice ')
                                filename = parts[0]
                                if len(parts) > 1 and parts[1]:
                                    if 'Calc' in parts[1]:
                                        app_type = 'spreadsheet'
                                    elif 'Writer' in parts[1]:
                                        app_type = 'word'
                                    elif 'Impress' in parts[1]:
                                        app_type = 'presentation'
                            
                            windows.append({
                                'type': app_type,
                                'filename': filename,
                                'filepath': '',  # Can't easily get filepath from window title
                                'title': title,
                                'active': True  # Assume the window is active if it's returned by xdotool
                            })
            except Exception as e:
                logger.debug(f"Error getting LibreOffice info: {e}")
                
        except Exception as e:
            logger.error(f"Error getting Linux Office info: {e}")
            
        return windows
    
    def get_office_context(self) -> Dict[str, str]:
        """
        Get Office application context data.
        
        Returns:
            Dictionary containing Office context information
        """
        context = {
            'office_application': '',
            'office_document': '',
            'office_filepath': '',
            'office_details': ''  # For application-specific details like sheet name, slide number, etc.
        }
        
        # Get window information
        windows = self.get_active_office_windows()
        
        # Use information from the active window, or the first one if none is marked active
        active_window = None
        for window in windows:
            if window.get('active', False):
                active_window = window
                break
                
        if not active_window and windows:
            active_window = windows[0]
            
        if active_window:
            context['office_application'] = active_window.get('type', '')
            context['office_document'] = active_window.get('filename', '')
            context['office_filepath'] = active_window.get('filepath', '')
            
            # Add application-specific details
            details = []
            if 'excel' in active_window.get('type', '').lower():
                if 'sheet' in active_window:
                    details.append(f"Sheet: {active_window['sheet']}")
                if 'selection' in active_window:
                    details.append(f"Selection: {active_window['selection']}")
            elif 'word' in active_window.get('type', '').lower():
                if 'selection' in active_window and active_window['selection']:
                    selection = active_window['selection']
                    # Truncate long selections
                    if len(selection) > 100:
                        selection = selection[:97] + '...'
                    details.append(f"Selection: {selection}")
            elif 'powerpoint' in active_window.get('type', '').lower():
                if 'slide' in active_window:
                    details.append(f"Slide: {active_window['slide']}")
                    
            context['office_details'] = '; '.join(details)
            
        return context

# Standalone test function
def test_office_context():
    """Test the Office context enricher."""
    logging.basicConfig(level=logging.INFO)
    enricher = OfficeContextEnricher()
    context = enricher.get_office_context()
    print("Office Context:")
    print(f"Application: {context['office_application']}")
    print(f"Document: {context['office_document']}")
    print(f"File Path: {context['office_filepath']}")
    print(f"Details: {context['office_details']}")

if __name__ == "__main__":
    test_office_context()