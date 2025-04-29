/**
 * Script to update electron dependencies automatically.
 * This script will scan requirements.txt and package.json to 
 * ensure all dependencies are correctly installed.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Paths
const rootDir = path.join(__dirname, '..');
const pythonReqPath = path.join(rootDir, 'requirements.txt');
const electronPackagePath = path.join(__dirname, 'package.json');
const buildConfigPath = path.join(__dirname, 'build-config.js');

// Functions
function executeCommand(command, cwd = process.cwd()) {
    console.log(`Executing: ${command}`);
    try {
        const output = execSync(command, { cwd, stdio: 'inherit' });
        return { success: true, output };
    } catch (error) {
        console.error(`Error executing ${command}:`, error.message);
        return { success: false, error };
    }
}

function updateElectronDependencies() {
    console.log('Updating Electron dependencies...');
    executeCommand('npm install', __dirname);
}

function extractPythonDependencies() {
    if (!fs.existsSync(pythonReqPath)) {
        console.error('requirements.txt not found');
        return [];
    }

    const content = fs.readFileSync(pythonReqPath, 'utf8');
    const lines = content.split('\n');
    const dependencies = [];

    for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine && !trimmedLine.startsWith('#')) {
            // Extract package name (remove version specifiers)
            const packageName = trimmedLine.split(/[=><~]+/)[0].trim();
            if (packageName) {
                dependencies.push(packageName);
            }
        }
    }

    return dependencies;
}

function updateBuildConfig() {
    console.log('Updating build configuration...');
    
    // Extract dependencies
    const pythonDependencies = extractPythonDependencies();
    
    // Check if build-config.js exists, if not, create it
    if (!fs.existsSync(buildConfigPath)) {
        console.log('build-config.js not found. Creating from template...');
        
        // Create a basic template
        const template = `/**
 * This file contains additional configuration for electron-builder
 * to handle Python packaging and platform-specific settings.
 */

const path = require('path');
const fs = require('fs');

// Get platform-specific settings
const platform = process.platform;

// Define paths
const rootDir = path.resolve(__dirname, '..');
const pythonDependencies = ${JSON.stringify(pythonDependencies, null, 4)};

// Define the python executable to use
const pythonExecutable = platform === 'win32' ? 'python.exe' : 'python3';

// Create a requirements.txt file for Python dependencies
const createRequirementsTxt = () => {
    const requirementsPath = path.join(__dirname, 'requirements.txt');
    fs.writeFileSync(requirementsPath, pythonDependencies.join('\\n'));
    return requirementsPath;
};

// Export the config
module.exports = {
    pythonExecutable,
    requirementsPath: createRequirementsTxt(),
    
    // Platform-specific build options
    buildOptions: {
        appId: 'com.bettermanai.app',
        productName: 'BettermanAI',
        copyright: \`Copyright © \${new Date().getFullYear()} BettermanAI\`,
        
        // Files to include
        files: [
            "**/*",
            "!**/node_modules/*/{CHANGELOG.md,README.md,README,readme.md,readme}",
            "!**/node_modules/*/{test,__tests__,tests,powered-test,example,examples}",
            "!**/node_modules/*.d.ts",
            "!**/node_modules/.bin",
            "!**/*.{iml,o,hprof,orig,pyc,pyo,rbc,swp,csproj,sln,xproj}",
            "!.editorconfig",
            "!**/{.DS_Store,.git,.hg,.svn,CVS,RCS,SCCS,.gitignore,.gitattributes}",
            "!**/{__pycache__,thumbs.db,.flowconfig,.idea,.vs,.nyc_output}",
            "!**/{appveyor.yml,.travis.yml,circle.yml}",
            "!**/{npm-debug.log,yarn.lock,.yarn-integrity,.yarn-metadata.json}"
        ],
        
        extraResources: [
            {
                from: '..',
                to: 'app',
                filter: [
                    "**/*.py",
                    "**/*.html",
                    "**/*.css",
                    "**/*.js",
                    "**/*.png",
                    "**/*.jpg",
                    "templates/**/*",
                    "static/**/*",
                    "data/**/*",
                    "!**/*.db",
                    "!**/__pycache__/**",
                    "!**/venv/**",
                    "!**/dist/**",
                    "!**/.git/**"
                ]
            }
        ]
    }
};`;
        
        fs.writeFileSync(buildConfigPath, template);
        console.log('build-config.js created successfully');
    } else {
        // Read and update the existing file
        let content = fs.readFileSync(buildConfigPath, 'utf8');
        
        // Find the pythonDependencies array and update it
        const dependencyMatch = content.match(/const\s+pythonDependencies\s*=\s*\[([\s\S]*?)\];/);
        if (dependencyMatch) {
            const newDependencies = JSON.stringify(pythonDependencies, null, 4)
                .split('\n')
                .map((line, i) => i === 0 ? line : '    ' + line)
                .join('\n');
            
            content = content.replace(
                /const\s+pythonDependencies\s*=\s*\[([\s\S]*?)\];/,
                `const pythonDependencies = ${newDependencies};`
            );
            
            fs.writeFileSync(buildConfigPath, content);
            console.log('build-config.js updated successfully');
        } else {
            console.error('Could not find pythonDependencies in build-config.js');
        }
    }
}

// Main execution
function main() {
    console.log('Starting dependency update...');
    
    // Update Electron dependencies
    updateElectronDependencies();
    
    // Update build configuration
    updateBuildConfig();
    
    console.log('Dependency update completed successfully');
}

// Run the script
main();