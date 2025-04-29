/**
 * This file contains additional configuration for electron-builder
 * to handle Python packaging and platform-specific settings.
 */

const path = require('path');
const fs = require('fs');

// Get platform-specific settings
const platform = process.platform;

// Define paths
const rootDir = path.resolve(__dirname, '..');
const pythonDependencies = [
    "flask",
    "flask-sqlalchemy",
    "gunicorn",
    "psycopg2-binary",
    "pillow",
    "requests",
    "openai",
    "numpy"
];

// Define the python executable to use
const pythonExecutable = platform === 'win32' ? 'python.exe' : 'python3';

// Create a requirements.txt file for Python dependencies
const createRequirementsTxt = () => {
    const requirementsPath = path.join(__dirname, 'requirements.txt');
    fs.writeFileSync(requirementsPath, pythonDependencies.join('\n'));
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
        copyright: `Copyright © ${new Date().getFullYear()} BettermanAI`,
        
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
        ],
        
        // Package Python with the app
        extraMetadata: {
            build: {
                pythonPath: pythonExecutable
            }
        },
        
        // Platform-specific configurations
        mac: {
            target: ["dmg", "zip"],
            category: "public.app-category.productivity",
            darkModeSupport: true,
            icon: path.join(rootDir, 'generated-icon.png'),
            entitlements: "build/entitlements.mac.plist",
            entitlementsInherit: "build/entitlements.mac.plist",
            hardenedRuntime: true
        },
        
        win: {
            target: ["nsis", "portable"],
            icon: path.join(rootDir, 'generated-icon.png')
        },
        
        linux: {
            target: ["AppImage", "deb"],
            category: "Utility",
            synopsis: "BettermanAI - Personal Workflow Optimizer",
            maintainer: "BettermanAI Team",
            icon: path.join(rootDir, 'generated-icon.png')
        },
        
        // NSIS installer configuration for Windows
        nsis: {
            oneClick: false,
            perMachine: true,
            allowToChangeInstallationDirectory: true,
            createDesktopShortcut: true,
            createStartMenuShortcut: true,
            shortcutName: "BettermanAI",
            include: "installer.nsh"
        },
        
        // DMG configuration for macOS
        dmg: {
            contents: [
                {
                    x: 130,
                    y: 220
                },
                {
                    x: 410,
                    y: 220,
                    type: "link",
                    path: "/Applications"
                }
            ],
            window: {
                width: 540,
                height: 400
            }
        },
        
        // Auto-update configuration
        publish: {
            provider: "github",
            owner: "bettermanai",
            repo: "bettermanai-app"
        }
    }
};