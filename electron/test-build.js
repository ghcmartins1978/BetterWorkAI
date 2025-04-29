/**
 * Test script for electron build process.
 * This script verifies that all dependencies and configurations 
 * are properly set up before initiating a full build.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Paths
const rootDir = path.join(__dirname, '..');
const electronDir = __dirname;
const pythonReqPath = path.join(electronDir, 'requirements.txt');
const rustHelperDir = path.join(electronDir, 'rust_helper');

// Platform-specific settings
const isWin = process.platform === 'win32';
const isMac = process.platform === 'darwin';
const isLinux = process.platform === 'linux';
const platformName = isWin ? 'Windows' : (isMac ? 'macOS' : 'Linux');

// Terminal colors
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    dim: '\x1b[2m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m'
};

// Helper functions
function log(message, color = colors.reset) {
    console.log(`${color}${message}${colors.reset}`);
}

function executeCommand(command, silent = false) {
    try {
        const options = silent ? { stdio: 'pipe' } : { stdio: 'inherit' };
        const output = execSync(command, options);
        return { success: true, output: output ? output.toString() : '' };
    } catch (error) {
        return { 
            success: false, 
            error: error,
            output: error.stdout ? error.stdout.toString() : '',
            stderr: error.stderr ? error.stderr.toString() : ''
        };
    }
}

function checkPythonVersion() {
    log('Checking Python version...', colors.cyan);
    
    const pythonCmd = isWin ? 'python --version' : 'python3 --version';
    const result = executeCommand(pythonCmd, true);
    
    if (result.success) {
        const versionMatch = result.output.match(/Python (\d+\.\d+\.\d+)/);
        if (versionMatch) {
            const version = versionMatch[1];
            log(`  ✓ Python ${version} found`, colors.green);
            return { success: true, version };
        }
    }
    
    log(`  ✗ Python not found or error executing command`, colors.red);
    return { success: false };
}

function checkNodeVersion() {
    log('Checking Node.js version...', colors.cyan);
    
    const result = executeCommand('node --version', true);
    
    if (result.success) {
        const version = result.output.trim();
        log(`  ✓ Node.js ${version} found`, colors.green);
        return { success: true, version };
    }
    
    log(`  ✗ Node.js not found or error executing command`, colors.red);
    return { success: false };
}

function checkNpmDependencies() {
    log('Checking npm dependencies...', colors.cyan);
    
    // Check if node_modules exists
    const nodeModulesPath = path.join(electronDir, 'node_modules');
    if (!fs.existsSync(nodeModulesPath)) {
        log(`  ✗ node_modules not found, please run 'npm install' in the electron directory`, colors.red);
        return { success: false };
    }
    
    // Check if electron is installed
    const electronPath = path.join(nodeModulesPath, 'electron');
    if (!fs.existsSync(electronPath)) {
        log(`  ✗ Electron not found in node_modules`, colors.red);
        return { success: false };
    }
    
    // Check if electron-builder is installed
    const electronBuilderPath = path.join(nodeModulesPath, 'electron-builder');
    if (!fs.existsSync(electronBuilderPath)) {
        log(`  ✗ electron-builder not found in node_modules`, colors.red);
        return { success: false };
    }
    
    log(`  ✓ Required npm dependencies found`, colors.green);
    return { success: true };
}

function checkRustHelper() {
    log('Checking Rust helper binaries...', colors.cyan);
    
    // Check if rust_helper directory exists
    if (!fs.existsSync(rustHelperDir)) {
        log(`  ✗ rust_helper directory not found`, colors.red);
        return { success: false };
    }
    
    // Check for platform-specific binaries
    if (isWin) {
        const helperPath = path.join(rustHelperDir, 'betterman_helper.exe');
        const exists = fs.existsSync(helperPath);
        if (exists) {
            log(`  ✓ Windows helper binary found at ${helperPath}`, colors.green);
        } else {
            log(`  ⚠ Windows helper binary not found at ${helperPath} (will need to be added before final build)`, colors.yellow);
        }
        return { success: true, binaryExists: exists, binaryPath: helperPath };
    } else if (isMac || isLinux) {
        const helperPath = path.join(rustHelperDir, 'betterman_helper');
        const exists = fs.existsSync(helperPath);
        if (exists) {
            log(`  ✓ ${platformName} helper binary found at ${helperPath}`, colors.green);
        } else {
            log(`  ⚠ ${platformName} helper binary not found at ${helperPath} (will need to be added before final build)`, colors.yellow);
        }
        return { success: true, binaryExists: exists, binaryPath: helperPath };
    }
    
    return { success: false };
}

function checkBuildConfig() {
    log('Checking build configuration...', colors.cyan);
    
    // Check if build-config.js exists
    const buildConfigPath = path.join(electronDir, 'build-config.js');
    if (!fs.existsSync(buildConfigPath)) {
        log(`  ✗ build-config.js not found`, colors.red);
        return { success: false };
    }
    
    try {
        // Make sure it can be required
        const buildConfig = require('./build-config.js');
        log(`  ✓ build-config.js found and loaded successfully`, colors.green);
        return { success: true, config: buildConfig };
    } catch (error) {
        log(`  ✗ Error loading build-config.js: ${error.message}`, colors.red);
        return { success: false, error };
    }
}

function checkPythonRequirements() {
    log('Checking Python requirements...', colors.cyan);
    
    // Check if requirements.txt exists
    if (!fs.existsSync(pythonReqPath)) {
        log(`  ✗ requirements.txt not found in electron directory`, colors.red);
        return { success: false };
    }
    
    try {
        // Read requirements.txt
        const requirements = fs.readFileSync(pythonReqPath, 'utf8')
            .split('\n')
            .map(line => line.trim())
            .filter(line => line && !line.startsWith('#'))
            .map(line => line.split(/[<>=~]/)[0].trim());
        
        log(`  ✓ Found ${requirements.length} Python dependencies in requirements.txt`, colors.green);
        
        // Optionally verify if they're installed
        // (skipped for this test script since it would make the build environment-dependent)
        
        return { success: true, requirements };
    } catch (error) {
        log(`  ✗ Error reading requirements.txt: ${error.message}`, colors.red);
        return { success: false, error };
    }
}

function runPackagingTest() {
    log('Running packaging test...', colors.cyan);
    
    // Run a minimal packaging test without actually creating the final executable
    const testCommand = isWin ? 
        'npm run build:win -- --dir --x64 --publish never' : 
        'npm run build -- --dir --x64 --publish never';
    
    const result = executeCommand(testCommand);
    
    if (result.success) {
        log(`  ✓ Packaging test completed successfully`, colors.green);
        return { success: true };
    } else {
        log(`  ✗ Packaging test failed`, colors.red);
        return { success: false, error: result.error };
    }
}

// Main test function
function runTests() {
    log(`\n${colors.bright}BettermanAI Electron Build Test${colors.reset}`, colors.cyan);
    log(`Platform: ${platformName}`, colors.cyan);
    log(`Time: ${new Date().toLocaleString()}\n`, colors.cyan);
    
    const tests = [
        { name: 'Python Version', fn: checkPythonVersion },
        { name: 'Node.js Version', fn: checkNodeVersion },
        { name: 'NPM Dependencies', fn: checkNpmDependencies },
        { name: 'Rust Helper', fn: checkRustHelper },
        { name: 'Build Configuration', fn: checkBuildConfig },
        { name: 'Python Requirements', fn: checkPythonRequirements }
    ];
    
    // Run all tests
    const results = {};
    let allPassed = true;
    
    for (const test of tests) {
        const result = test.fn();
        results[test.name] = result;
        if (!result.success) {
            allPassed = false;
        }
    }
    
    // Display summary
    log('\nTest Summary:', colors.bright);
    for (const test of tests) {
        const result = results[test.name];
        const status = result.success ? `${colors.green}PASS` : `${colors.red}FAIL`;
        log(`${test.name}: ${status}${colors.reset}`);
    }
    
    // Check if we can proceed with packaging test
    if (allPassed) {
        log('\nAll pre-build tests passed. Running packaging test...', colors.bright + colors.green);
        const packagingResult = runPackagingTest();
        if (packagingResult.success) {
            log('\nAll tests passed! The application is ready for building.', colors.bright + colors.green);
        } else {
            log('\nPackaging test failed. Please fix the issues before building.', colors.bright + colors.red);
        }
    } else {
        log('\nSome tests failed. Please fix the issues before proceeding with the build.', colors.bright + colors.red);
    }
}

// Run the tests
runTests();