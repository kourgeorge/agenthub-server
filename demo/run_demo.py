#!/usr/bin/env python3
"""
AgentHub Marketplace Demo Runner
Simple script to run the complete marketplace demonstration
"""

import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Check if all requirements are available"""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check Docker
    if not shutil.which("docker"):
        print("❌ Docker not found. Please install Docker.")
        return False
    
    # Check if Docker is running
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not running. Please start Docker.")
            return False
    except Exception:
        print("❌ Cannot communicate with Docker.")
        return False
    
    # Check required Python packages
    required_packages = ["fastapi", "uvicorn", "httpx", "pyyaml", "docker"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All requirements satisfied")
    return True

def run_demo():
    """Run the marketplace demo"""
    print("🚀 Starting AgentHub Marketplace Demo...")
    
    # Change to demo directory
    demo_dir = Path(__file__).parent
    
    try:
        # Run the demo
        subprocess.run([sys.executable, str(demo_dir / "marketplace_demo.py")], cwd=demo_dir)
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")

def main():
    """Main function"""
    print("AgentHub Marketplace Demo Runner")
    print("=" * 40)
    
    if not check_requirements():
        sys.exit(1)
    
    print("\n📋 Demo Overview:")
    print("This demo will demonstrate all 8 stages of the agent lifecycle:")
    print("1. 🔄 Registration - Register Docker-based agents")
    print("2. 🔍 Discovery - Browse marketplace catalog")
    print("3. 🚀 Instantiation - Create customer instances")
    print("4. ⚡ Active/Running - Execute tasks")
    print("5. 📊 Monitoring - Resource and health monitoring")
    print("6. ⏸️ Pause/Resume - Cost-saving pause/resume")
    print("7. 🛑 Termination - Clean shutdown with billing")
    print("8. 🗑️ Deregistration - Remove from marketplace")
    
    print("\n⚠️  Prerequisites:")
    print("- Docker must be running")
    print("- Internet access for downloading base images")
    print("- About 10-15 minutes to complete")
    
    try:
        input("\nPress Enter to start the demo (Ctrl+C to cancel)...")
    except KeyboardInterrupt:
        print("\n👋 Demo cancelled")
        sys.exit(0)
    
    run_demo()

if __name__ == "__main__":
    main()