const electron = require('electron');
const path = require('path');
const { loadEnvFile } = require('./config/loadEnv');
const { speak, preprocessText } = require('./tts');

loadEnvFile();

if (!electron.app) {
  console.error('Start this app with "npm start" or "npx electron .", not "node src/main.js".');
  process.exit(1);
}

const { app, BrowserWindow, ipcMain, screen } = electron;

let overlayWindow;

function createOverlayWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: displayWidth } = primaryDisplay.workAreaSize;

  overlayWindow = new BrowserWindow({
    width: 360,
    height: 210,
    x: Math.max(24, displayWidth - 390),
    y: 72,
    type: process.platform === 'darwin' ? 'panel' : undefined,
    frame: false,
    transparent: true,
    resizable: false,
    movable: true,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    hasShadow: false,
    alwaysOnTop: true,
    acceptFirstMouse: true,
    backgroundColor: '#00000000',
    title: 'Helper Overlay',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  overlayWindow.setAlwaysOnTop(true, 'screen-saver');
  overlayWindow.setVisibleOnAllWorkspaces(true, {
    visibleOnFullScreen: true
  });

  if (process.platform === 'darwin') {
    overlayWindow.setWindowButtonVisibility(false);
  }

  overlayWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  if (process.platform === 'darwin') {
    app.dock.hide();
  }

  createOverlayWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createOverlayWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.on('overlay:close', () => {
  app.quit();
});

ipcMain.on('overlay:shrink', () => {
  if (!overlayWindow) return;
  overlayWindow.setSize(172, 132, true);
});

ipcMain.on('overlay:expand', () => {
  if (!overlayWindow) return;
  overlayWindow.setSize(360, 210, true);
});

ipcMain.on('overlay:input', async (_event, value) => {
  const text = preprocessText(value);

  if (!text) {
    console.log('[overlay input] Empty input ignored.');
    return;
  }

  console.log(`[overlay input] ${text}`);

  try {
    await speak(text);
  } catch (error) {
    console.error(`[overlay tts] ${error.message || 'Text-to-speech failed.'}`);
  }
});
