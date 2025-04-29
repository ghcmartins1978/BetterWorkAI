/**
 * BettermanAI Electron Application
 * 
 * Preload script that runs in the renderer process.
 * This provides a secure bridge between the renderer process and main process.
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose a limited set of Node.js functionality to the renderer process
contextBridge.exposeInMainWorld('electron', {
    // App information
    getVersion: () => ipcRenderer.invoke('get-version'),
    getAppPath: () => ipcRenderer.invoke('get-app-path'),
    
    // File dialog
    showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),
    showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),
    
    // Environment detection
    isElectron: true,
    
    // Platform detection
    platform: process.platform
});

// Add a class to the document body when it loads
window.addEventListener('DOMContentLoaded', () => {
    // Add a class to body to enable Electron-specific CSS
    document.body.classList.add('electron-app');
    
    // Add platform-specific class
    document.body.classList.add(`platform-${process.platform}`);
    
    // Add a global variable to detect Electron in JavaScript
    const script = document.createElement('script');
    script.textContent = `window.isRunningInElectron = true;`;
    document.head.appendChild(script);
    
    // Handle external links - make them open in the system browser
    document.addEventListener('click', (event) => {
        const element = event.target.closest('a');
        if (element && element.getAttribute('href') && element.getAttribute('href').startsWith('http')) {
            const href = element.getAttribute('href');
            const isInternal = href.startsWith('http://localhost:') || href.startsWith('http://127.0.0.1:');
            
            if (!isInternal) {
                event.preventDefault();
                ipcRenderer.send('open-external', href);
            }
        }
    });
});