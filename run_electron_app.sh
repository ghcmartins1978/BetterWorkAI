#!/bin/bash
# Script to run the BettermanAI Electron app locally

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== BettermanAI Development Setup ===${NC}"

# Check prerequisites
echo -e "\n${BLUE}Checking prerequisites...${NC}"

# Check Node.js
if command_exists node; then
  node_version=$(node -v)
  echo -e "${GREEN}✓ Node.js found: $node_version${NC}"
else
  echo -e "${RED}✗ Node.js not found. Please install Node.js 18 or higher: https://nodejs.org/${NC}"
  exit 1
fi

# Check npm
if command_exists npm; then
  npm_version=$(npm -v)
  echo -e "${GREEN}✓ npm found: $npm_version${NC}"
else
  echo -e "${RED}✗ npm not found. Please install Node.js which includes npm: https://nodejs.org/${NC}"
  exit 1
fi

# Check Python
python_cmd="python"
if ! command_exists $python_cmd; then
  python_cmd="python3"
  if ! command_exists $python_cmd; then
    echo -e "${RED}✗ Python not found. Please install Python 3.8 or higher: https://www.python.org/${NC}"
    exit 1
  fi
fi
python_version=$($python_cmd --version)
echo -e "${GREEN}✓ Python found: $python_version${NC}"

# Check pip
pip_cmd="pip"
if ! command_exists $pip_cmd; then
  pip_cmd="pip3"
  if ! command_exists $pip_cmd; then
    echo -e "${RED}✗ pip not found. Please install pip: https://pip.pypa.io/en/stable/installation/${NC}"
    exit 1
  fi
fi
pip_version=$($pip_cmd --version)
echo -e "${GREEN}✓ pip found: $pip_version${NC}"

# Set up environment
echo -e "\n${BLUE}Setting up environment...${NC}"

# Install Python dependencies
echo -e "\n${YELLOW}Installing Python dependencies...${NC}"
$pip_cmd install flask flask-sqlalchemy gunicorn pyyaml requests pyaudio soundfile trafilatura numpy opencv-python psutil openai email-validator psycopg2-binary pillow websocket-client
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to install Python dependencies. Check the error messages above.${NC}"
  echo -e "${YELLOW}You may need to install some system-level dependencies. On Ubuntu/Debian:${NC}"
  echo -e "${YELLOW}sudo apt-get install python3-dev portaudio19-dev libsndfile1-dev${NC}"
  echo -e "${YELLOW}On Windows, you might need Visual C++ Build Tools.${NC}"
  echo -e "${RED}Try to install the dependencies manually:${NC}"
  echo -e "${YELLOW}pip install flask flask-sqlalchemy gunicorn${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Install Node.js dependencies
echo -e "\n${YELLOW}Installing Node.js dependencies...${NC}"
cd electron
npm install
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to install Node.js dependencies. Check the error messages above.${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Node.js dependencies installed${NC}"

# Create data directory if it doesn't exist
echo -e "\n${YELLOW}Setting up data directory...${NC}"
cd ..
mkdir -p data
echo -e "${GREEN}✓ Data directory created${NC}"

# Set up environment variables
echo -e "\n${YELLOW}Setting up environment variables...${NC}"
export NODE_ENV=development
export RUNNING_IN_ELECTRON=1
export DATABASE_URL="sqlite:///$PWD/data/betterman.db"
export AUTOMATION_SERVER_URL="http://127.0.0.1:17400"
echo -e "${GREEN}✓ Environment variables set${NC}"

# Start the application
echo -e "\n${BLUE}Starting BettermanAI...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the application${NC}\n"

# Navigate to electron directory
cd electron

# Run the appropriate command based on platform
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  # Windows
  npm run win-dev
else
  # macOS or Linux
  npm run dev
fi