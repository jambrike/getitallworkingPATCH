const electron = require('electron');
const path = require('path');
const { loadEnvFile } = require('./config/loadEnv');
const { speak, preprocessText } = require('./tts');
const { sendPrompt } = require('./companion/client');

loadEnvFile(path.join(__dirname, '..', '..', '.env'));
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
    width: 380,
    height: 270,
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
  overlayWindow.setSize(380, 270, true);
});

ipcMain.on('overlay:input', async (_event, value) => {
  const text = preprocessText(value);

  if (!text) {
    console.log('[overlay input] Empty input ignored.');
    return;
  }

  console.log(`[overlay input] ${text}`);
  resizeForThinking();
  sendOverlayStatus('thinking');

  try {
    const response = await sendPrompt(text, 'overlay');
    const say = preprocessText(response.say || '');

    if (!say) {
      sendOverlayReply('');
      sendOverlayStatus('listening');
      return;
    }

    sendOverlayReply(say);
    resizeForReply(say);
    sendOverlayStatus('speaking');
    await speak(say);
    sendOverlayStatus('listening');
  } catch (error) {
    sendOverlayReply('Something went wrong. Try that again.');
    sendOverlayStatus('error');
    console.error(`[overlay companion] ${error.message || 'Companion request failed.'}`);
  }
});

ipcMain.on('overlay:speak-text', async (_event, value) => {
  const text = preprocessText(value);

  if (!text) {
    console.log('[overlay speak] Empty input ignored.');
    return;
  }

  sendOverlayReply(text);
  resizeForReply(text);
  sendOverlayStatus('speaking');

  try {
    await speak(text);
    sendOverlayStatus('listening');
  } catch (error) {
    sendOverlayStatus('error');
    console.error(`[overlay tts] ${error.message || 'Text-to-speech failed.'}`);
  }
});

function sendOverlayStatus(status) {
  if (!overlayWindow) return;
  overlayWindow.webContents.send('overlay:status', status);
}

function sendOverlayReply(text) {
  if (!overlayWindow) return;
  overlayWindow.webContents.send('overlay:reply', text);
}

function resizeForReply(text) {
  if (!overlayWindow) return;

  const textLength = text.length;
  const targetHeight = Math.min(390, Math.max(310, 280 + Math.ceil(textLength / 75) * 24));
  overlayWindow.setSize(420, targetHeight, true);
}

function resizeForThinking() {
  if (!overlayWindow) return;
  overlayWindow.setSize(410, 310, true);
}
