const { app, BrowserWindow } = require('electron');
const path = require('path');
const http = require('http');
const fs = require('fs');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;
let uiServer;
let uiServerPort = 0;

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2'
};

// Serves the statically-exported Next.js `out/` folder over a real
// http://localhost origin instead of file://, so client-side routing,
// relative asset resolution, and CORS all behave like a normal browser.
function startUiServer(outDir) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let reqPath = decodeURIComponent(req.url.split('?')[0]);
      let filePath = path.join(outDir, reqPath);

      // Directory or no-extension request -> serve index.html (SPA fallback)
      if (!path.extname(filePath)) {
        const asHtml = `${filePath}.html`;
        if (fs.existsSync(asHtml)) {
          filePath = asHtml;
        } else if (fs.existsSync(path.join(filePath, 'index.html'))) {
          filePath = path.join(filePath, 'index.html');
        } else {
          filePath = path.join(outDir, 'index.html');
        }
      }

      fs.readFile(filePath, (err, data) => {
        if (err) {
          // Fallback to index.html so client-side navigation to unknown
          // paths (e.g. a hard refresh on /setup) doesn't 404.
          fs.readFile(path.join(outDir, 'index.html'), (err2, indexData) => {
            if (err2) {
              res.writeHead(404);
              res.end('Not found');
              return;
            }
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(indexData);
          });
          return;
        }
        const ext = path.extname(filePath);
        res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
        res.end(data);
      });
    });

    server.listen(0, '127.0.0.1', () => {
      uiServer = server;
      uiServerPort = server.address().port;
      resolve(uiServerPort);
    });
  });
}

function startBackend() {
  if (app.isPackaged) {
    const backendPath = path.join(process.resourcesPath, 'wage-backend', 'wage-backend');
    backendProcess = spawn(backendPath, [], { cwd: path.dirname(backendPath), stdio: 'inherit' });
  } else {
    const pythonCommand = process.env.WAGE_PYTHON || 'python3';
    backendProcess = spawn(
      pythonCommand,
      ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
      { cwd: path.join(__dirname, 'jobradar-api'), stdio: 'inherit' }
    );
  }

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend process.', err);
  });
}

async function waitForBackendReady(timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;

  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.request(
        { hostname: '127.0.0.1', port: 8000, path: '/health', method: 'GET', timeout: 1000 },
        (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else if (Date.now() < deadline) {
            setTimeout(check, 250);
          } else {
            reject(new Error(`Backend did not become ready within ${timeoutMs}ms`));
          }
        }
      );

      req.on('error', () => {
        if (Date.now() < deadline) {
          setTimeout(check, 250);
        } else {
          reject(new Error(`Backend did not become ready within ${timeoutMs}ms`));
        }
      });

      req.end();
    };

    check();
  });
}

async function createWindow() {
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

  const appPath = app.isPackaged ? app.getAppPath() : __dirname;
  const outDir = path.join(appPath, 'out');

  if (!uiServer) {
    await startUiServer(outDir);
  }

  if (!app.isPackaged) {
    try {
      await waitForBackendReady(10000);
    } catch (err) {
      console.warn('Backend readiness check failed:', err?.message || err);
    }
  }

  mainWindow.loadURL(`http://127.0.0.1:${uiServerPort}/`);
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
  if (uiServer) {
    uiServer.close();
  }
});