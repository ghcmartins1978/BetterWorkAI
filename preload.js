const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'electron', {
    getAppPath: () => ipcRenderer.invoke('get-app-path'),
    getPlatform: () => process.platform,
    reloadApp: () => ipcRenderer.invoke('reload-app'),
    goBack: () => ipcRenderer.invoke('go-back'),
    goForward: () => ipcRenderer.invoke('go-forward'),
    openDevTools: () => ipcRenderer.invoke('open-dev-tools'),
    checkDatabaseConnection: () => ipcRenderer.invoke('check-database-connection'),
    platform: process.platform
  }
);