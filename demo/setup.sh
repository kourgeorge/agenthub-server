#!/bin/bash

# AgentHub Marketplace Demo Setup Script

set -e

echo "🚀 Setting up AgentHub Marketplace Demo"
echo "======================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "❌ Python 3.8+ is required. Found: Python $python_version"
    exit 1
fi

echo "✅ Python $python_version found"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed."
    echo "   Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running."
    echo "   Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is available and running"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the demo:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo "  2. Run the demo:"
echo "     python run_demo.py"
echo ""
echo "Or run the setup and demo in one command:"
echo "  ./run_demo.sh"
echo ""