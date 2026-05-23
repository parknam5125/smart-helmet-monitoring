const { contextBridge, ipcRenderer } = require('electron')

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getPlatform: () => process.platform,
  
  // Window controls
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  maximizeWindow: () => ipcRenderer.send('maximize-window'),
  closeWindow: () => ipcRenderer.send('close-window'),
  
  // Notifications
  showNotification: (title, body) => ipcRenderer.send('show-notification', { title, body }),
  
  // System tray
  showInTray: () => ipcRenderer.send('show-in-tray'),
  
  // Event listeners
  onHelmetAlert: (callback) => ipcRenderer.on('helmet-alert', callback),
  removeHelmetAlert: () => ipcRenderer.removeAllListeners('helmet-alert')
})

// Log when preload script is loaded
console.log('Electron preload script loaded')
