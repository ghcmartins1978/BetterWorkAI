# BettermanAI - Personal Workflow Optimizer

BettermanAI is an intelligent cross-platform workflow automation platform that learns from your behavior to help you work more efficiently. It detects repetitive patterns in your daily activities and suggests automated workflows tailored to your specific needs.

![BettermanAI Screenshot](static/img/screenshot.png)

## Key Features

- **Intelligent Pattern Detection**: Automatically identifies repetitive tasks and workflows
- **Automation Suggestions**: Generates suggestions for automating common tasks
- **Macro Recording**: Create and edit automation macros with a simple interface
- **Advanced Execution Engine**: Reliable execution of automation workflows
- **Time Saving Analysis**: Track and visualize time saved through automations
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **OpenAI Integration**: Uses AI to enhance automation capabilities
- **Privacy-First Approach**: All data stays on your machine

## Installation

Download the latest version for your platform from the [Releases](https://github.com/bettermanai/bettermanai-app/releases) page.

See [INSTALLATION.md](INSTALLATION.md) for detailed installation instructions.

## System Requirements

- **Windows**: Windows 10 or newer
- **macOS**: macOS 10.15 (Catalina) or newer
- **Linux**: Ubuntu 20.04+, Debian 10+, or compatible distribution
- **Disk Space**: At least 500MB free
- **Memory**: 4GB RAM minimum, 8GB recommended

## Quick Start

1. Install BettermanAI following the instructions for your platform
2. Launch the application
3. Let it observe your workflow for a few days
4. Review and accept suggestions, or create your own macros
5. Enjoy your automated workflow!

## Development

For developers interested in contributing or customizing the application, see [DEVELOPMENT.md](DEVELOPMENT.md) for setup instructions.

### Building from Source

```bash
# Clone the repository
git clone https://github.com/bettermanai/bettermanai-app.git
cd bettermanai-app

# Install dependencies
cd electron
npm install

# Build for your platform
npm run build
```

## Architecture

BettermanAI follows a hybrid architecture with three main components:

1. **Flask Web Application**: Provides the UI and core application logic
2. **Rust Helper**: Provides system-level monitoring and automation capabilities
3. **Electron Wrapper**: Packages the Flask app and Rust helper into a desktop application

## License

Proprietary - All Rights Reserved

## Contact

- Website: [https://bettermanai.com](https://bettermanai.com)
- Support: support@bettermanai.com
- GitHub: [https://github.com/bettermanai](https://github.com/bettermanai)