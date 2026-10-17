#!/usr/bin/env python3
"""
CTTC AutoTask FastAPI Backend Starter
Quick script to start the FastAPI backend from the root directory.
"""

import subprocess
import sys
import os

def main():
    """Start the FastAPI backend server."""
    print("🚀 Starting CTTC AutoTask FastAPI Backend...")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("backend/main.py"):
        print("❌ Error: backend/main.py not found!")
        print("   Please run this script from the project root directory.")
        sys.exit(1)
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found!")
        print("   Please create a .env file with your configuration.")
        print("   See backend/README.md for details.")
    
    print("📚 API Documentation will be available at: http://localhost:8000/docs")
    print("📖 ReDoc Documentation will be available at: http://localhost:8000/redoc")
    print("🔍 Health check: http://localhost:8000/health")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "backend.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 