#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="client-exploration-tool"
DOCKER_IMAGE="${APP_NAME}:latest"
PORT=5000

echo -e "${BLUE}=== Client Exploration Tool Deployment ===${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to build and run with Docker
run_with_docker() {
    echo -e "${GREEN}Docker detected! Using containerized deployment...${NC}"
    
    # Build Docker image
    echo -e "${YELLOW}Building Docker image...${NC}"
    if docker build -t "${DOCKER_IMAGE}" .; then
        echo -e "${GREEN}✓ Docker image built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build Docker image${NC}"
        return 1
    fi
    
    # Stop any existing container
    echo -e "${YELLOW}Checking for existing containers...${NC}"
    if docker ps -a | grep -q "${APP_NAME}"; then
        echo "Stopping and removing existing container..."
        docker stop "${APP_NAME}" 2>/dev/null
        docker rm "${APP_NAME}" 2>/dev/null
    fi
    
    # Run the container
    echo -e "${YELLOW}Starting Docker container...${NC}"
    if docker run -d \
        --name "${APP_NAME}" \
        -p "${PORT}:5000" \
        -v "$(pwd)/client_exploration.db:/app/client_exploration.db" \
        "${DOCKER_IMAGE}"; then
        echo -e "${GREEN}✓ Container started successfully${NC}"
        echo -e "${BLUE}Application is running at: http://localhost:${PORT}${NC}"
        echo ""
        echo "To view logs: docker logs -f ${APP_NAME}"
        echo "To stop: docker stop ${APP_NAME}"
    else
        echo -e "${RED}✗ Failed to start Docker container${NC}"
        return 1
    fi
}

# Function to run with native Python venv
run_with_venv() {
    echo -e "${YELLOW}Docker not available. Using native Python virtual environment...${NC}"
    
    # Check Python availability
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}✗ Python is not installed. Please install Python 3.8 or higher.${NC}"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "Python version: $PYTHON_VERSION"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        $PYTHON_CMD -m venv venv
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Virtual environment created${NC}"
        else
            echo -e "${RED}✗ Failed to create virtual environment${NC}"
            exit 1
        fi
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        echo -e "${RED}✗ Could not find virtual environment activation script${NC}"
        exit 1
    fi
    
    # Upgrade pip
    echo -e "${YELLOW}Upgrading pip...${NC}"
    pip install --upgrade pip
    
    # Install requirements
    echo -e "${YELLOW}Installing requirements...${NC}"
    if pip install -r requirements.txt; then
        echo -e "${GREEN}✓ Requirements installed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to install requirements${NC}"
        exit 1
    fi
    
    # Check if database exists, create if not
    if [ ! -f "client_exploration.db" ]; then
        echo -e "${YELLOW}Database not found. Creating sample database...${NC}"
        python database.py
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Database created successfully${NC}"
        else
            echo -e "${RED}✗ Failed to create database${NC}"
            exit 1
        fi
    fi
    
    # Run the application
    echo -e "${YELLOW}Starting Flask application...${NC}"
    echo -e "${BLUE}Application will run at: http://localhost:${PORT}${NC}"
    echo ""
    python app.py
}

# Function to display help
show_help() {
    echo "Usage: ./run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --docker    Force Docker deployment"
    echo "  --venv      Force virtual environment deployment"
    echo "  --build     Build/rebuild only (Docker mode)"
    echo "  --help      Show this help message"
    echo ""
    echo "By default, the script will:"
    echo "  1. Check if Docker is available and use it if found"
    echo "  2. Fall back to Python virtual environment if Docker is not available"
}

# Parse command line arguments
FORCE_DOCKER=false
FORCE_VENV=false
BUILD_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            FORCE_DOCKER=true
            shift
            ;;
        --venv)
            FORCE_VENV=true
            shift
            ;;
        --build)
            BUILD_ONLY=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution logic
if [ "$FORCE_VENV" = true ]; then
    run_with_venv
elif [ "$FORCE_DOCKER" = true ]; then
    if command_exists docker; then
        if [ "$BUILD_ONLY" = true ]; then
            echo -e "${YELLOW}Building Docker image only...${NC}"
            docker build -t "${DOCKER_IMAGE}" .
        else
            run_with_docker
        fi
    else
        echo -e "${RED}✗ Docker is not installed but --docker flag was used${NC}"
        exit 1
    fi
else
    # Auto-detect deployment method
    if command_exists docker; then
        # Check if Docker daemon is running
        if docker info >/dev/null 2>&1; then
            if [ "$BUILD_ONLY" = true ]; then
                echo -e "${YELLOW}Building Docker image only...${NC}"
                docker build -t "${DOCKER_IMAGE}" .
            else
                run_with_docker
            fi
        else
            echo -e "${YELLOW}Docker is installed but daemon is not running${NC}"
            run_with_venv
        fi
    else
        run_with_venv
    fi
fi