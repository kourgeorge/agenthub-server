#!/bin/bash

# AgentHub Marketplace Demo - One-Command Runner

set -e

echo "🚀 AgentHub Marketplace Demo - One-Command Runner"
echo "================================================="

# Change to demo directory
cd "$(dirname "$0")"

# Run setup first
echo "🔧 Running setup..."
./setup.sh

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Run the demo
echo ""
echo "🎬 Starting demo..."
echo ""
python run_demo.py

echo ""
echo "✅ Demo completed!"
echo ""
echo "Cleanup:"
echo "  - Docker containers have been stopped and removed"
echo "  - Demo database saved as: demo_agenthub.db"
echo "  - Docker images preserved for reuse"
echo ""
echo "To run again:"
echo "  ./run_demo.sh"
echo ""