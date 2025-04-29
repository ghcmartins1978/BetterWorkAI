/**
 * Mock Rust Helper Server
 * 
 * This is a simple Express server that mocks the Rust helper API
 * for development purposes.
 */

// Try loading dependencies, with fallbacks for different installation locations
let express, cors;

try {
    // Try loading from local first
    express = require('express');
    cors = require('cors');
    console.log('Successfully loaded Express and CORS modules from local installation');
} catch (error) {
    // If that fails, try loading from parent directory
    try {
        express = require('../node_modules/express');
        cors = require('../node_modules/cors');
        console.log('Successfully loaded Express and CORS modules from parent directory');
    } catch (innerError) {
        // If that also fails, try loading from global installation
        try {
            // This assumes Node.js can find globally installed modules
            express = require('express');
            cors = require('cors');
            console.log('Successfully loaded Express and CORS modules from global installation');
        } catch (finalError) {
            console.error('Failed to load Express and CORS modules from any location!');
            console.error('Please install them using: npm install express cors');
            console.error('Original error:', error.message);
            process.exit(1);
        }
    }
}

const app = express();
const port = process.env.MOCK_HELPER_PORT || 17402; // Use environment variable or default to 17402

// Enable CORS
app.use(cors());
app.use(express.json());

// Global state for the mock helper
const state = {
  isMonitoring: false,
  events: [],
  windows: [
    { id: 1, title: 'Mock Window 1', app: 'Chrome' },
    { id: 2, title: 'Mock Window 2', app: 'Visual Studio Code' },
    { id: 3, title: 'Mock Window 3', app: 'Terminal' }
  ],
  macros: {},
  executions: {}
};

// API Routes
app.get('/api/status', (req, res) => {
  res.json({
    status: 'ok',
    version: '1.0.0-mock',
    platform: process.platform,
    isMonitoring: state.isMonitoring
  });
});

app.get('/api/windows', (req, res) => {
  res.json(state.windows);
});

app.get('/api/events', (req, res) => {
  const limit = parseInt(req.query.limit) || 100;
  res.json(state.events.slice(0, limit));
});

app.post('/api/start-monitoring', (req, res) => {
  state.isMonitoring = true;
  res.json({ success: true, message: 'Monitoring started' });
});

app.post('/api/stop-monitoring', (req, res) => {
  state.isMonitoring = false;
  res.json({ success: true, message: 'Monitoring stopped' });
});

app.post('/api/execute-macro', (req, res) => {
  const { macro_id, steps, variables } = req.body;
  
  if (!macro_id) {
    return res.status(400).json({ 
      success: false, 
      message: 'Macro ID is required' 
    });
  }
  
  // Generate a unique execution ID
  const execution_id = `exec-${Date.now()}`;
  
  // Save the execution in state
  state.executions[execution_id] = {
    macro_id,
    status: 'running',
    start_time: new Date().toISOString(),
    steps: steps || [],
    variables: variables || {},
    logs: ['Mock execution started']
  };
  
  // Simulate execution completion after a delay
  setTimeout(() => {
    state.executions[execution_id].status = 'success';
    state.executions[execution_id].end_time = new Date().toISOString();
    state.executions[execution_id].logs.push('Mock execution completed successfully');
  }, 3000);
  
  res.json({
    success: true,
    execution_id,
    message: 'Macro execution started'
  });
});

app.get('/api/execution-status/:execution_id', (req, res) => {
  const { execution_id } = req.params;
  
  if (!state.executions[execution_id]) {
    return res.status(404).json({
      success: false,
      message: 'Execution not found'
    });
  }
  
  res.json({
    success: true,
    execution: state.executions[execution_id]
  });
});

app.post('/api/stop-execution/:execution_id', (req, res) => {
  const { execution_id } = req.params;
  
  if (!state.executions[execution_id]) {
    return res.status(404).json({
      success: false,
      message: 'Execution not found'
    });
  }
  
  if (state.executions[execution_id].status === 'running') {
    state.executions[execution_id].status = 'stopped';
    state.executions[execution_id].end_time = new Date().toISOString();
    state.executions[execution_id].logs.push('Execution stopped by user');
  }
  
  res.json({
    success: true,
    message: 'Execution stopped'
  });
});

// Function to try different ports if the main one is in use
function startServer(initialPort) {
  let currentPort = initialPort;
  const maxRetries = 5;
  
  function tryPort(port, retryCount = 0) {
    const server = app.listen(port)
      .on('listening', () => {
        console.log(`Mock Rust helper server running at http://localhost:${port}`);
        // Store the port we're actually using
        process.env.MOCK_HELPER_PORT = port;
      })
      .on('error', (err) => {
        if (err.code === 'EADDRINUSE' && retryCount < maxRetries) {
          console.log(`Port ${port} is in use, trying port ${port + 1}...`);
          server.close();
          // Try the next port
          tryPort(port + 1, retryCount + 1);
        } else if (retryCount >= maxRetries) {
          console.error(`Failed to find an available port after ${maxRetries} attempts.`);
          process.exit(1);
        } else {
          console.error(`Error starting mock helper server: ${err.message}`);
          process.exit(1);
        }
      });
  }
  
  // Try to start on the initial port
  tryPort(currentPort);
}

// Start the server
startServer(port);