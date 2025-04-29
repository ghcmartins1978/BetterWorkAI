/**
 * Mock Rust Helper Server
 * 
 * This is a simple Express server that mocks the Rust helper API
 * for development purposes.
 */

const express = require('express');
const cors = require('cors');
const app = express();
const port = 17400;

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

// Start the server
app.listen(port, () => {
  console.log(`Mock Rust helper server running at http://localhost:${port}`);
});