# BettermanAI

An intelligent cross-platform workflow automation platform that leverages advanced technologies to enhance productivity and user experience.

## Overview

BettermanAI is a personal workflow optimizer/copilot designed to automate repetitive tasks by observing user behavior, detecting patterns, and suggesting automations. The system functions as an intelligent assistant that learns from user actions and provides workflow optimization through pattern recognition, macro recording, and AI-powered reasoning.

## Core Technologies

- Electron desktop application framework
- Python backend with Flask and SQLAlchemy ORM
- Machine learning-powered automation
- OpenAI integration for intelligent recommendations
- Modular, responsive UI design with adaptive interfaces
- Event-driven architecture with comprehensive user behavior tracking

## Quick Start

1. Clone the repository
```
git clone https://github.com/ghcmartins1978/BetterWorkAI.git
cd BetterWorkAI
```

2. Install dependencies
```
install_dependencies.bat
install_electron.bat
```

3. Set up OpenAI API key (optional, for AI features)
```
set_openai_key.bat
```

4. Run the application
```
run_app_local_electron.bat
```

## Setup Scripts

- `install_dependencies.bat` - Installs Python dependencies
- `install_electron.bat` - Installs Electron and required NPM packages
- `set_openai_key.bat` - Sets up OpenAI API key for AI features
- `run_app_local_electron.bat` - Runs the full application with Electron
- `run_flask_web.bat` - Runs just the Flask web interface
- `cleanup_processes.bat` - Cleans up any running processes
- `check_app_status.bat` - Checks the status of the application setup

## Troubleshooting

If you encounter issues:

1. Run `check_app_status.bat` to check your environment setup
2. Run `cleanup_processes.bat` to clean up any lingering processes
3. Make sure your OpenAI API key is set if you want to use AI features
4. Check the logs in the console windows for any error messages

## Development

The application is structured with:
- Flask backend in Python
- Electron for desktop integration
- A mock helper service for development
- SQLite/PostgreSQL database for data storage

For development work, you can run just the Flask interface using `run_flask_web.bat`.

## License

[License information]