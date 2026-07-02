const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('overlayControls', {
  close: () => ipcRenderer.send('overlay:close'),
  shrink: () => ipcRenderer.send('overlay:shrink'),
  expand: () => ipcRenderer.send('overlay:expand'),
  printInput: (value) => ipcRenderer.send('overlay:input', value),
  onStatus: (callback) => {
    ipcRenderer.on('overlay:status', (_event, status) => callback(status));
  }
});
