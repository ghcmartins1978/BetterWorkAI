/**
 * BettermanAI Electron Application
 * 
 * Main process for the Electron application that packages the Flask web app
 * and Rust helper together.
 */

const { app, BrowserWindow, ipcMain, dialog, shell, Menu, Tray } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');

// Configure logging
log.transports.file.level = 'info';
log.info('App starting...');

// Global references to prevent garbage collection
let mainWindow = null;
let tray = null;
let flaskServer = null;
let rustHelper = null;
let shuttingDown = false;

// Paths and environment variables
const isDevelopment = process.env.NODE_ENV === 'development';
const appRoot = path.join(__dirname, '..');
const pythonScript = path.join(appRoot, 'main.py');
const pythonInterpreter = isDevelopment ? 'python3' : path.join(process.resourcesPath, 'app', 'python', 'python');
const rustHelperPath = isDevelopment ? 
    path.join(appRoot, 'betterman_helper') : 
    path.join(process.resourcesPath, 'app', 'rust_helper', getHelperExecutableName());

// Get the correct executable name for the platform
function getHelperExecutableName() {
    switch(process.platform) {
        case 'win32':
            return 'betterman_helper.exe';
        case 'darwin':
        case 'linux':
            return 'betterman_helper';
        default:
            return 'betterman_helper';
    }
}

// Start the Flask server
function startFlaskServer() {
    log.info('Starting Flask server...');
    
    // Set environment variables
    const env = Object.assign({}, process.env, {
        'RUNNING_IN_ELECTRON': '1',
        'FLASK_ENV': isDevelopment ? 'development' : 'production',
        'PYTHONUNBUFFERED': '1'
    });
    
    // Start Flask with Gunicorn in development, or directly in production
    let args = [];
    
    if (isDevelopment) {
        // In development, use Flask's built-in server
        args = [pythonScript];
    } else {
        // In production, use gunicorn
        args = ['-m', 'gunicorn', '--bind', '127.0.0.1:5000', 'main:app'];
    }
    
    flaskServer = spawn(pythonInterpreter, args, {
        cwd: appRoot,
        env: env
    });
    
    flaskServer.stdout.on('data', (data) => {
        log.info(`Flask stdout: ${data}`);
    });
    
    flaskServer.stderr.on('data', (data) => {
        log.error(`Flask stderr: ${data}`);
    });
    
    flaskServer.on('close', (code) => {
        log.info(`Flask server process exited with code ${code}`);
        if (!shuttingDown) {
            // Attempt to restart if not shutting down
            log.info('Attempting to restart Flask server...');
            setTimeout(startFlaskServer, 1000);
        }
    });
}

// Start the Rust helper
function startRustHelper() {
    log.info('Starting Rust helper...');
    
    // Use the Rust helper in all modes
    // Check for the rust helper binary in development mode
    let helperBinaryPath = '';
    
    if (isDevelopment) {
        // Look in several possible locations for the helper binary
        const possiblePaths = [
            path.join(appRoot, 'electron', 'rust_helper', getHelperExecutableName()),
            path.join(appRoot, 'rust_helper', 'target', 'release', getHelperExecutableName()),
            path.join(__dirname, 'rust_helper', getHelperExecutableName()),
            rustHelperPath
        ];
        
        for (const tryPath of possiblePaths) {
            if (fs.existsSync(tryPath)) {
                helperBinaryPath = tryPath;
                log.info(`Found Rust helper at ${helperBinaryPath}`);
                break;
            }
        }
        
        // If not found, use the Python implementation as fallback
        if (!helperBinaryPath) {
            const pyHelperPath = path.join(appRoot, 'rust_helper.py');
            if (fs.existsSync(pyHelperPath)) {
                log.info(`Using Python helper implementation at ${pyHelperPath}`);
                
                // Start the Python implementation 
                const env = Object.assign({}, process.env);
                
                rustHelper = spawn('python', [pyHelperPath], {
                    cwd: appRoot,
                    env: env
                });
                
                rustHelper.stdout.on('data', (data) => {
                    const dataStr = data.toString();
                    log.info(`Python helper stdout: ${dataStr}`);
                });
                
                rustHelper.stderr.on('data', (data) => {
                    log.error(`Python helper stderr: ${data}`);
                });
                
                rustHelper.on('close', (code) => {
                    log.info(`Python helper process exited with code ${code}`);
                    if (!shuttingDown) {
                        log.info('Attempting to restart Python helper...');
                        setTimeout(startRustHelper, 1000);
                    }
                });
                
                // Set the automation server URL environment variable
                process.env.AUTOMATION_SERVER_URL = 'http://127.0.0.1:17400';
                return;
            }
            
            // If no helper implementation found, show error
            log.error('No Rust helper or Python fallback found');
            dialog.showErrorBox(
                'Error Starting BettermanAI',
                'Could not find the helper application. The application may not function correctly.'
            );
            return;
        }
    } else {
        // In production mode, use the path defined above
        helperBinaryPath = rustHelperPath;
    }
    
    log.info(`Using Rust helper at: ${helperBinaryPath}`);
    
    // Check if Rust helper exists
    if (!fs.existsSync(helperBinaryPath)) {
        log.error(`Rust helper not found at ${helperBinaryPath}`);
        dialog.showErrorBox(
            'Error Starting BettermanAI',
            `Could not find the helper application at ${helperBinaryPath}. The application may not function correctly.`
        );
        return;
    }
    
    // Make sure the helper is executable (for macOS and Linux)
    if (process.platform !== 'win32') {
        try {
            fs.chmodSync(helperBinaryPath, '755');
        } catch (err) {
            log.error(`Error making Rust helper executable: ${err}`);
        }
    }
    
    // Start the helper
    const env = Object.assign({}, process.env, {
        'RUST_LOG': isDevelopment ? 'debug' : 'info'
    });
    
    rustHelper = spawn(helperBinaryPath, [], {
        cwd: appRoot,
        env: env
    });
    
    rustHelper.stdout.on('data', (data) => {
        log.info(`Rust helper stdout: ${data}`);
    });
    
    rustHelper.stderr.on('data', (data) => {
        log.error(`Rust helper stderr: ${data}`);
    });
    
    rustHelper.on('close', (code) => {
        log.info(`Rust helper process exited with code ${code}`);
        if (!shuttingDown) {
            // Attempt to restart if not shutting down
            log.info('Attempting to restart Rust helper...');
            setTimeout(startRustHelper, 1000);
        }
    });
}

