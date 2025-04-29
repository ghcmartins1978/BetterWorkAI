const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const waitOn = require('wait-on');
const { PythonShell } = require('python-shell');
const fs = require('fs');

// Keep a global reference of the window object to avoid garbage collection
let mainWindow;
let flaskProcess;
let rustHelperProcess;

// Flask server port
const FLASK_PORT = 5000;
const FLASK_URL = `http://localhost:${FLASK_PORT}`;

// Rust helper port
const RUST_HELPER_PORT = 17400;
const RUST_HELPER_URL = `http://localhost:${RUST_HELPER_PORT}`;

// Create the main application window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false, // For security
      contextIsolation: true, // For security
      preload: path.join(__dirname, 'preload.js') // For secure IPC
    },
    icon: path.join(__dirname, 'generated-icon.png')
  });

  // Load the Flask app URL when ready
  mainWindow.loadURL(FLASK_URL);

  // Open DevTools in development mode
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Start the Flask server as a child process
function startFlaskServer() {
  console.log('Starting Flask server...');
  
  // Set environment variables for Flask
  const env = { 
    ...process.env,
    FLASK_APP: 'main.py',
    FLASK_ENV: 'production',
    DATABASE_URL: process.env.DATABASE_URL || 'sqlite:///data/betterman.db',
    AUTOMATION_SERVER_URL: RUST_HELPER_URL,
  };

  // Use python or pythonw depending on platform
  const pythonExecutable = process.platform === 'win32' ? 'pythonw' : 'python';
  
  // Start Flask with gunicorn (or directly with Flask for Windows)
  if (process.platform === 'win32') {
    flaskProcess = spawn(pythonExecutable, [
      '-m', 'flask', 'run', 
      '--host=127.0.0.1', 
      `--port=${FLASK_PORT}`
    ], { env, shell: true });
  } else {
    flaskProcess = spawn('gunicorn', [
      '--bind', `127.0.0.1:${FLASK_PORT}`,
      '--reuse-port', 
      '--reload',
      'main:app'
    ], { env, shell: true });
  }

  flaskProcess.stdout.on('data', (data) => {
    console.log(`Flask: ${data}`);
  });

  flaskProcess.stderr.on('data', (data) => {
    console.error(`Flask error: ${data}`);
  });

  flaskProcess.on('close', (code) => {
    console.log(`Flask server process exited with code ${code}`);
  });
}

// Start the Rust helper process
function startRustHelper() {
  console.log('Starting Rust helper...');
  
  // Get the appropriate binary based on platform
  let helperPath;
  
  if (process.platform === 'win32') {
    helperPath = path.join(__dirname, 'rust_helper', 'betterman_helper.exe');
  } else if (process.platform === 'darwin') {
    helperPath = path.join(__dirname, 'rust_helper', 'betterman_helper');
  } else {
    // Linux
    helperPath = path.join(__dirname, 'rust_helper', 'betterman_helper');
  }
  
  // Check if helper exists
  if (!fs.existsSync(helperPath)) {
    console.error(`Rust helper not found at ${helperPath}`);
    return;
  }
  
  // Make sure the helper is executable on macOS/Linux
  if (process.platform !== 'win32') {
    try {
      fs.chmodSync(helperPath, '755');
    } catch (err) {
      console.error(`Failed to make helper executable: ${err}`);
    }
  }
  
  // Start the helper
  rustHelperProcess = spawn(helperPath, [], { shell: true });
  
  rustHelperProcess.stdout.on('data', (data) => {
    console.log(`Rust helper: ${data}`);
  });
  
  rustHelperProcess.stderr.on('data', (data) => {
    console.error(`Rust helper error: ${data}`);
  });
  
  rustHelperProcess.on('close', (code) => {
    console.log(`Rust helper process exited with code ${code}`);
  });
}

// Quit when all windows are closed
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// Initialize the app
app.on('ready', async () => {
  // Start the Flask server
  startFlaskServer();
  
  // Start the Rust helper
  startRustHelper();
  
  // Wait for the Flask server to be available
  try {
    await waitOn({ resources: [FLASK_URL], timeout: 30000 });
    console.log('Flask server is running');
    createWindow();
  } catch (err) {
    console.error('Flask server failed to start:', err);
    app.quit();
  }
});

// Clean up processes when app is closing
app.on('will-quit', () => {
  console.log('Cleaning up processes...');
  
  if (flaskProcess) {
    console.log('Terminating Flask server...');
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', flaskProcess.pid, '/f', '/t']);
    } else {
      flaskProcess.kill('SIGTERM');
    }
  }
  
  if (rustHelperProcess) {
    console.log('Terminating Rust helper...');
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', rustHelperProcess.pid, '/f', '/t']);
    } else {
      rustHelperProcess.kill('SIGTERM');
    }
  }
});

// IPC handlers for communication between renderer and main process
ipcMain.handle('get-app-path', () => app.getAppPath());
ipcMain.handle('get-platform', () => process.platform);