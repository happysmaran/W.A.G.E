const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

function startBackend() {
  const backendPath = app.isPackaged
    ? path.join(process.resourcesPath, 'wage-backend', 'wage-backend')
    : path.join(__dirname, 'jobradar-api', 'dist', 'wage-backend', 'wage-backend');

  // Spawn the PyInstaller compiled executable
  backendProcess = spawn(backendPath, [], {
    detached: false, // ensures child dies if parent is killed
    stdio: 'inherit'
  });

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend process.', err);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'W.A.G.E.',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Next.js static export loads from the local out/ directory
  if (app.isPackaged) {
    mainWindow.loadFile(path.join(process.resourcesPath, 'out', 'index.html'));
  } else {
    // In dev, we might just load the dev server, but for simplicity we load the built static site
    mainWindow.loadFile(path.join(__dirname, 'out', 'index.html'));
  }

  // Handle SPA routing for local files (so refreshing doesn't 404)
  mainWindow.webContents.on('did-fail-load', (e, code, desc, url) => {
    if (url.startsWith('file://')) {
      mainWindow.loadFile(path.join(app.isPackaged ? process.resourcesPath : __dirname, 'out', 'index.html'));
    }
  });
}

app.whenReady().then(() => {
  startBackend();
  
  // Wait a moment for FastAPI to boot before showing the window
  setTimeout(createWindow, 1000);

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Quit when all windows are closed
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// Clean up backend process on exit
app.on('will-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