// Create the main application window
function createMainWindow() {
    log.info('Creating main window...');
    
    const windowConfig = {
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            spellcheck: true
        },
        icon: path.join(appRoot, 'generated-icon.png'),
        show: false // Don't show the window until it's ready
    };
    
    mainWindow = new BrowserWindow(windowConfig);
    
    // Load the Flask app URL
    const appUrl = isDevelopment ? 
        'http://localhost:5000' : 
        'http://127.0.0.1:5000';
    
    // Set a timeout to load the app (give Flask time to start)
    setTimeout(() => {
        log.info(`Loading URL: ${appUrl}`);
        mainWindow.loadURL(appUrl);
    }, 2000);
    
    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });
    
    // Handle window closed
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
    
    // Open external links in browser
    mainWindow.webContents.on('will-navigate', (event, url) => {
        if (!url.startsWith('http://localhost:5000') && !url.startsWith('http://127.0.0.1:5000')) {
            event.preventDefault();
            shell.openExternal(url);
        }
    });
    
    return mainWindow;
}

// Create system tray icon
function createTray() {
    log.info('Creating tray icon...');
    
    const iconPath = path.join(appRoot, 'generated-icon.png');
    tray = new Tray(iconPath);
    
    const contextMenu = Menu.buildFromTemplate([
        { 
            label: 'Open BettermanAI', 
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                } else {
                    createMainWindow();
                }
            } 
        },
        { type: 'separator' },
        { 
            label: 'Check for Updates', 
            click: () => {
                autoUpdater.checkForUpdatesAndNotify();
            } 
        },
        { type: 'separator' },
        { 
            label: 'Quit', 
            click: () => {
                shuttingDown = true;
                app.quit();
            }
        }
    ]);
    
    tray.setToolTip('BettermanAI');
    tray.setContextMenu(contextMenu);
    
    tray.on('click', () => {
        if (mainWindow) {
            mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
        } else {
            createMainWindow();
        }
    });
}

// Check for updates
function checkForUpdates() {
    if (!isDevelopment) {
        log.info('Checking for updates...');
        autoUpdater.checkForUpdatesAndNotify();
    }
}

// Handle auto-updater events
autoUpdater.on('checking-for-update', () => {
    log.info('Checking for update...');
});

autoUpdater.on('update-available', (info) => {
    log.info('Update available:', info);
    dialog.showMessageBox({
        type: 'info',
        title: 'Update Available',
        message: 'A new version of BettermanAI is available. It will be downloaded in the background and installed when you restart the application.',
        buttons: ['OK']
    });
});

autoUpdater.on('update-not-available', () => {
    log.info('Update not available');
});

autoUpdater.on('error', (err) => {
    log.error('Error in auto-updater:', err);
});

autoUpdater.on('download-progress', (progressObj) => {
    let log_message = `Download speed: ${progressObj.bytesPerSecond}`;
    log_message = `${log_message} - Downloaded ${progressObj.percent}%`;
    log_message = `${log_message} (${progressObj.transferred}/${progressObj.total})`;
    log.info(log_message);
});

autoUpdater.on('update-downloaded', (info) => {
    log.info('Update downloaded:', info);
    dialog.showMessageBox({
        type: 'info',
        title: 'Update Ready',
        message: 'A new version of BettermanAI has been downloaded. Restart the application to apply the updates.',
        buttons: ['Restart', 'Later']
    }).then((returnValue) => {
        if (returnValue.response === 0) {
            autoUpdater.quitAndInstall();
        }
    });
});

// App event handlers
app.on('ready', () => {
    log.info('App ready');
    
    // Start the Flask server and Rust helper
    startFlaskServer();
    startRustHelper();
    
    // Create the main window
    createMainWindow();
    
    // Create system tray icon
    createTray();
    
    // Check for updates
    setTimeout(checkForUpdates, 5000);
});

app.on('window-all-closed', () => {
    log.info('All windows closed');
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    log.info('App activated');
    if (mainWindow === null) {
        createMainWindow();
    }
});

app.on('before-quit', () => {
    log.info('App before-quit');
    shuttingDown = true;
    
    // Kill child processes
    if (flaskServer) {
        log.info('Killing Flask server...');
        flaskServer.kill();
    }
    
    if (rustHelper) {
        log.info('Killing Rust helper...');
        rustHelper.kill();
    }
});

// IPC handlers
ipcMain.handle('get-version', () => {
    return app.getVersion();
});

ipcMain.handle('get-app-path', () => {
    return app.getAppPath();
});

ipcMain.handle('show-open-dialog', async (event, options) => {
    const result = await dialog.showOpenDialog(options);
    return result.filePaths;
});

ipcMain.handle('show-save-dialog', async (event, options) => {
    const result = await dialog.showSaveDialog(options);
    return result.filePath;
});