# BettermanAI - Development Guide

This document provides an overview of the BettermanAI development process and architecture.

## Development Environment Setup

### Prerequisites

- Node.js 18+ with npm
- Python 3.8+ with pip
- Rust toolchain (for building the helper)
- PostgreSQL (for development, optional)

### Initial Setup

1. Clone the repository:
   ```
   git clone https://github.com/bettermanai/bettermanai-app.git
   cd bettermanai-app
   ```

2. Install Node.js dependencies:
   ```
   npm install
   cd electron
   npm install
   cd ..
   ```

3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   # Create a .env file with the following variables
   OPENAI_API_KEY=your_openai_api_key  # Required for AI features
   DATABASE_URL=your_database_url      # PostgreSQL connection string (or SQLite)
   AUTOMATION_SERVER_URL=http://127.0.0.1:17400  # Local Rust helper URL
   ```

### Running in Development Mode

#### Running Flask App Directly

```
python main.py
```

This will start the Flask application on port 5000.

#### Running in Electron

```
cd electron
npm run dev  # On macOS/Linux
npm run win-dev  # On Windows
```

This will:
1. Start the Flask server as a child process
2. Start the Rust helper as a child process
3. Launch the Electron app pointing to the Flask server

### Building for Production

```
cd electron
npm run build  # Build for all platforms
npm run build:mac  # Build for macOS
npm run build:win  # Build for Windows
npm run build:linux  # Build for Linux
```

The built applications will be in the `electron/dist` directory.

## Project Architecture

BettermanAI follows a hybrid architecture with three main components:

### 1. Flask Web Application

- Location: Repository root
- Purpose: Provides the UI and core application logic
- Key files:
  - `main.py`: Main Flask application
  - `models.py`: SQLAlchemy database models
  - `database.py`: Database connection handling
  - `ai_llm.py`: OpenAI integration
  - `templates/`: HTML templates
  - `static/`: CSS, JavaScript, and static assets

### 2. Rust Helper

- Location: External repository, packaged in `electron/rust_helper/`
- Purpose: Provides system-level monitoring and automation capabilities
- Key components:
  - REST API for communication with Flask
  - TagUI integration for automation execution
  - Event listening for workflow monitoring

### 3. Electron Wrapper

- Location: `electron/`
- Purpose: Packages the Flask app and Rust helper into a desktop application
- Key files:
  - `main.js`: Main Electron process
  - `preload.js`: Secure bridge to web content
  - `package.json`: Application configuration
  - `build-config.js`: Build configuration

## Feature Development Process

When developing new features:

1. Begin with the Flask application logic
2. Update the database models if needed
3. Implement the UI in HTML/CSS/JavaScript
4. If needed, extend the Rust helper API
5. Test in development mode
6. Package with Electron and test distribution

## Testing

Run Python tests with:
```
python -m unittest discover tests
```

Run Electron tests with:
```
cd electron
npm test
```

## Database Migrations

When changing the database schema:

1. Update the models in `models.py`
2. Use SQLAlchemy's automatic migration handling
3. Test the migration thoroughly

## Contribution Guidelines

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## Versioning

BettermanAI follows semantic versioning:
- MAJOR version for incompatible API changes
- MINOR version for new features
- PATCH version for bug fixes